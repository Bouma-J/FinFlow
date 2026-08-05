from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.storage_urls import file_download_url, is_s3_storage
from apps.common.tenancy import get_current_tenant_id
from apps.common.viewsets import TenantScopedViewSet

from .context import LOOP_HELP, VARIABLE_CATALOG, build_context
from .models import ContractTemplate, GeneratedContract
from .rendering import ContractRenderError, render_template
from .serializers import (
    ContractTemplateSerializer,
    GeneratedContractSerializer,
    GenerateContractSerializer,
    SignedContractUploadSerializer,
)
from .services import refresh_contract_status
from .tasks import generate_contract_task


def _get_application(application_id):
    from apps.credits.models import CreditApplication

    try:
        return CreditApplication.objects.select_related(
            "client", "product", "agency", "tenant"
        ).get(id=application_id)
    except (CreditApplication.DoesNotExist, ValueError, TypeError):
        raise Http404("Dossier introuvable.")


class ContractTemplateViewSet(TenantScopedViewSet):
    queryset = ContractTemplate.objects.select_related("product").all()
    serializer_class = ContractTemplateSerializer
    action_perms = {
        "variables": ["contracts.view_contracttemplate"],
        "applicable": ["contracts.view_contracttemplate"],
    }
    filterset_fields = ["category", "applies_to", "is_active", "is_required"]
    search_fields = ["name", "code", "description"]

    @action(detail=False, methods=["get"])
    def variables(self, request):
        """Catalogue documenté des variables utilisables dans les modèles."""
        return Response({"groups": VARIABLE_CATALOG, "loop_help": LOOP_HELP})

    @action(detail=False, methods=["get"])
    def applicable(self, request):
        """Modèles pertinents pour un dossier + statut de génération."""
        application_id = request.query_params.get("application")
        if not application_id:
            raise ValidationError({"application": "Paramètre requis."})
        application = _get_application(application_id)
        generated = {
            gc.template_id: gc
            for gc in application.generated_contracts.exclude(
                status=GeneratedContract.Status.CANCELLED
            )
        }
        result = []
        for tpl in self.get_queryset().filter(is_active=True):
            if not tpl.applies_to_application(application):
                continue
            gc = generated.get(tpl.id)
            result.append({
                "template": ContractTemplateSerializer(
                    tpl, context=self.get_serializer_context()
                ).data,
                "generated": gc is not None,
                "generated_contract_id": str(gc.id) if gc else None,
            })
        return Response(result)


class GeneratedContractViewSet(TenantScopedViewSet):
    queryset = GeneratedContract.objects.select_related(
        "application", "template", "created_by"
    ).all()
    serializer_class = GeneratedContractSerializer
    action_perms = {
        "generate": ["contracts.add_generatedcontract"],
        "upload_signed": ["contracts.change_generatedcontract"],
        "download": ["contracts.view_generatedcontract"],
    }
    filterset_fields = ["application", "status", "template"]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def create(self, request, *args, **kwargs):
        raise ValidationError(
            "Utilisez l'action « generate » pour produire un contrat."
        )

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Génère un contrat pour un dossier à partir d'un modèle."""
        payload = GenerateContractSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        application = _get_application(data["application"])
        try:
            template = ContractTemplate.objects.get(id=data["template"])
        except ContractTemplate.DoesNotExist:
            raise Http404("Modèle introuvable.")

        extra_values = data.get("extra_values") or {}
        async_mode = str(request.query_params.get("async", "")).lower() in (
            "1", "true", "yes",
        )
        if async_mode:
            task = generate_contract_task.delay(
                str(application.id),
                str(template.id),
                str(request.user.id),
                extra_values,
                str(get_current_tenant_id() or application.tenant_id or ""),
            )
            return Response(
                {"task_id": task.id, "status": "queued"},
                status=status.HTTP_202_ACCEPTED,
            )

        context = build_context(application, extra_values)

        try:
            rendered = render_template(template, context)
        except ContractRenderError as exc:
            raise ValidationError({"detail": str(exc)})

        with transaction.atomic():
            # Un seul contrat actif par modèle et par dossier : on annule
            # l'éventuel précédent pour garder une trace tout en régénérant.
            application.generated_contracts.filter(
                template=template
            ).exclude(status=GeneratedContract.Status.CANCELLED).update(
                status=GeneratedContract.Status.CANCELLED
            )
            # tenant AVANT file.save : upload_to utilise tenant_id pour le chemin S3.
            gc = GeneratedContract(
                tenant_id=application.tenant_id,
                application=application,
                template=template,
                template_name=template.name,
                category=template.category,
                context_snapshot=context,
                extra_values=extra_values,
                created_by=request.user,
                updated_by=request.user,
            )
            gc.file.save(rendered.name, rendered, save=False)
            gc.save()
            refresh_contract_status(application, request.user)

        serializer = self.get_serializer(gc)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        gc = self.get_object()
        if not gc.file:
            raise Http404("Aucun fichier.")
        if is_s3_storage() or request.query_params.get("presign") == "1":
            url = file_download_url(gc.file, expires=3600)
            if url and request.query_params.get("redirect") == "1":
                return redirect(url)
            if url:
                return Response({
                    "url": url,
                    "filename": gc.file.name.split("/")[-1],
                    "expires_in": 3600,
                })
        gc.file.open("rb")
        return FileResponse(
            gc.file, as_attachment=True, filename=gc.file.name.split("/")[-1]
        )

    @action(detail=True, methods=["post"])
    def upload_signed(self, request, pk=None):
        gc = self.get_object()
        serializer = SignedContractUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gc.signed_file = serializer.validated_data["signed_file"]
        gc.notes = serializer.validated_data.get("notes", gc.notes)
        gc.status = GeneratedContract.Status.SIGNED
        gc.signed_at = timezone.now()
        gc.updated_by = request.user
        gc.save()
        return Response(self.get_serializer(gc).data)

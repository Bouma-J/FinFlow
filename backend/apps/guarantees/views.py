from django.db import transaction
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.clients.models import Client
from apps.common.viewsets import AgencyScopedViewSet, TenantScopedViewSet
from apps.workflow.models import WorkflowInstance
from django.contrib.contenttypes.models import ContentType

from .models import (
    DationRequest,
    Guarantee,
    GuaranteeMovement,
    GuaranteeReleaseRequest,
)

from .process_services import (
    ProcessError,
    complete_dation_request,
    complete_release_request,
    initiate_dation_request,
    initiate_release_request,
    preview_dation_cbs,
    release_client_context,
)
from .serializers import (
    DationRequestSerializer,
    GuaranteeListSerializer,
    GuaranteeMovementSerializer,
    GuaranteeReleaseRequestSerializer,
    GuaranteeSerializer,
)

# Correspondance entre le type de mouvement et le nouveau statut de la garantie
_MOVEMENT_STATUS = {
    GuaranteeMovement.MovementType.RELEASE: Guarantee.Status.RELEASED,
    GuaranteeMovement.MovementType.REALIZATION: Guarantee.Status.REALIZED,
    GuaranteeMovement.MovementType.TRANSFER: Guarantee.Status.TRANSFERRED,
}


class GuaranteeViewSet(AgencyScopedViewSet):
    queryset = Guarantee.objects.select_related(
        "client", "application", "agency", "surety", "renewed_from"
    ).all()
    serializer_class = GuaranteeSerializer
    action_perms = {
        "add_movement": ["guarantees.change_guarantee"],
        "initiate_release": ["guarantees.initiate_guaranteereleaserequest"],
    }
    filterset_fields = ["guarantee_type", "status", "client", "application", "is_insured", "agency"]
    search_fields = ["reference", "description", "owners"]

    def get_serializer_class(self):
        if self.action == "list":
            return GuaranteeListSerializer
        return GuaranteeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            return qs
        return qs.select_related("surety").prefetch_related(
            "movements", "photos", "jewelry_items", "documents",
        )

    @staticmethod
    def _assert_application_allows_collateral(application, user):
        from apps.credits.access import can_attach_collateral

        if application is None:
            return
        if not can_attach_collateral(application, user):
            raise ValidationError(
                "Impossible de rattacher ou modifier une garantie sur un "
                f"dossier « {application.get_status_display()} »."
            )

    def perform_create(self, serializer):
        application = serializer.validated_data.get("application")
        self._assert_application_allows_collateral(
            application, self.request.user
        )
        super().perform_create(serializer)

    def perform_update(self, serializer):
        application = serializer.validated_data.get(
            "application", serializer.instance.application
        )
        self._assert_application_allows_collateral(
            application, self.request.user
        )
        super().perform_update(serializer)

    @action(detail=True, methods=["post"])
    def add_movement(self, request, pk=None):
        """Enregistre un mouvement et met à jour l'état de la garantie."""
        guarantee = self.get_object()
        serializer = GuaranteeMovementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            movement = serializer.save(guarantee=guarantee)
            if movement.movement_type == GuaranteeMovement.MovementType.REVALUATION:
                if movement.value is not None:
                    guarantee.current_value = movement.value
                    guarantee.last_valuation_date = movement.movement_date
            new_status = _MOVEMENT_STATUS.get(movement.movement_type)
            if new_status:
                guarantee.status = new_status
            guarantee.save()
        return Response(GuaranteeSerializer(guarantee).data)

    @action(detail=True, methods=["post"], url_path="initiate-release")
    def initiate_release(self, request, pk=None):
        """Démarre une main levée (contrôle CBS strict : prêt soldé)."""
        if not (
            request.user.is_superuser
            or request.user.has_perm("guarantees.initiate_guaranteereleaserequest")
        ):
            raise PermissionDenied(
                "Vous n'avez pas le droit d'initier une main levée."
            )
        guarantee = self.get_object()
        try:
            req = initiate_release_request(
                guarantee=guarantee,
                user=request.user,
                comment=request.data.get("comment", ""),
                cbs_loan_reference=request.data.get("cbs_loan_reference", ""),
            )
        except ProcessError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(GuaranteeReleaseRequestSerializer(req).data)


class GuaranteeMovementViewSet(TenantScopedViewSet):
    queryset = GuaranteeMovement.objects.select_related("guarantee").all()
    serializer_class = GuaranteeMovementSerializer
    filterset_fields = ["guarantee", "movement_type"]


class GuaranteeReleaseRequestViewSet(TenantScopedViewSet):
    queryset = GuaranteeReleaseRequest.objects.select_related(
        "guarantee", "guarantee__client", "application", "loan", "agency"
    ).all()
    serializer_class = GuaranteeReleaseRequestSerializer
    action_perms = {
        "create": ["guarantees.initiate_guaranteereleaserequest"],
        "client_context": ["guarantees.initiate_guaranteereleaserequest"],
        "retry_cbs": ["guarantees.initiate_guaranteereleaserequest"],
        "workflow": ["guarantees.view_guaranteereleaserequest"],
    }
    filterset_fields = ["status", "guarantee", "application", "agency"]
    search_fields = [
        "reference", "cbs_loan_reference", "cbs_client_id", "comment",
    ]
    http_method_names = ["get", "head", "options", "post"]

    @action(detail=False, methods=["get"], url_path="client-context")
    def client_context(self, request):
        """
        Garanties Fin Flow + crédits du client avec statut CBS.
        Matricule CBS = fiche client (cbs_client_id).
        """
        if not (
            request.user.is_superuser
            or request.user.has_perm(
                "guarantees.initiate_guaranteereleaserequest"
            )
        ):
            raise PermissionDenied(
                "Vous n'avez pas le droit d'initier une main levée."
            )
        client_id = request.query_params.get("client")
        if not client_id:
            raise ValidationError({"client": "Obligatoire."})
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist as exc:
            raise ValidationError({"client": "Client introuvable."}) from exc
        try:
            data = release_client_context(
                client=client,
                tenant_id=getattr(request.user, "tenant_id", None)
                or client.tenant_id,
            )
        except ProcessError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(data)

    def create(self, request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or request.user.has_perm(
                "guarantees.initiate_guaranteereleaserequest"
            )
        ):
            raise PermissionDenied(
                "Vous n'avez pas le droit d'initier une main levée."
            )
        guarantee_id = request.data.get("guarantee")
        if not guarantee_id:
            raise ValidationError({"guarantee": "Obligatoire."})
        try:
            guarantee = Guarantee.objects.get(pk=guarantee_id)
        except Guarantee.DoesNotExist as exc:
            raise ValidationError({"guarantee": "Garantie introuvable."}) from exc

        loan = None
        loan_id = request.data.get("loan")
        if loan_id:
            from apps.credits.models import Loan

            try:
                loan = Loan.objects.get(pk=loan_id)
            except Loan.DoesNotExist as exc:
                raise ValidationError({"loan": "Prêt introuvable."}) from exc

        request_date = request.data.get("request_date") or None
        try:
            req = initiate_release_request(
                guarantee=guarantee,
                user=request.user,
                comment=request.data.get("comment", ""),
                cbs_loan_reference=request.data.get("cbs_loan_reference", ""),
                loan=loan,
                request_date=request_date,
                release_fees=request.data.get("release_fees"),
                cbs_client_id=request.data.get("cbs_client_id", ""),
            )
        except ProcessError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(GuaranteeReleaseRequestSerializer(req).data, status=201)

    @action(detail=True, methods=["post"])
    def retry_cbs(self, request, pk=None):
        """Retente la finalisation CBS si la demande est bloquée."""
        req = self.get_object()
        if req.status != GuaranteeReleaseRequest.Status.BLOCKED:
            raise ValidationError(
                "Seule une demande bloquée par le CBS peut être relancée."
            )
        updated = complete_release_request(req)
        return Response(GuaranteeReleaseRequestSerializer(updated).data)

    @action(detail=True, methods=["get"])
    def workflow(self, request, pk=None):
        req = self.get_object()
        ct = ContentType.objects.get_for_model(GuaranteeReleaseRequest)
        inst = (
            WorkflowInstance.objects.filter(content_type=ct, object_id=req.pk)
            .select_related("definition")
            .prefetch_related("tasks", "tasks__step")
            .order_by("-created_at")
            .first()
        )
        if inst is None:
            return Response({"instance": None})
        from apps.workflow.serializers import WorkflowInstanceSerializer

        return Response({"instance": WorkflowInstanceSerializer(inst).data})


class DationRequestViewSet(TenantScopedViewSet):
    queryset = DationRequest.objects.select_related(
        "client", "application", "agency", "resulting_guarantee"
    ).prefetch_related("assets", "assets__guarantee").all()
    serializer_class = DationRequestSerializer
    action_perms = {
        "create": ["guarantees.initiate_dationrequest"],
        "preview_cbs": ["guarantees.initiate_dationrequest"],
        "retry_cbs": ["guarantees.initiate_dationrequest"],
        "workflow": ["guarantees.view_dationrequest"],
    }
    filterset_fields = ["status", "client", "application", "agency"]
    search_fields = ["reference", "cbs_client_id", "asset_description", "comment"]
    http_method_names = ["get", "head", "options", "post"]

    @action(detail=False, methods=["get"], url_path="preview-cbs")
    def preview_cbs(self, request):
        """
        Interroge le CBS pour le montant de créance (encours client)
        sans créer de demande — utilisé à la sélection du client.
        """
        if not (
            request.user.is_superuser
            or request.user.has_perm("guarantees.initiate_dationrequest")
        ):
            raise PermissionDenied(
                "Vous n'avez pas le droit d'initier une dation en paiement."
            )
        cbs_id = (
            request.query_params.get("cbs_client_id")
            or request.query_params.get("cbs_client")
            or ""
        ).strip()
        currency = (request.query_params.get("currency") or "XAF").strip() or "XAF"
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            raise ValidationError("Contexte filiale manquant.")
        try:
            cbs = preview_dation_cbs(
                tenant_id=tenant_id,
                cbs_client_id=cbs_id,
                currency=currency,
            )
        except ProcessError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(
            {
                "cbs_client_id": cbs_id,
                "total_outstanding": str(cbs["total_outstanding"]),
                "currency": cbs["currency"],
                "breakdown": cbs.get("breakdown") or [],
                "checked_at": None,
            }
        )

    def create(self, request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or request.user.has_perm("guarantees.initiate_dationrequest")
        ):
            raise PermissionDenied(
                "Vous n'avez pas le droit d'initier une dation en paiement."
            )
        client_id = request.data.get("client")
        if not client_id:
            raise ValidationError({"client": "Obligatoire."})
        try:
            client = Client.objects.get(pk=client_id)
        except Client.DoesNotExist as exc:
            raise ValidationError({"client": "Client introuvable."}) from exc

        application = None
        app_id = request.data.get("application")
        if app_id:
            from apps.credits.models import CreditApplication

            try:
                application = CreditApplication.objects.get(pk=app_id)
            except CreditApplication.DoesNotExist as exc:
                raise ValidationError({"application": "Dossier introuvable."}) from exc

        guarantee_ids = request.data.get("guarantee_ids") or []
        if isinstance(guarantee_ids, str):
            guarantee_ids = [guarantee_ids]
        if not isinstance(guarantee_ids, list):
            raise ValidationError({"guarantee_ids": "Liste attendue."})

        additional_assets = request.data.get("additional_assets") or []
        if not isinstance(additional_assets, list):
            raise ValidationError({"additional_assets": "Liste attendue."})

        asset_value = request.data.get("asset_value")
        try:
            req = initiate_dation_request(
                client=client,
                user=request.user,
                asset_description=request.data.get("asset_description", ""),
                asset_value=asset_value if asset_value not in (None, "") else None,
                application=application,
                comment=request.data.get("comment", ""),
                cbs_client_id=request.data.get("cbs_client_id", ""),
                guarantee_ids=guarantee_ids,
                additional_assets=additional_assets,
            )
        except ProcessError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(DationRequestSerializer(req).data, status=201)

    @action(detail=True, methods=["post"])
    def retry_cbs(self, request, pk=None):
        req = self.get_object()
        if req.status != DationRequest.Status.BLOCKED:
            raise ValidationError(
                "Seule une demande bloquée par le CBS peut être relancée."
            )
        updated = complete_dation_request(req)
        return Response(DationRequestSerializer(updated).data)

    @action(detail=True, methods=["get"])
    def workflow(self, request, pk=None):
        req = self.get_object()
        ct = ContentType.objects.get_for_model(DationRequest)
        inst = (
            WorkflowInstance.objects.filter(content_type=ct, object_id=req.pk)
            .select_related("definition")
            .prefetch_related("tasks", "tasks__step")
            .order_by("-created_at")
            .first()
        )
        if inst is None:
            return Response({"instance": None})
        from apps.workflow.serializers import WorkflowInstanceSerializer

        return Response({"instance": WorkflowInstanceSerializer(inst).data})

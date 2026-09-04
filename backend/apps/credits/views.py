from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.deletion import ProtectedError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditLog
from apps.common.permissions import HasModelPermission, MustChangePasswordGate
from apps.common.tenancy import get_current_tenant_id
from apps.common.viewsets import (
    AgencyScopedViewSet,
    TenantContextMixin,
    TenantScopedReadOnlyViewSet,
    TenantScopedViewSet,
)
from apps.workflow.models import ApprovalTask, WorkflowInstance
from apps.workflow.services import WorkflowError

from .models import (
    AnalysisThreshold,
    CreditApplication,
    CreditDocument,
    CreditInstructionPolicy,
    FieldVisit,
    FinancialAnalysis,
    Loan,
)
from .serializers import (
    AnalysisThresholdSerializer,
    CreditApplicationListSerializer,
    CreditApplicationSerializer,
    CreditDocumentSerializer,
    CreditInstructionPolicySerializer,
    FieldVisitSerializer,
    FinancialAnalysisSerializer,
    LoanSerializer,
    SimulationSerializer,
)
from .services import (
    cancel_application,
    cancel_disbursement_request,
    cancel_submission,
    compute_amortization_schedule,
    disburse_application,
    request_disbursement,
    submit_application,
)


class CreditApplicationViewSet(AgencyScopedViewSet):
    queryset = CreditApplication.objects.select_related(
        "client", "product", "agency"
    ).all()
    serializer_class = CreditApplicationSerializer
    permission_classes = [IsAuthenticated, HasModelPermission]
    enforce_model_permissions = True
    action_perms = {
        "submit": ["credits.change_creditapplication"],
        "cancel_submission": ["credits.change_creditapplication"],
        "request_disburse": ["credits.initiate_disburse_creditapplication"],
        # Initiateur ou valideur (contrôle OR dans l'action).
        "cancel_disburse_request": [],
        "disburse": ["credits.disburse_creditapplication"],
        "simulate": ["credits.view_creditapplication"],
        "timeline": ["credits.view_creditapplication"],
        "collateral_summary": ["credits.view_creditapplication"],
        "readiness": ["credits.view_creditapplication"],
        "cancel": ["credits.change_creditapplication"],
        "renewable_guarantees": ["credits.view_creditapplication"],
        "renew_guarantee": [
            "credits.change_creditapplication",
            "guarantees.add_guarantee",
        ],
    }
    filterset_fields = [
        "status", "client", "product", "agency", "currency", "risk_level",
    ]
    search_fields = [
        "reference", "client__reference", "client__last_name",
        "client__first_name", "client__company_name",
    ]
    ordering_fields = ["created_at", "amount_requested", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            return qs.select_related("client", "product", "agency")
        return qs.prefetch_related("stock_photos", "documents", "extra_fees")

    def get_serializer_class(self):
        if self.action == "list":
            return CreditApplicationListSerializer
        return CreditApplicationSerializer

    @staticmethod
    def _assert_is_creator(application, user, action_label):
        """N'autorise l'action qu'au créateur du dossier (ou à un super-admin)."""
        if getattr(user, "is_superuser", False):
            return
        if application.created_by_id and application.created_by_id == user.id:
            return
        raise PermissionDenied(
            f"Seul le créateur du dossier peut {action_label}."
        )

    @staticmethod
    def _assert_is_submitter(application, user):
        """N'autorise l'annulation qu'à l'auteur de la soumission (ou super-admin)."""
        if getattr(user, "is_superuser", False):
            return
        submitter_id = application.submitted_by_id or application.created_by_id
        if submitter_id and submitter_id == user.id:
            return
        raise PermissionDenied(
            "Seul le profil ayant soumis le dossier peut annuler la soumission."
        )

    # Statuts autorisant la modification (hors circuit d'approbation).
    EDITABLE_STATUSES = (
        CreditApplication.Status.DRAFT,
        CreditApplication.Status.RETURNED,
    )

    def destroy(self, request, *args, **kwargs):
        application = self.get_object()
        self._assert_is_creator(application, request.user, "le supprimer")
        # Suppression réservée aux brouillons jamais soumis.
        if application.status != CreditApplication.Status.DRAFT:
            raise ValidationError(
                "Seul un dossier en brouillon (non soumis) peut être supprimé. "
                "Annulez d'abord la soumission si nécessaire."
            )
        try:
            with transaction.atomic():
                # Les engagements de caution saisis dans le brouillon lui
                # appartiennent : ils sont supprimés en même temps que le dossier.
                application.surety_engagements.all().delete()
                application.delete()
        except ProtectedError as exc:
            # Filet de sécurité : si un objet protégé subsiste (p. ex. un prêt),
            # on renvoie un message explicite plutôt qu'une erreur 500.
            labels = sorted(
                {
                    str(type(obj)._meta.verbose_name)
                    for obj in exc.protected_objects
                }
            )
            detail = ", ".join(labels) if labels else "des éléments liés"
            raise ValidationError(
                "Suppression impossible : ce dossier est encore rattaché à "
                f"{detail}. Ces éléments doivent être retirés au préalable."
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _assert_editable(self, application):
        if application.status not in self.EDITABLE_STATUSES:
            raise ValidationError(
                "Ce dossier ne peut plus être modifié dans son état actuel "
                f"(« {application.get_status_display()} »). Annulez d'abord la "
                "soumission pour le repasser en brouillon."
            )

    def update(self, request, *args, **kwargs):
        application = self.get_object()
        self._assert_editable(application)
        self._assert_is_creator(
            application, request.user, "modifier ce dossier"
        )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        application = self.get_object()
        self._assert_editable(application)
        self._assert_is_creator(
            application, request.user, "modifier ce dossier"
        )
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Soumet le dossier et démarre le circuit d'approbation."""
        application = self.get_object()
        self._assert_is_creator(
            application, request.user, "le soumettre dans le circuit"
        )
        try:
            submit_application(application, request.user)
        except WorkflowError as exc:
            raise ValidationError(str(exc))
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"])
    def cancel_submission(self, request, pk=None):
        """Annule la soumission et repasse le dossier en brouillon."""
        application = self.get_object()
        self._assert_is_submitter(application, request.user)
        try:
            cancel_submission(application, request.user)
        except WorkflowError as exc:
            raise ValidationError(str(exc))
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["get"], url_path="collateral-summary")
    def collateral_summary(self, request, pk=None):
        """Synthèse garanties réelles + cautions (piliers séparés) pour l'analyse."""
        from .collateral import build_collateral_summary

        application = self.get_object()
        return Response(build_collateral_summary(application))

    @action(detail=True, methods=["get"])
    def readiness(self, request, pk=None):
        """Checklist de readiness avant soumission (selon politique filiale)."""
        from .instruction_policy import build_readiness

        application = self.get_object()
        return Response(build_readiness(application))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Annulation formelle du dossier (statut CANCELLED), si politique active."""
        application = self.get_object()
        self._assert_is_creator(
            application, request.user, "annuler ce dossier"
        )
        try:
            cancel_application(application, request.user)
        except WorkflowError as exc:
            raise ValidationError(str(exc))
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        """Chronologie (piste d'audit) des évènements clés du dossier."""
        application = self.get_object()
        events = []

        # Création du dossier.
        creator = application.created_by
        events.append({
            "timestamp": application.created_at.isoformat(),
            "kind": "CREATION",
            "event": "CREATED",
            "actor": str(creator) if creator else None,
            "comment": "",
            "step": None,
        })

        # Évènements de workflow explicites (soumission, annulation, renvois…).
        wf_logs = AuditLog.objects.filter(
            action=AuditLog.Action.WORKFLOW,
            model_label=application._meta.label,
            object_id=str(application.pk),
        ).select_related("user")
        for log in wf_logs:
            events.append({
                "timestamp": log.timestamp.isoformat(),
                "kind": "WORKFLOW",
                "event": (log.changes or {}).get("event", "WORKFLOW"),
                "actor": str(log.user) if log.user else None,
                "comment": (log.changes or {}).get("detail", ""),
                "step": None,
            })

        # Décisions prises sur les étapes d'approbation.
        ct = ContentType.objects.get_for_model(CreditApplication)
        instance_ids = WorkflowInstance.all_tenants.filter(
            content_type=ct, object_id=application.pk
        ).values_list("id", flat=True)
        tasks = (
            ApprovalTask.all_tenants.filter(
                instance_id__in=list(instance_ids),
                acted_at__isnull=False,
            )
            .select_related("step", "acted_by")
            .order_by("acted_at")
        )
        for task in tasks:
            events.append({
                "timestamp": task.acted_at.isoformat(),
                "kind": "DECISION",
                "event": task.status,
                "actor": str(task.acted_by) if task.acted_by else None,
                "comment": task.decision_comment or "",
                "step": task.step.name if task.step_id else None,
                "opinion": task.opinion or None,
            })

        events.sort(key=lambda e: e["timestamp"])
        return Response({"results": events})

    @action(detail=True, methods=["post"], url_path="request-disburse")
    def request_disburse(self, request, pk=None):
        """Initie une demande de décaissement (validation opérations requise)."""
        application = self.get_object()
        try:
            request_disbursement(application, user=request.user)
        except WorkflowError as exc:
            raise ValidationError(str(exc))
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"], url_path="cancel-disburse-request")
    def cancel_disburse_request(self, request, pk=None):
        """Annule une demande de décaissement en attente."""
        user = request.user
        if not (
            user.is_superuser
            or user.has_perm("credits.initiate_disburse_creditapplication")
            or user.has_perm("credits.disburse_creditapplication")
        ):
            raise PermissionDenied(
                "Droit insuffisant pour annuler une demande de décaissement."
            )
        application = self.get_object()
        try:
            cancel_disbursement_request(application)
        except WorkflowError as exc:
            raise ValidationError(str(exc))
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"])
    def disburse(self, request, pk=None):
        """Valide / exécute le décaissement (push CBS Perfect + prêt local).

        Réservé aux utilisateurs disposant du droit
        ``credits.disburse_creditapplication`` (Responsable des opérations,
        Administrateur filiale, etc.).

        Body optionnel :
        - ``core_banking_reference`` : surcharge manuelle de la réf. CBS
        - ``skip_cbs`` : true (superuser) pour forcer le mode local sans Perfect
        """
        application = self.get_object()
        cbs_ref = (request.data.get("core_banking_reference") or "").strip()
        skip_cbs = bool(request.data.get("skip_cbs")) and (
            request.user.is_superuser
            or getattr(request.user, "is_group_level", False)
        )
        try:
            loan = disburse_application(application, skip_cbs=skip_cbs)
        except WorkflowError as exc:
            raise ValidationError(str(exc))
        if cbs_ref:
            loan.core_banking_reference = cbs_ref
            loan.save(update_fields=["core_banking_reference"])
        return Response(LoanSerializer(loan).data)

    @action(detail=True, methods=["get"], url_path="renewable-guarantees")
    def renewable_guarantees(self, request, pk=None):
        """Garanties du client détectées comme reconductibles sur ce dossier."""
        from apps.guarantees.renewal_services import renewable_guarantees_for_application
        from apps.guarantees.serializers import GuaranteeSerializer

        application = self.get_object()
        qs = renewable_guarantees_for_application(application)
        return Response({"results": GuaranteeSerializer(qs, many=True).data})

    @action(detail=True, methods=["post"], url_path="renew-guarantee")
    def renew_guarantee(self, request, pk=None):
        """
        Reconduit une garantie antérieure sur ce dossier (nouvelle fiche liée).

        Body :
        - source_guarantee (uuid, obligatoire)
        - revaluate (bool)
        - valuation (objet optionnel : expertise_value, value_to_consider, …)
        - comment (str)
        """
        from apps.guarantees.models import Guarantee
        from apps.guarantees.renewal_services import RenewalError, renew_guarantee
        from apps.guarantees.serializers import GuaranteeSerializer

        application = self.get_object()
        source_id = request.data.get("source_guarantee")
        if not source_id:
            raise ValidationError({"source_guarantee": "Obligatoire."})
        try:
            source = Guarantee.objects.get(pk=source_id)
        except Guarantee.DoesNotExist as exc:
            raise ValidationError(
                {"source_guarantee": "Garantie introuvable."}
            ) from exc

        revaluate = bool(request.data.get("revaluate"))
        valuation = request.data.get("valuation") or {}
        if not isinstance(valuation, dict):
            raise ValidationError({"valuation": "Objet attendu."})

        try:
            clone = renew_guarantee(
                source=source,
                application=application,
                user=request.user,
                revaluate=revaluate,
                valuation=valuation,
                comment=request.data.get("comment", ""),
            )
        except RenewalError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(GuaranteeSerializer(clone).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def simulate(self, request):
        """Simulation d'un échéancier d'amortissement."""
        payload = SimulationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        schedule = compute_amortization_schedule(
            data["amount"], data["annual_rate"], data["months"],
            periodicity=data.get("periodicity", "MONTHLY"),
            start_date=data.get("simulation_date"),
            first_due_date=data.get("first_due_date"),
            savings_rate=data.get("savings_rate") or 0,
            mechanism=data.get("mechanism") or "DEGRESSIVE",
            tenant_id=getattr(request.user, "tenant_id", None)
            or request.headers.get("X-Tenant-Id"),
        )
        total = sum(row["total"] for row in schedule)
        total_savings = sum(row["savings"] for row in schedule)
        total_institution = sum(row["institution_due"] for row in schedule)
        total_interest = total_institution - data["amount"]
        first = schedule[0] if schedule else None
        return Response({
            "installment": first["institution_due"] if first else 0,
            "monthly_payment": first["institution_due"] if first else 0,
            "client_total_first": first["total"] if first else 0,
            "total_repayment": total,
            "total_institution": total_institution,
            "total_interest": total_interest,
            "total_savings": total_savings,
            "schedule": schedule,
        })


class CreditDocumentViewSet(TenantScopedViewSet):
    queryset = CreditDocument.objects.select_related("application").all()
    serializer_class = CreditDocumentSerializer
    permission_classes = [IsAuthenticated, HasModelPermission]
    enforce_model_permissions = True
    filterset_fields = ["application"]

    def get_queryset(self):
        from apps.common.access import apply_related_data_scope

        qs = super().get_queryset()
        user = self.request.user
        if user and user.is_authenticated:
            qs = apply_related_data_scope(qs, user, "application__agency")
        return qs


class FinancialAnalysisViewSet(TenantScopedViewSet):
    queryset = (
        FinancialAnalysis.objects.select_related(
            "application", "application__client", "created_by"
        )
        .prefetch_related("documents")
        .all()
    )
    serializer_class = FinancialAnalysisSerializer
    permission_classes = [IsAuthenticated, HasModelPermission]
    enforce_model_permissions = True
    filterset_fields = ["application", "client_type", "recommendation"]

    def get_queryset(self):
        from apps.common.access import apply_related_data_scope

        qs = super().get_queryset()
        user = self.request.user
        if user and user.is_authenticated:
            qs = apply_related_data_scope(qs, user, "application__agency")
        return qs

    def perform_create(self, serializer):
        from apps.accounts.utils import user_role_label
        from apps.common.tenancy import get_current_tenant_id

        from .access import can_contribute

        if get_current_tenant_id() is None:
            raise ValidationError({
                "detail": "Aucune filiale sélectionnée. Choisissez une filiale "
                          "dans la barre supérieure avant de créer un "
                          "enregistrement."
            })
        application = serializer.validated_data.get("application")
        if application is not None and not can_contribute(
            application, self.request.user
        ):
            raise PermissionDenied(
                "Vous n'êtes pas autorisé à ajouter une analyse sur ce dossier."
            )
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
            author_role=user_role_label(self.request.user),
        )

    def _assert_author(self, instance):
        user = self.request.user
        if not (user.is_superuser or instance.created_by_id == user.id):
            raise PermissionDenied(
                "Seul l'auteur peut modifier ou supprimer cette analyse."
            )

    def _assert_mutable(self, instance):
        from .access import can_mutate_contribution

        self._assert_author(instance)
        if not can_mutate_contribution(instance.application, self.request.user):
            raise PermissionDenied(
                "Cette analyse ne peut plus être modifiée : la fenêtre de "
                "contribution est fermée."
            )

    def perform_update(self, serializer):
        self._assert_mutable(serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._assert_mutable(instance)
        super().perform_destroy(instance)


class AnalysisThresholdViewSet(TenantScopedViewSet):
    """Seuils normatifs d'analyse, paramétrables par filiale."""

    queryset = AnalysisThreshold.objects.all()
    serializer_class = AnalysisThresholdSerializer
    action_perms = {
        "effective": ["credits.view_analysisthreshold"],
    }

    @action(detail=False, methods=["get"])
    def effective(self, request):
        """Renvoie les seuils applicables (ceux de la filiale ou les défauts)."""
        tenant_id = get_current_tenant_id()
        th = AnalysisThreshold.for_tenant(tenant_id)
        return Response(AnalysisThresholdSerializer(th).data)


class CreditInstructionPolicyViewSet(TenantContextMixin, viewsets.ViewSet):
    """
    Politique d'instruction crédit de la filiale active.

    - GET  /api/v1/credit-instruction-policy/current/
    - PATCH /api/v1/credit-instruction-policy/current/
    """

    permission_classes = [IsAuthenticated, MustChangePasswordGate]

    def _resolve_tenant_id(self, request):
        tenant_id = get_current_tenant_id()
        if not tenant_id and getattr(request.user, "tenant_id", None):
            tenant_id = request.user.tenant_id
        return tenant_id

    def _can_manage(self, user) -> bool:
        return bool(
            user.is_superuser
            or getattr(user, "is_group_level", False)
            or user.is_staff
            or user.has_perm("credits.change_creditinstructionpolicy")
        )

    @action(detail=False, methods=["get", "patch"])
    def current(self, request):
        tenant_id = self._resolve_tenant_id(request)
        if not tenant_id:
            return Response(
                {
                    "detail": (
                        "Sélectionnez une filiale pour paramétrer "
                        "la politique d'instruction."
                    )
                },
                status=400,
            )
        policy = CreditInstructionPolicy.for_tenant(tenant_id)
        if policy.pk is None:
            policy.tenant_id = tenant_id
            policy.save()

        if request.method == "GET":
            if not (
                request.user.has_perm("credits.view_creditinstructionpolicy")
                or self._can_manage(request.user)
            ):
                return Response({"detail": "Droit insuffisant."}, status=403)
            return Response(CreditInstructionPolicySerializer(policy).data)

        if not self._can_manage(request.user):
            return Response({"detail": "Droit insuffisant."}, status=403)

        serializer = CreditInstructionPolicySerializer(
            policy, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class FieldVisitViewSet(TenantScopedViewSet):
    queryset = FieldVisit.objects.select_related("application", "visited_by").all()
    serializer_class = FieldVisitSerializer
    permission_classes = [IsAuthenticated, HasModelPermission]
    enforce_model_permissions = True
    filterset_fields = ["application", "visited_by"]

    def get_queryset(self):
        from apps.common.access import apply_related_data_scope

        qs = super().get_queryset()
        user = self.request.user
        if user and user.is_authenticated:
            qs = apply_related_data_scope(qs, user, "application__agency")
        return qs

    def perform_create(self, serializer):
        from .access import can_contribute

        application = serializer.validated_data.get("application")
        if application is not None and not can_contribute(
            application, self.request.user
        ):
            raise PermissionDenied(
                "Vous n'êtes pas autorisé à ajouter une visite sur ce dossier."
            )
        super().perform_create(serializer)

    def _assert_author(self, instance):
        user = self.request.user
        if not (user.is_superuser or instance.visited_by_id == user.id):
            raise PermissionDenied(
                "Seul l'auteur peut modifier ou supprimer cette visite."
            )

    def _assert_mutable(self, instance):
        from .access import can_mutate_contribution

        self._assert_author(instance)
        if not can_mutate_contribution(instance.application, self.request.user):
            raise PermissionDenied(
                "Cette visite ne peut plus être modifiée : la fenêtre de "
                "contribution est fermée."
            )

    def perform_update(self, serializer):
        self._assert_mutable(serializer.instance)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._assert_mutable(instance)
        super().perform_destroy(instance)


class LoanViewSet(TenantScopedReadOnlyViewSet):
    queryset = Loan.objects.select_related("application").prefetch_related(
        "installments"
    ).all()
    serializer_class = LoanSerializer
    filterset_fields = ["status", "application"]

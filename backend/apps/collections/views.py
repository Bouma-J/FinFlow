from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.access import DataScope, get_user_agency_ids
from apps.common.viewsets import TenantScopedViewSet

from .models import (
    CollectionAction,
    CollectionCase,
    PaymentPromise,
    Repayment,
)
from .serializers import (
    CaseAssignSerializer,
    CaseRepaymentCreateSerializer,
    CaseStageSerializer,
    CollectionActionSerializer,
    CollectionCaseListSerializer,
    CollectionCaseSerializer,
    PaymentPromiseSerializer,
    RepaymentSerializer,
)

User = get_user_model()


class RepaymentViewSet(TenantScopedViewSet):
    queryset = Repayment.objects.select_related("loan").all()
    serializer_class = RepaymentSerializer
    filterset_fields = ["loan"]
    search_fields = ["reference"]


class CollectionCaseViewSet(TenantScopedViewSet):
    queryset = CollectionCase.objects.select_related(
        "loan",
        "loan__application",
        "loan__application__client",
        "loan__application__agency",
        "assigned_to",
    ).prefetch_related(
        "actions",
        "promises",
        "loan__installments",
        "loan__repayments",
    ).all()
    filterset_fields = ["stage", "par_class", "assigned_to"]
    ordering_fields = ["days_overdue", "overdue_amount", "created_at"]
    search_fields = [
        "loan__application__reference",
        "loan__application__client__last_name",
        "loan__application__client__first_name",
        "loan__core_banking_reference",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return CollectionCaseListSerializer
        return CollectionCaseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if getattr(user, "is_group_level", False):
            return qs
        scope = getattr(user, "data_scope", DataScope.AGENCY)
        if scope == DataScope.AGENCY:
            agency_ids = get_user_agency_ids(user)
            if not agency_ids:
                return qs.none()
            qs = qs.filter(loan__application__agency_id__in=agency_ids)
        elif scope == DataScope.OWN:
            qs = qs.filter(assigned_to=user)
        # TENANT : toute la filiale (déjà scopée par tenant)
        mine = self.request.query_params.get("mine")
        if mine in {"1", "true", "True"}:
            qs = qs.filter(assigned_to=user)
        open_only = self.request.query_params.get("open")
        if open_only in {"1", "true", "True"}:
            qs = qs.exclude(stage=CollectionCase.Stage.CLOSED)
        return qs

    @action(detail=True, methods=["post"], url_path="repayments")
    def add_repayment(self, request, pk=None):
        """Enregistre un encaissement et l'applique à l'échéancier."""
        case = self.get_object()
        serializer = CaseRepaymentCreateSerializer(
            data=request.data, context={"case": case, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        case.refresh_from_db()
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        """Affecte (ou retire) l'agent de recouvrement."""
        case = self.get_object()
        serializer = CaseAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data.get("assigned_to")
        if user_id is None:
            case.assigned_to = None
        else:
            try:
                agent = User.objects.get(pk=user_id)
            except User.DoesNotExist as exc:
                raise ValidationError({
                    "assigned_to": "Utilisateur introuvable."
                }) from exc
            if (
                not getattr(agent, "is_group_level", False)
                and agent.tenant_id
                and agent.tenant_id != case.tenant_id
            ):
                raise ValidationError({
                    "assigned_to": "L'agent doit appartenir à la filiale."
                })
            case.assigned_to = agent
        case.save(update_fields=["assigned_to"])
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="set-stage")
    def set_stage(self, request, pk=None):
        """Change le stade du dossier (amiable / précontentieux / …)."""
        case = self.get_object()
        serializer = CaseStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case.stage = serializer.validated_data["stage"]
        case.save(update_fields=["stage"])
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data
        )


class CollectionActionViewSet(TenantScopedViewSet):
    queryset = CollectionAction.objects.select_related("case").all()
    serializer_class = CollectionActionSerializer
    filterset_fields = ["case", "action_type"]


class PaymentPromiseViewSet(TenantScopedViewSet):
    queryset = PaymentPromise.objects.select_related("case").all()
    serializer_class = PaymentPromiseSerializer
    filterset_fields = ["case", "status"]

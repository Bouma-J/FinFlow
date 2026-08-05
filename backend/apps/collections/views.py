from apps.common.viewsets import TenantScopedViewSet

from .models import (
    CollectionAction,
    CollectionCase,
    PaymentPromise,
    Repayment,
)
from .serializers import (
    CollectionActionSerializer,
    CollectionCaseSerializer,
    PaymentPromiseSerializer,
    RepaymentSerializer,
)


class RepaymentViewSet(TenantScopedViewSet):
    queryset = Repayment.objects.select_related("loan").all()
    serializer_class = RepaymentSerializer
    filterset_fields = ["loan"]
    search_fields = ["reference"]


class CollectionCaseViewSet(TenantScopedViewSet):
    queryset = CollectionCase.objects.select_related("loan", "assigned_to").prefetch_related(
        "actions", "promises"
    ).all()
    serializer_class = CollectionCaseSerializer
    filterset_fields = ["stage", "par_class", "assigned_to"]
    ordering_fields = ["days_overdue", "overdue_amount"]


class CollectionActionViewSet(TenantScopedViewSet):
    queryset = CollectionAction.objects.select_related("case").all()
    serializer_class = CollectionActionSerializer
    filterset_fields = ["case", "action_type"]


class PaymentPromiseViewSet(TenantScopedViewSet):
    queryset = PaymentPromise.objects.select_related("case").all()
    serializer_class = PaymentPromiseSerializer
    filterset_fields = ["case", "status"]

from django.db.models import Count, Q
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.tenancy import get_current_tenant_id, is_group_context
from apps.common.viewsets import TenantScopedReadOnlyViewSet

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogFilter(filters.FilterSet):
    model_label = filters.CharFilter(lookup_expr="icontains")
    user_q = filters.CharFilter(method="filter_user")
    ip = filters.CharFilter(field_name="ip_address", lookup_expr="icontains")
    timestamp_after = filters.DateFilter(field_name="timestamp", lookup_expr="date__gte")
    timestamp_before = filters.DateFilter(field_name="timestamp", lookup_expr="date__lte")

    class Meta:
        model = AuditLog
        fields = ["action", "object_id", "user", "tenant"]

    def filter_user(self, queryset, _name, value):
        return queryset.filter(
            Q(user__username__icontains=value)
            | Q(user__first_name__icontains=value)
            | Q(user__last_name__icontains=value)
        )


class AuditLogViewSet(TenantScopedReadOnlyViewSet):
    """Consultation en lecture seule de la piste d'audit."""

    serializer_class = AuditLogSerializer
    filterset_class = AuditLogFilter
    search_fields = ["object_repr", "object_id", "model_label"]
    ordering_fields = ["timestamp"]

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.filter_queryset(self.get_queryset())
        by_action = {
            row["action"]: row["n"]
            for row in qs.values("action").annotate(n=Count("id"))
        }
        return Response({"total": sum(by_action.values()), "by_action": by_action})

    def get_queryset(self):
        qs = AuditLog.objects.select_related("user", "tenant")
        if not is_group_context():
            tenant_id = get_current_tenant_id()
            qs = qs.filter(tenant_id=tenant_id) if tenant_id else qs.none()
        return qs

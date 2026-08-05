from django.conf import settings
from rest_framework.response import Response

from apps.common.cache_utils import cache_key, cached_get
from apps.common.tenancy import get_current_tenant_id
from apps.common.viewsets import TenantMandatoryMixin, TenantScopedViewSet

from .models import (
    ChecklistItem,
    CreditProduct,
    ProductCategory,
    RejectReason,
)
from .serializers import (
    ChecklistItemSerializer,
    CreditProductSerializer,
    ProductCategorySerializer,
    RejectReasonSerializer,
)


class ProductCategoryViewSet(TenantMandatoryMixin, TenantScopedViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    filterset_fields = ["is_active"]
    search_fields = ["code", "label"]


class CreditProductViewSet(TenantMandatoryMixin, TenantScopedViewSet):
    queryset = CreditProduct.objects.select_related("category").all()
    serializer_class = CreditProductSerializer
    filterset_fields = ["category", "client_type", "currency", "is_active"]
    search_fields = ["code", "label"]

    def list(self, request, *args, **kwargs):
        tenant_id = get_current_tenant_id()
        qs_key = "&".join(
            f"{k}={','.join(request.query_params.getlist(k))}"
            for k in sorted(request.query_params.keys())
        )
        key = cache_key("credit-products", tenant_id, qs_key)
        ttl = getattr(settings, "CATALOG_CACHE_TTL", 120)

        def _produce():
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data).data
            serializer = self.get_serializer(queryset, many=True)
            return serializer.data

        return Response(cached_get(key, _produce, timeout=ttl))


class RejectReasonViewSet(TenantMandatoryMixin, TenantScopedViewSet):
    queryset = RejectReason.objects.all()
    serializer_class = RejectReasonSerializer
    filterset_fields = ["is_active"]
    search_fields = ["code", "label"]


class ChecklistItemViewSet(TenantMandatoryMixin, TenantScopedViewSet):
    queryset = ChecklistItem.objects.select_related("product").all()
    serializer_class = ChecklistItemSerializer
    filterset_fields = ["product", "is_mandatory"]

from rest_framework.routers import DefaultRouter

from .views import (
    ChecklistItemViewSet,
    CreditProductViewSet,
    ProductCategoryViewSet,
    RejectReasonViewSet,
)

router = DefaultRouter()
router.register("product-categories", ProductCategoryViewSet, basename="product-category")
router.register("credit-products", CreditProductViewSet, basename="credit-product")
router.register("reject-reasons", RejectReasonViewSet, basename="reject-reason")
router.register("checklist-items", ChecklistItemViewSet, basename="checklist-item")

urlpatterns = router.urls

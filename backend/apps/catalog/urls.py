from rest_framework.routers import DefaultRouter

from .views import (
    ChecklistItemViewSet,
    CreditProductViewSet,
    CurrencyViewSet,
    LoanPeriodicityViewSet,
    ProductCategoryViewSet,
    RejectReasonViewSet,
    RepaymentMethodViewSet,
)

router = DefaultRouter()
router.register("product-categories", ProductCategoryViewSet, basename="product-category")
router.register("credit-products", CreditProductViewSet, basename="credit-product")
router.register("reject-reasons", RejectReasonViewSet, basename="reject-reason")
router.register("loan-periodicities", LoanPeriodicityViewSet, basename="loan-periodicity")
router.register("repayment-methods", RepaymentMethodViewSet, basename="repayment-method")
router.register("currencies", CurrencyViewSet, basename="currency")
router.register("checklist-items", ChecklistItemViewSet, basename="checklist-item")

urlpatterns = router.urls

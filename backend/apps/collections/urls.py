from rest_framework.routers import DefaultRouter

from .views import (
    CollectionActionViewSet,
    CollectionCaseViewSet,
    PaymentPromiseViewSet,
    RepaymentViewSet,
)

router = DefaultRouter()
router.register("repayments", RepaymentViewSet, basename="repayment")
router.register("collection-cases", CollectionCaseViewSet, basename="collection-case")
router.register("collection-actions", CollectionActionViewSet, basename="collection-action")
router.register("payment-promises", PaymentPromiseViewSet, basename="payment-promise")

urlpatterns = router.urls

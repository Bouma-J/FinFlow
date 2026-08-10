from rest_framework.routers import DefaultRouter

from .views import (
    CollectionActionViewSet,
    CollectionCaseViewSet,
    CollectionEscalationRuleViewSet,
    LegalPartyViewSet,
    LitigationFileViewSet,
    PaymentPromiseViewSet,
    RepaymentViewSet,
)

router = DefaultRouter()
router.register("repayments", RepaymentViewSet, basename="repayment")
router.register("collection-cases", CollectionCaseViewSet, basename="collection-case")
router.register("collection-actions", CollectionActionViewSet, basename="collection-action")
router.register("payment-promises", PaymentPromiseViewSet, basename="payment-promise")
router.register(
    "collection-escalation-rules",
    CollectionEscalationRuleViewSet,
    basename="collection-escalation-rule",
)
router.register("legal-parties", LegalPartyViewSet, basename="legal-party")
router.register("litigations", LitigationFileViewSet, basename="litigation")

urlpatterns = router.urls

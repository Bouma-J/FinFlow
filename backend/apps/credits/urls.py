from rest_framework.routers import DefaultRouter

from .views import (
    AnalysisThresholdViewSet,
    CreditApplicationViewSet,
    CreditDocumentViewSet,
    CreditInstructionPolicyViewSet,
    FieldVisitViewSet,
    FinancialAnalysisViewSet,
    LoanRestructuringRequestViewSet,
    LoanViewSet,
    LoanWriteOffRequestViewSet,
)

router = DefaultRouter()
router.register("credit-applications", CreditApplicationViewSet, basename="credit-application")
router.register("credit-documents", CreditDocumentViewSet, basename="credit-document")
router.register("financial-analyses", FinancialAnalysisViewSet, basename="financial-analysis")
router.register("analysis-thresholds", AnalysisThresholdViewSet, basename="analysis-threshold")
router.register(
    "credit-instruction-policy",
    CreditInstructionPolicyViewSet,
    basename="credit-instruction-policy",
)
router.register("field-visits", FieldVisitViewSet, basename="field-visit")
router.register("loans", LoanViewSet, basename="loan")
router.register(
    "loan-writeoff-requests",
    LoanWriteOffRequestViewSet,
    basename="loan-writeoff-request",
)
router.register(
    "loan-restructuring-requests",
    LoanRestructuringRequestViewSet,
    basename="loan-restructuring-request",
)

urlpatterns = router.urls

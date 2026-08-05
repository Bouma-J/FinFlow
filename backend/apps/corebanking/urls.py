from rest_framework.routers import DefaultRouter

from .views import CoreBankingConnectorViewSet, IntegrationLogViewSet

router = DefaultRouter()
router.register("cbs-connectors", CoreBankingConnectorViewSet, basename="cbs-connector")
router.register("integration-logs", IntegrationLogViewSet, basename="integration-log")

urlpatterns = router.urls

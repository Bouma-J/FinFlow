from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.viewsets import TenantScopedReadOnlyViewSet, TenantScopedViewSet

from .models import CoreBankingConnector, IntegrationLog
from .serializers import (
    CoreBankingConnectorSerializer,
    IntegrationLogSerializer,
)
from .services import send_operation


class CoreBankingConnectorViewSet(TenantScopedViewSet):
    queryset = CoreBankingConnector.objects.all()
    serializer_class = CoreBankingConnectorSerializer
    action_perms = {
        "test_operation": ["corebanking.change_corebankingconnector"],
    }
    filterset_fields = ["protocol", "is_active"]
    search_fields = ["name"]

    @action(detail=True, methods=["post"])
    def test_operation(self, request, pk=None):
        """Envoie une opération de test au connecteur (journalisée)."""
        connector = self.get_object()
        operation = request.data.get("operation", "PING")
        payload = request.data.get("payload", {})
        log = send_operation(connector, operation, payload)
        return Response(IntegrationLogSerializer(log).data)


class IntegrationLogViewSet(TenantScopedReadOnlyViewSet):
    queryset = IntegrationLog.objects.select_related("connector").all()
    serializer_class = IntegrationLogSerializer
    action_perms = {
        "retry": ["corebanking.change_integrationlog"],
    }
    filterset_fields = ["connector", "status", "direction", "operation"]
    search_fields = ["operation", "external_reference", "idempotency_key"]

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Rejoue une opération en échec."""
        log = self.get_object()
        if log.status not in (IntegrationLog.Status.FAILED, IntegrationLog.Status.RETRY):
            raise ValidationError("Seule une opération en échec peut être rejouée.")
        new_log = send_operation(
            log.connector, log.operation, log.request_payload, log.idempotency_key
        )
        return Response(IntegrationLogSerializer(new_log).data)

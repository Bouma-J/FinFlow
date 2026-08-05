from rest_framework import serializers

from .models import CoreBankingConnector, IntegrationLog


class CoreBankingConnectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreBankingConnector
        fields = [
            "id", "name", "protocol", "base_url", "auth_config",
            "mapping_rules", "certificate_reference", "is_active",
            "timeout_seconds", "max_retries", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {
            "auth_config": {"write_only": True, "required": False},
            "mapping_rules": {"required": False},
        }


class IntegrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationLog
        fields = [
            "id", "connector", "operation", "direction", "idempotency_key",
            "request_payload", "response_payload", "status", "attempts",
            "external_reference", "error_message", "created_at",
        ]
        read_only_fields = fields

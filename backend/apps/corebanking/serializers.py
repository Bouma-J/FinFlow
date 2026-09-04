from rest_framework import serializers

from .models import CoreBankingConnector, IntegrationLog
from .perfect_defaults import perfect_auth_config, perfect_mapping_rules


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

    def create(self, validated_data):
        """Applique les défauts Perfect si auth / mapping absents."""
        protocol = validated_data.get("protocol") or CoreBankingConnector.Protocol.REST
        if protocol == CoreBankingConnector.Protocol.REST:
            rules = validated_data.get("mapping_rules") or {}
            if not rules:
                validated_data["mapping_rules"] = perfect_mapping_rules(demo=False)
            auth = validated_data.get("auth_config") or {}
            if not auth:
                validated_data["auth_config"] = perfect_auth_config()
            elif "scope" not in auth:
                auth = {**perfect_auth_config(), **auth}
                validated_data["auth_config"] = auth
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Fusionne auth_config (ne pas écraser password si omis)."""
        if "auth_config" in validated_data:
            incoming = validated_data.pop("auth_config") or {}
            merged = dict(instance.auth_config or {})
            for key, value in incoming.items():
                if value in (None, ""):
                    continue
                merged[key] = value
            if "scope" not in merged:
                merged["scope"] = perfect_auth_config()["scope"]
            validated_data["auth_config"] = merged
        return super().update(instance, validated_data)


class IntegrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationLog
        fields = [
            "id", "connector", "operation", "direction", "idempotency_key",
            "request_payload", "response_payload", "status", "attempts",
            "external_reference", "error_message", "created_at",
        ]
        read_only_fields = fields

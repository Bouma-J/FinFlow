import json

from rest_framework import serializers

from .models import ContractTemplate, GeneratedContract


class JSONOrStringField(serializers.JSONField):
    """JSONField tolérant : accepte aussi une chaîne JSON (envois multipart)."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            if data.strip() == "":
                return []
            try:
                return json.loads(data)
            except ValueError:
                self.fail("invalid")
        return super().to_internal_value(data)


class ContractTemplateSerializer(serializers.ModelSerializer):
    extra_fields = JSONOrStringField(required=False)
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    applies_to_display = serializers.CharField(
        source="get_applies_to_display", read_only=True
    )
    product_label = serializers.CharField(
        source="product.label", read_only=True
    )

    class Meta:
        model = ContractTemplate
        fields = [
            "id", "code", "name", "category", "category_display",
            "description", "engine", "file",
            "applies_to", "applies_to_display", "product", "product_label",
            "amount_min", "amount_max", "extra_fields",
            "is_required", "is_active", "ordering", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        from apps.common.storage_urls import file_download_url

        data["file"] = file_download_url(instance.file)
        return data

    def validate_file(self, value):
        name = (value.name or "").lower()
        if not (name.endswith(".docx") or name.endswith(".xlsx")):
            raise serializers.ValidationError(
                "Formats acceptés : .docx (Word) ou .xlsx (Excel)."
            )
        return value

    def validate(self, attrs):
        # Déduit le moteur à partir de l'extension du fichier importé.
        file = attrs.get("file")
        if file is not None:
            name = (file.name or "").lower()
            attrs["engine"] = (
                ContractTemplate.Engine.XLSX
                if name.endswith(".xlsx")
                else ContractTemplate.Engine.DOCX
            )
        return attrs


class GeneratedContractSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = GeneratedContract
        fields = [
            "id", "application", "template", "template_name", "category",
            "file", "status", "status_display", "signed_file", "signed_at",
            "notes", "extra_values", "created_by_name", "created_at",
        ]
        read_only_fields = [
            "id", "template_name", "category", "file", "context_snapshot",
            "created_by_name", "created_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        from apps.common.storage_urls import file_download_url

        # Évite les URLs MinIO non signées / sans bucket (AccessDenied).
        data["file"] = file_download_url(instance.file)
        data["signed_file"] = (
            file_download_url(instance.signed_file)
            if instance.signed_file
            else None
        )
        return data


class GenerateContractSerializer(serializers.Serializer):
    """Payload de génération d'un contrat pour un dossier."""

    application = serializers.UUIDField()
    template = serializers.UUIDField()
    extra_values = serializers.DictField(required=False, default=dict)


class SignedContractUploadSerializer(serializers.Serializer):
    signed_file = serializers.FileField()
    notes = serializers.CharField(required=False, allow_blank=True)

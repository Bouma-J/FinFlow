import os

from django.conf import settings
from rest_framework import serializers

from .models import Document, DocumentCategory


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentCategory
        fields = ["id", "code", "label", "description", "tracks_expiry", "is_active"]
        read_only_fields = ["id"]


class DocumentSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="category.label", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "category", "category_label", "name", "file", "mime_type",
            "size_bytes", "sha256", "version", "issue_date", "expiry_date",
            "content_type", "object_id", "uploaded_by", "created_at",
        ]
        read_only_fields = [
            "id", "mime_type", "size_bytes", "sha256",
            "uploaded_by", "created_at",
        ]

    def validate_file(self, value):
        max_bytes = settings.GED_MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"Fichier trop volumineux (max {settings.GED_MAX_UPLOAD_SIZE_MB} Mo)."
            )
        ext = os.path.splitext(value.name)[1].lower().lstrip(".")
        if ext not in settings.GED_ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Extension « {ext} » non autorisée."
            )
        request = self.context.get("request")
        tenant = getattr(getattr(request, "user", None), "tenant", None)
        if tenant is None and request is not None:
            from apps.common.tenancy import get_current_tenant_id
            from apps.tenants.models import Tenant

            tid = get_current_tenant_id()
            if tid:
                tenant = Tenant.objects.filter(pk=tid).first()
        if tenant is not None:
            from .quotas import assert_ged_quota

            assert_ged_quota(tenant, value.size)
        return value

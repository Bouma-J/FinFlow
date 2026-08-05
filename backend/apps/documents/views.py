import uuid
from datetime import timedelta

from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.storage_urls import (
    file_download_url,
    generate_presigned_upload,
    is_s3_storage,
)
from apps.common.tenancy import get_current_tenant_id
from apps.common.viewsets import TenantScopedViewSet

from .models import Document, DocumentCategory
from .serializers import DocumentCategorySerializer, DocumentSerializer


class DocumentCategoryViewSet(TenantScopedViewSet):
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer
    filterset_fields = ["tracks_expiry", "is_active"]
    search_fields = ["code", "label"]


class DocumentViewSet(TenantScopedViewSet):
    queryset = Document.objects.select_related("category", "uploaded_by").all()
    serializer_class = DocumentSerializer
    action_perms = {
        "download": ["documents.view_document"],
        "upload_url": ["documents.add_document"],
        "expiring_soon": ["documents.view_document"],
    }
    filterset_fields = ["category", "content_type", "object_id"]
    search_fields = ["name"]

    def perform_create(self, serializer):
        instance = serializer.save(uploaded_by=self.request.user)
        instance.mime_type = getattr(instance.file.file, "content_type", "") or ""
        instance.compute_hash()
        instance.save(update_fields=["mime_type", "sha256", "size_bytes"])
        from .quotas import bump_ged_usage

        bump_ged_usage(instance.tenant_id, instance.size_bytes)

    def perform_destroy(self, instance):
        size = int(instance.size_bytes or 0)
        tenant_id = instance.tenant_id
        super().perform_destroy(instance)
        from .quotas import bump_ged_usage

        bump_ged_usage(tenant_id, -size)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """URL de téléchargement (présignée S3) ou redirection locale."""
        doc = self.get_object()
        if not doc.file:
            raise Http404("Aucun fichier.")
        url = file_download_url(doc.file, expires=3600)
        if not url:
            raise Http404("Aucun fichier.")
        if request.query_params.get("redirect") == "1":
            return redirect(url)
        return Response({"url": url, "name": doc.name, "expires_in": 3600})

    @action(detail=False, methods=["post"])
    def upload_url(self, request):
        """
        URL PUT présignée pour upload direct vers MinIO/S3.
        Corps : {filename, content_type?, category?}
        """
        if not is_s3_storage():
            raise ValidationError(
                "L'upload présigné n'est disponible qu'avec STORAGE_BACKEND=s3."
            )
        filename = (request.data.get("filename") or "upload.bin").strip()
        content_type = (
            request.data.get("content_type") or "application/octet-stream"
        )
        tenant_id = get_current_tenant_id() or "group"
        category = request.data.get("category") or "misc"
        key = f"documents/{tenant_id}/{category}/{uuid.uuid4().hex}_{filename}"
        payload = generate_presigned_upload(
            key=key, content_type=content_type, expires=900
        )
        if not payload:
            raise ValidationError("Impossible de générer l'URL présignée.")
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def expiring_soon(self, request):
        """Documents dont l'expiration approche (30 jours) ou est dépassée."""
        horizon = timezone.now().date() + timedelta(days=30)
        qs = self.get_queryset().filter(
            category__tracks_expiry=True,
            expiry_date__isnull=False,
            expiry_date__lte=horizon,
        ).order_by("expiry_date")
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

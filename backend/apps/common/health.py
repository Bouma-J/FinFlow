"""Santé plateforme et métriques d'exploitation."""
from __future__ import annotations

import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import MustChangePasswordGate


def _check_database() -> dict:
    t0 = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"ok": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _check_cache() -> dict:
    t0 = time.perf_counter()
    try:
        key = "healthcheck:ping"
        cache.set(key, "1", 5)
        ok = cache.get(key) == "1"
        return {
            "ok": ok,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def _check_storage() -> dict:
    backend = getattr(settings, "STORAGE_BACKEND", "local")
    if backend != "s3":
        return {"ok": True, "backend": "local"}
    try:
        import boto3
        from botocore.client import Config

        t0 = time.perf_counter()
        client = boto3.client(
            "s3",
            endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None) or None,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=getattr(settings, "AWS_S3_REGION_NAME", "us-east-1"),
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
        client.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
        return {
            "ok": True,
            "backend": "s3",
            "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "backend": "s3", "error": str(exc)}


class HealthView(APIView):
    """
    Sonde liveness/readiness (DB, Redis, stockage).
    Public pour les probes K8s ; ne révèle pas de secrets.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        checks = {
            "database": _check_database(),
            "cache": _check_cache(),
            "storage": _check_storage(),
        }
        ready = all(c.get("ok") for c in checks.values())
        return Response(
            {
                "status": "ok" if ready else "degraded",
                "ready": ready,
                "time": timezone.now().isoformat(),
                "checks": checks,
            },
            status=200 if ready else 503,
        )


class MetricsView(APIView):
    """Métriques JSON d'exploitation (admin / groupe)."""

    permission_classes = [IsAuthenticated, MustChangePasswordGate]

    def get(self, request):
        user = request.user
        if not (
            user.is_staff
            or user.is_superuser
            or getattr(user, "is_group_level", False)
        ):
            raise PermissionDenied("Réservé aux administrateurs / Groupe.")

        from apps.credits.models import CreditApplication
        from apps.documents.models import Document
        from apps.tenants.models import Tenant
        from apps.workflow.models import ApprovalTask

        User = get_user_model()
        return Response(
            {
                "time": timezone.now().isoformat(),
                "tenants_active": Tenant.objects.filter(is_active=True).count(),
                "users_active": User.objects.filter(is_active=True).count(),
                "applications_total": CreditApplication.all_tenants.count(),
                "documents_total": Document.all_tenants.count(),
                "documents_bytes": Document.all_tenants.aggregate(t=Sum("size_bytes"))["t"]
                or 0,
                "approval_tasks_pending": ApprovalTask.all_tenants.filter(
                    status=ApprovalTask.Status.PENDING
                ).count(),
                "ged_quota_total": sum(
                    Tenant.objects.values_list("ged_quota_bytes", flat=True)
                ),
                "ged_used_total": sum(
                    Tenant.objects.values_list("ged_used_bytes", flat=True)
                ),
            }
        )

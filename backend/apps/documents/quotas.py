"""Gestion des quotas GED par filiale."""
from __future__ import annotations

from django.db import transaction
from django.db.models import F, Sum


def recalculate_tenant_ged_usage(tenant_id) -> int:
    from apps.documents.models import Document
    from apps.tenants.models import Tenant

    total = (
        Document.all_tenants.filter(tenant_id=tenant_id).aggregate(
            total=Sum("size_bytes")
        )["total"]
        or 0
    )
    Tenant.objects.filter(pk=tenant_id).update(ged_used_bytes=total)
    return int(total)


@transaction.atomic
def assert_ged_quota(tenant, additional_bytes: int) -> None:
    """Lève ValidationError si le quota serait dépassé."""
    from rest_framework import serializers

    if tenant is None:
        return
    used = int(tenant.ged_used_bytes or 0)
    quota = int(tenant.ged_quota_bytes or 0)
    if quota <= 0:
        return
    if used + int(additional_bytes) > quota:
        raise serializers.ValidationError(
            f"Quota GED dépassé pour la filiale ({used} / {quota} octets). "
            "Augmentez le quota ou archivez des documents."
        )


@transaction.atomic
def bump_ged_usage(tenant_id, delta: int) -> None:
    if not tenant_id or not delta:
        return
    from apps.tenants.models import Tenant

    Tenant.objects.filter(pk=tenant_id).update(
        ged_used_bytes=F("ged_used_bytes") + int(delta)
    )
    # Évite les valeurs négatives en cas de course.
    Tenant.objects.filter(pk=tenant_id, ged_used_bytes__lt=0).update(ged_used_bytes=0)

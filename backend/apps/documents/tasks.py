"""Tâches Celery — GED (alertes expiration)."""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("finflow")


@shared_task(ignore_result=True)
def notify_expiring_documents():
    """Journalise les documents expirant sous 30 jours (hook alertes)."""
    from apps.documents.models import Document

    horizon = timezone.now().date() + timedelta(days=30)
    qs = Document.all_tenants.filter(
        category__tracks_expiry=True,
        expiry_date__isnull=False,
        expiry_date__lte=horizon,
    )
    count = qs.count()
    logger.info("GED : %s document(s) à échéance ≤ 30 j", count)
    return count

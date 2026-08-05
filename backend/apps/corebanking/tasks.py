"""Tâches Celery — Core Banking (rejeux)."""
import logging

from celery import shared_task

logger = logging.getLogger("finflow")


@shared_task(ignore_result=True)
def retry_cbs_integrations(limit: int = 50):
    """Rejoue les opérations CBS marquées RETRY."""
    from apps.corebanking.models import IntegrationLog
    from apps.corebanking.services import send_operation

    logs = list(
        IntegrationLog.all_tenants.filter(status=IntegrationLog.Status.RETRY)
        .select_related("connector")
        .order_by("created_at")[:limit]
    )
    done = 0
    for log in logs:
        try:
            send_operation(
                log.connector,
                log.operation,
                log.request_payload or {},
                log.idempotency_key or "",
            )
            done += 1
        except Exception:  # noqa: BLE001
            logger.exception("Échec retry CBS log=%s", log.id)
    logger.info("CBS retry : %s opérations rejouées", done)
    return done

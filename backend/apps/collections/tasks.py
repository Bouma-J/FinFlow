"""Tâches Celery — recouvrement."""
import logging

from celery import shared_task

logger = logging.getLogger("finflow")


@shared_task(ignore_result=True)
def refresh_all_overdue_loans():
    """Recalcule les retards PAR pour tous les prêts actifs."""
    from apps.collections.services import (
        refresh_broken_promises,
        refresh_loan_overdue,
    )
    from apps.credits.models import Loan

    loans = Loan.all_tenants.filter(status=Loan.Status.ACTIVE).iterator()
    count = 0
    for loan in loans:
        try:
            refresh_loan_overdue(loan)
            count += 1
        except Exception:  # noqa: BLE001
            logger.exception("Échec refresh overdue loan=%s", loan.id)
    broken = refresh_broken_promises()
    logger.info(
        "Recouvrement : %s prêts actualisés, %s promesses rompues",
        count,
        broken,
    )
    return count


@shared_task(ignore_result=True)
def send_collection_reminders():
    """Relances automatiques EMAIL/SMS pour les actions dues."""
    from apps.collections.services import send_due_collection_reminders

    stats = send_due_collection_reminders()
    logger.info("Relances recouvrement : %s", stats)
    return stats


@shared_task(ignore_result=True)
def notify_hearing_reminders():
    """Rappels e-mail pour les audiences contentieux à J-7."""
    from apps.collections.services import notify_upcoming_hearings

    stats = notify_upcoming_hearings(within_days=7)
    logger.info("Rappels audiences contentieux : %s", stats)
    return stats

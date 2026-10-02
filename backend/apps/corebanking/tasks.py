"""Tâches Celery pour CBS: retry, réconciliation, monitoring."""
import logging

from config.celery import app

logger = logging.getLogger("finflow.cbs.tasks")


@app.task(name="corebanking.detect_orphan_disbursements")
def detect_orphan_disbursements():
    """
    Détecte les décaissements orphelins (CBS OK sans Loan local).
    
    Exécuté périodiquement (toutes les 15 min) pour réconciliation.
    Alerte ops si orphelins détectés.
    """
    from .outbox import find_orphan_disbursements
    
    orphans = find_orphan_disbursements()
    
    if orphans:
        logger.critical(
            f"ALERTE: {len(orphans)} décaissement(s) orphelin(s) détecté(s)",
            extra={
                "orphan_count": len(orphans),
                "orphan_ids": [o.pk for o in orphans],
            }
        )
        
        # TODO: Envoyer notification email/Slack aux ops
        # TODO: Créer ticket support automatique
        
        return {
            "status": "orphans_detected",
            "count": len(orphans),
            "ids": [o.pk for o in orphans],
        }
    
    logger.info("Réconciliation CBS: aucun orphelin détecté")
    return {"status": "ok", "count": 0}


@app.task(name="corebanking.cleanup_old_outbox_events")
def cleanup_old_outbox_events(retention_days=90):
    """
    Nettoie les events outbox complétés > retention_days.
    
    Args:
        retention_days: Rétention en jours (défaut: 90)
    """
    from datetime import timedelta
    from django.utils import timezone
    from .outbox import CbsOutboxEvent
    
    threshold = timezone.now() - timedelta(days=retention_days)
    
    deleted = CbsOutboxEvent.objects.filter(
        status__in=[
            CbsOutboxEvent.Status.COMPLETED,
            CbsOutboxEvent.Status.FAILED,
        ],
        completed_at__lt=threshold,
    ).delete()
    
    count = deleted[0] if deleted else 0
    logger.info(f"Nettoyage outbox CBS: {count} events supprimés (> {retention_days}j)")
    
    return {"deleted": count, "retention_days": retention_days}

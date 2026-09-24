"""
Pattern Outbox pour opérations CBS asynchrones et réconciliation.

Évite les orphelins CBS: si décaissement CBS réussit mais Django échoue,
l'outbox permet de tracer et réconcilier l'état.
"""
import logging
from django.db import models, transaction
from django.utils import timezone

from apps.common.models import TenantScopedModel

logger = logging.getLogger("finflow.cbs.outbox")


class CbsOutboxEvent(TenantScopedModel):
    """
    Journal des opérations CBS en attente de confirmation locale.
    
    Workflow:
    1. Créer event PENDING avant appel CBS
    2. Appeler CBS (hors transaction)
    3. Si CBS OK: marquer COMPLETED + créer entité locale
    4. Si CBS KO: marquer FAILED
    5. Worker réconciliation détecte PENDING > 5min
    """
    
    class EventType(models.TextChoices):
        DISBURSEMENT = "DISBURSEMENT", "Décaissement crédit"
        REPAYMENT = "REPAYMENT", "Remboursement"
        RESTRUCTURE = "RESTRUCTURE", "Restructuration"
    
    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente confirmation"
        COMPLETED = "COMPLETED", "Confirmé avec entité locale"
        FAILED = "FAILED", "Échec CBS"
        ORPHAN = "ORPHAN", "CBS OK mais entité locale manquante"
    
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    
    # Référence entité source (ex: CreditApplication.pk)
    entity_type = models.CharField(max_length=50)
    entity_id = models.BigIntegerField()
    
    # Résultat CBS
    cbs_request_payload = models.JSONField(null=True, blank=True)
    cbs_response = models.JSONField(null=True, blank=True)
    cbs_reference = models.CharField(max_length=200, blank=True, db_index=True)
    cbs_error = models.TextField(blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-initiated_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "initiated_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]
    
    def __str__(self):
        return f"{self.event_type} {self.entity_type}:{self.entity_id} [{self.status}]"
    
    def mark_completed(self, cbs_response=None):
        """Marquer comme complété après création entité locale."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        if cbs_response:
            self.cbs_response = cbs_response
        self.save(update_fields=["status", "completed_at", "cbs_response", "updated_at"])
        logger.info(
            f"Outbox event {self.pk} ({self.event_type}) marked COMPLETED",
            extra={"outbox_id": self.pk, "entity": f"{self.entity_type}:{self.entity_id}"}
        )
    
    def mark_failed(self, error: str):
        """Marquer comme échoué."""
        self.status = self.Status.FAILED
        self.cbs_error = error
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "cbs_error", "completed_at", "updated_at"])
        logger.warning(
            f"Outbox event {self.pk} ({self.event_type}) marked FAILED: {error}",
            extra={"outbox_id": self.pk, "entity": f"{self.entity_type}:{self.entity_id}"}
        )
    
    def mark_orphan(self):
        """Marquer comme orphelin (CBS OK mais pas d'entité locale)."""
        self.status = self.Status.ORPHAN
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])
        logger.error(
            f"Outbox event {self.pk} ({self.event_type}) marked ORPHAN - CBS success but local entity missing",
            extra={
                "outbox_id": self.pk,
                "entity": f"{self.entity_type}:{self.entity_id}",
                "cbs_reference": self.cbs_reference,
            }
        )


@transaction.atomic
def create_disbursement_outbox(application, cbs_request_payload=None):
    """Créer event outbox avant décaissement CBS."""
    from apps.credits.models import CreditApplication
    
    return CbsOutboxEvent.objects.create(
        tenant=application.tenant,
        event_type=CbsOutboxEvent.EventType.DISBURSEMENT,
        entity_type="CreditApplication",
        entity_id=application.pk,
        cbs_request_payload=cbs_request_payload or {},
    )


def find_orphan_disbursements():
    """
    Détecte les décaissements orphelins (CBS OK sans Loan local).
    
    Returns:
        QuerySet[CbsOutboxEvent]: Events PENDING > 5min avec CBS success probable
    """
    from datetime import timedelta
    threshold = timezone.now() - timedelta(minutes=5)
    
    pending = CbsOutboxEvent.objects.filter(
        event_type=CbsOutboxEvent.EventType.DISBURSEMENT,
        status=CbsOutboxEvent.Status.PENDING,
        initiated_at__lt=threshold,
    ).select_related("tenant")
    
    orphans = []
    for event in pending:
        # Vérifier si Loan existe
        from apps.credits.models import Loan
        loan_exists = Loan.objects.filter(
            application_id=event.entity_id,
            tenant=event.tenant,
        ).exists()
        
        if not loan_exists and event.cbs_reference:
            # CBS a réussi (reference présente) mais pas de Loan
            orphans.append(event)
            event.mark_orphan()
    
    return orphans

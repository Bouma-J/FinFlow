"""Recouvrement amiable et contentieux."""
from django.db import models

from apps.common.models import TenantScopedModel


class Repayment(TenantScopedModel):
    """Encaissement affecté à une ou plusieurs échéances d'un prêt."""

    loan = models.ForeignKey(
        "credits.Loan",
        on_delete=models.PROTECT,
        related_name="repayments",
        verbose_name="prêt",
    )
    amount = models.DecimalField("montant", max_digits=18, decimal_places=2)
    payment_date = models.DateField("date de paiement")
    reference = models.CharField("référence", max_length=100, blank=True)

    class Meta:
        verbose_name = "encaissement"
        verbose_name_plural = "encaissements"
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.amount} — {self.loan}"


class CollectionCase(TenantScopedModel):
    """Dossier de recouvrement associé à un prêt en retard."""

    class Stage(models.TextChoices):
        AMICABLE = "AMICABLE", "Amiable"
        PRECONTENTIOUS = "PRECONTENTIOUS", "Précontentieux"
        LITIGATION = "LITIGATION", "Contentieux"
        CLOSED = "CLOSED", "Clôturé"

    class ParClass(models.TextChoices):
        HEALTHY = "PAR0", "Sain"
        PAR1 = "PAR1_30", "PAR 1-30"
        PAR30 = "PAR31_90", "PAR 31-90"
        PAR90 = "PAR91_180", "PAR 91-180"
        PAR180 = "PAR180_PLUS", "PAR > 180"

    loan = models.OneToOneField(
        "credits.Loan",
        on_delete=models.CASCADE,
        related_name="collection_case",
        verbose_name="prêt",
    )
    stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.AMICABLE, db_index=True
    )
    par_class = models.CharField(
        max_length=20, choices=ParClass.choices, default=ParClass.HEALTHY, db_index=True
    )
    days_overdue = models.PositiveIntegerField("jours de retard", default=0)
    overdue_amount = models.DecimalField(
        "montant en retard", max_digits=18, decimal_places=2, default=0
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collection_cases",
        verbose_name="agent de recouvrement",
    )

    class Meta:
        verbose_name = "dossier de recouvrement"
        verbose_name_plural = "dossiers de recouvrement"
        ordering = ["-days_overdue"]
        indexes = [models.Index(fields=["tenant", "par_class", "stage"])]

    def __str__(self):
        return f"Recouvrement {self.loan}"


class CollectionAction(TenantScopedModel):
    """Action de relance ou de suivi sur un dossier de recouvrement."""

    class ActionType(models.TextChoices):
        CALL = "CALL", "Appel téléphonique"
        SMS = "SMS", "SMS"
        EMAIL = "EMAIL", "Courriel"
        LETTER = "LETTER", "Courrier"
        VISIT = "VISIT", "Visite terrain"
        LEGAL = "LEGAL", "Acte judiciaire"

    case = models.ForeignKey(
        CollectionCase,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name="dossier",
    )
    action_type = models.CharField(max_length=10, choices=ActionType.choices)
    action_date = models.DateField("date")
    result = models.CharField("résultat", max_length=255, blank=True)
    comment = models.TextField("commentaire", blank=True)

    class Meta:
        verbose_name = "action de recouvrement"
        verbose_name_plural = "actions de recouvrement"
        ordering = ["-action_date"]

    def __str__(self):
        return f"{self.get_action_type_display()} — {self.action_date}"


class PaymentPromise(TenantScopedModel):
    """Promesse de paiement prise dans le cadre du recouvrement."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        KEPT = "KEPT", "Tenue"
        BROKEN = "BROKEN", "Non tenue"

    case = models.ForeignKey(
        CollectionCase,
        on_delete=models.CASCADE,
        related_name="promises",
        verbose_name="dossier",
    )
    amount = models.DecimalField("montant promis", max_digits=18, decimal_places=2)
    promised_date = models.DateField("date promise")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )

    class Meta:
        verbose_name = "promesse de paiement"
        verbose_name_plural = "promesses de paiement"
        ordering = ["-promised_date"]

    def __str__(self):
        return f"{self.amount} — {self.promised_date}"

"""Workflow de validation pour les opérations sensibles sur prêts (Second Regard)."""
import logging
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from apps.common.models import AuthoredModel, TenantScopedModel

logger = logging.getLogger("finflow.credits")


class LoanOperationRequest(TenantScopedModel, AuthoredModel):
    """Classe abstraite pour les demandes d'opérations sensibles sur prêts."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente de validation"
        APPROVED = "APPROVED", "Approuvée"
        REJECTED = "REJECTED", "Rejetée"
        CANCELLED = "CANCELLED", "Annulée"
        EXECUTED = "EXECUTED", "Exécutée"

    loan = models.ForeignKey(
        "credits.Loan",
        on_delete=models.PROTECT,
        verbose_name="prêt",
    )
    status = models.CharField(
        "statut",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    justification = models.TextField(
        "justification de la demande",
        help_text="Expliquez en détail les raisons de cette demande.",
    )

    # Validation
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="validé par",
    )
    reviewed_at = models.DateTimeField("date de validation", null=True, blank=True)
    review_comment = models.TextField("commentaire du validateur", blank=True)

    # Exécution
    executed_at = models.DateTimeField("date d'exécution", null=True, blank=True)
    executed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="exécuté par",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def can_be_approved(self):
        """Vérifie si la demande peut être approuvée."""
        return self.status == self.Status.PENDING

    def can_be_rejected(self):
        """Vérifie si la demande peut être rejetée."""
        return self.status == self.Status.PENDING

    def can_be_executed(self):
        """Vérifie si la demande peut être exécutée."""
        return self.status == self.Status.APPROVED

    def approve(self, user, comment=""):
        """Approuve la demande."""
        if not self.can_be_approved():
            raise ValueError(
                f"La demande ne peut pas être approuvée (statut actuel: {self.status})"
            )

        self.status = self.Status.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_comment = comment
        self.save()
        logger.info(
            f"Demande {self.__class__.__name__} {self.pk} approuvée par {user}",
            extra={
                "request_id": self.pk,
                "request_type": self.__class__.__name__,
                "loan_id": self.loan_id,
                "approved_by": user.pk,
                "tenant_id": self.tenant_id,
            },
        )

    def reject(self, user, comment):
        """Rejette la demande."""
        if not self.can_be_rejected():
            raise ValueError(
                f"La demande ne peut pas être rejetée (statut actuel: {self.status})"
            )

        if not comment:
            raise ValueError("Un commentaire est obligatoire pour rejeter une demande")

        self.status = self.Status.REJECTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_comment = comment
        self.save()
        logger.info(
            f"Demande {self.__class__.__name__} {self.pk} rejetée par {user}",
            extra={
                "request_id": self.pk,
                "request_type": self.__class__.__name__,
                "loan_id": self.loan_id,
                "rejected_by": user.pk,
                "tenant_id": self.tenant_id,
            },
        )

    def cancel(self, user, reason=""):
        """Annule la demande (par le demandeur)."""
        if self.status not in (self.Status.PENDING, self.Status.APPROVED):
            raise ValueError(
                f"La demande ne peut plus être annulée (statut actuel: {self.status})"
            )

        self.status = self.Status.CANCELLED
        self.review_comment = f"Annulée par le demandeur. {reason}".strip()
        self.save()
        logger.info(
            f"Demande {self.__class__.__name__} {self.pk} annulée par {user}",
            extra={
                "request_id": self.pk,
                "request_type": self.__class__.__name__,
                "loan_id": self.loan_id,
                "cancelled_by": user.pk,
                "tenant_id": self.tenant_id,
            },
        )


class LoanWriteOffRequest(LoanOperationRequest):
    """Demande de passage en perte d'un crédit irrécupérable (Write-off)."""

    class WriteOffReason(models.TextChoices):
        UNRECOVERABLE = "UNRECOVERABLE", "Créance totalement irrécupérable"
        DEBTOR_DECEASED = "DEBTOR_DECEASED", "Décès du débiteur sans succession"
        DEBTOR_DISAPPEARED = "DEBTOR_DISAPPEARED", "Disparition du débiteur"
        LEGAL_EXHAUSTED = "LEGAL_EXHAUSTED", "Recours judiciaires épuisés"
        COST_BENEFIT = "COST_BENEFIT", "Coût de recouvrement > montant récupérable"
        OTHER = "OTHER", "Autre raison"

    reason = models.CharField(
        "motif du write-off",
        max_length=30,
        choices=WriteOffReason.choices,
        default=WriteOffReason.UNRECOVERABLE,
    )
    outstanding_balance = models.DecimalField(
        "solde restant dû au moment de la demande",
        max_digits=18,
        decimal_places=2,
        help_text="Montant qui sera passé en perte.",
    )
    days_past_due = models.PositiveIntegerField(
        "nombre de jours de retard",
        help_text="Nombre de jours depuis la première échéance impayée.",
    )
    recovery_attempts = models.TextField(
        "démarches de recouvrement effectuées",
        help_text="Listez toutes les actions de recouvrement entreprises (amiable, judiciaire, saisies...).",
    )
    guarantees_status = models.TextField(
        "statut des garanties",
        help_text="État des garanties et résultat de leur réalisation.",
        blank=True,
    )
    accounting_provision_rate = models.DecimalField(
        "taux de provisionnement actuel (%)",
        max_digits=6,
        decimal_places=2,
        default=100,
        help_text="Doit être à 100% pour un write-off.",
    )

    class Meta:
        verbose_name = "demande de passage en perte"
        verbose_name_plural = "demandes de passage en perte"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["loan", "-created_at"]),
        ]
        permissions = [
            ("approve_writeoff", "Peut approuver les demandes de write-off"),
            ("execute_writeoff", "Peut exécuter les write-offs approuvés"),
        ]

    def __str__(self):
        return f"Write-off {self.loan} — {self.get_status_display()}"

    def clean(self):
        """Validation métier avant enregistrement."""
        from django.core.exceptions import ValidationError

        errors = {}

        # Le prêt doit être actif
        if self.loan_id and self.loan.status != "ACTIVE":
            errors["loan"] = f"Le prêt doit être actif (statut actuel: {self.loan.get_status_display()})"

        # Minimum de jours de retard
        if self.days_past_due and self.days_past_due < 180:
            errors["days_past_due"] = (
                "Un write-off nécessite généralement au moins 180 jours de retard. "
                "Justifiez en détail si ce délai est plus court."
            )

        # Provisionnement obligatoire à 100%
        if self.accounting_provision_rate != Decimal("100"):
            errors["accounting_provision_rate"] = (
                "Le crédit doit être provisionné à 100% avant passage en perte."
            )

        # Solde > 0
        if self.outstanding_balance and self.outstanding_balance <= 0:
            errors["outstanding_balance"] = "Le solde restant dû doit être positif."

        if errors:
            raise ValidationError(errors)

    def execute(self, user):
        """Exécute le passage en perte après approbation."""
        if not self.can_be_executed():
            raise ValueError(
                f"La demande ne peut pas être exécutée (statut actuel: {self.status})"
            )

        with transaction.atomic():
            # Mettre à jour le statut du prêt
            loan = self.loan
            loan.status = "DEFAULTED"
            loan.save(update_fields=["status"])

            # Marquer la demande comme exécutée
            self.status = self.Status.EXECUTED
            self.executed_by = user
            self.executed_at = timezone.now()
            self.save()

            logger.warning(
                f"WRITE-OFF EXÉCUTÉ: Prêt {loan.pk} passé en perte",
                extra={
                    "request_id": self.pk,
                    "loan_id": loan.pk,
                    "application_id": loan.application_id,
                    "outstanding_balance": float(self.outstanding_balance),
                    "days_past_due": self.days_past_due,
                    "reason": self.reason,
                    "executed_by": user.pk,
                    "approved_by": self.reviewed_by.pk if self.reviewed_by else None,
                    "requested_by": self.created_by.pk if self.created_by else None,
                    "tenant_id": self.tenant_id,
                },
            )

        return loan


class LoanRestructuringRequest(LoanOperationRequest):
    """Demande de restructuration de crédit."""

    class RestructuringReason(models.TextChoices):
        TEMPORARY_DIFFICULTY = "TEMPORARY_DIFFICULTY", "Difficultés temporaires du client"
        INCOME_REDUCTION = "INCOME_REDUCTION", "Baisse de revenus"
        HEALTH_ISSUES = "HEALTH_ISSUES", "Problèmes de santé"
        BUSINESS_DOWNTURN = "BUSINESS_DOWNTURN", "Baisse d'activité économique"
        FORCE_MAJEURE = "FORCE_MAJEURE", "Force majeure (catastrophe naturelle, etc.)"
        AVOID_DEFAULT = "AVOID_DEFAULT", "Prévenir le défaut de paiement"
        OTHER = "OTHER", "Autre raison"

    reason = models.CharField(
        "motif de la restructuration",
        max_length=30,
        choices=RestructuringReason.choices,
        default=RestructuringReason.TEMPORARY_DIFFICULTY,
    )

    # État actuel du prêt
    current_outstanding_balance = models.DecimalField(
        "solde restant dû actuel",
        max_digits=18,
        decimal_places=2,
    )
    current_monthly_installment = models.DecimalField(
        "mensualité actuelle",
        max_digits=18,
        decimal_places=2,
    )
    current_remaining_months = models.PositiveIntegerField(
        "nombre de mois restants actuels",
    )
    current_days_past_due = models.PositiveIntegerField(
        "jours de retard actuels",
        default=0,
    )

    # Nouveaux termes proposés
    new_duration_months = models.PositiveIntegerField(
        "nouvelle durée (mois)",
        help_text="Durée totale restante après restructuration.",
    )
    new_interest_rate = models.DecimalField(
        "nouveau taux d'intérêt (%)",
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Laisser vide pour conserver le taux actuel.",
    )
    grace_period_months = models.PositiveIntegerField(
        "période de grâce (mois)",
        default=0,
        help_text="Nombre de mois sans remboursement de capital (intérêts uniquement).",
    )
    capitalize_arrears = models.BooleanField(
        "capitaliser les arriérés",
        default=False,
        help_text="Intégrer les impayés dans le nouveau capital.",
    )
    arrears_amount = models.DecimalField(
        "montant des arriérés à capitaliser",
        max_digits=18,
        decimal_places=2,
        default=0,
    )

    # Impact financier (calculé automatiquement)
    new_monthly_installment = models.DecimalField(
        "nouvelle mensualité estimée",
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    additional_interest_cost = models.DecimalField(
        "surcoût d'intérêts estimé",
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Coût supplémentaire lié à l'allongement de la durée.",
    )

    # Analyse de la capacité de remboursement révisée
    client_revised_income = models.DecimalField(
        "revenus révisés du client",
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    client_revised_expenses = models.DecimalField(
        "charges révisées du client",
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    revised_debt_ratio = models.DecimalField(
        "taux d'endettement révisé (%)",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Garanties maintenues
    guarantees_maintained = models.BooleanField(
        "garanties maintenues",
        default=True,
        help_text="Les garanties initiales restent en vigueur.",
    )
    guarantees_comment = models.TextField(
        "commentaire sur les garanties",
        blank=True,
    )

    # Conditions particulières
    special_conditions = models.TextField(
        "conditions particulières de la restructuration",
        blank=True,
        help_text="Clauses spécifiques, obligations du client, etc.",
    )

    # Historique
    previous_restructuring_count = models.PositiveIntegerField(
        "nombre de restructurations antérieures",
        default=0,
        help_text="Combien de fois ce prêt a déjà été restructuré.",
    )

    class Meta:
        verbose_name = "demande de restructuration"
        verbose_name_plural = "demandes de restructuration"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["loan", "-created_at"]),
        ]
        permissions = [
            ("approve_restructuring", "Peut approuver les demandes de restructuration"),
            ("execute_restructuring", "Peut exécuter les restructurations approuvées"),
        ]

    def __str__(self):
        return f"Restructuration {self.loan} — {self.get_status_display()}"

    def clean(self):
        """Validation métier avant enregistrement."""
        from django.core.exceptions import ValidationError

        errors = {}

        # Le prêt doit être actif
        if self.loan_id and self.loan.status != "ACTIVE":
            errors["loan"] = f"Le prêt doit être actif (statut actuel: {self.loan.get_status_display()})"

        # La nouvelle durée doit être différente
        if self.new_duration_months and self.current_remaining_months:
            if self.new_duration_months <= self.current_remaining_months:
                errors["new_duration_months"] = (
                    "La nouvelle durée doit être supérieure à la durée restante actuelle "
                    "pour qu'il s'agisse d'une restructuration."
                )

        # Limite de restructurations
        if self.previous_restructuring_count and self.previous_restructuring_count >= 2:
            errors["previous_restructuring_count"] = (
                "Ce prêt a déjà été restructuré 2 fois. Une 3ème restructuration "
                "nécessite une justification exceptionnelle et une autorisation spéciale."
            )

        # Période de grâce raisonnable
        if self.grace_period_months and self.grace_period_months > 6:
            errors["grace_period_months"] = (
                "Une période de grâce supérieure à 6 mois nécessite une justification exceptionnelle."
            )

        # Arriérés cohérents
        if self.capitalize_arrears and self.arrears_amount <= 0:
            errors["arrears_amount"] = (
                "Si vous capitalisez les arriérés, le montant doit être positif."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Calcul automatique de l'impact financier."""
        if self.new_duration_months and self.current_outstanding_balance:
            # Estimation simple de la nouvelle mensualité (sans tenir compte de la période de grâce)
            # Formule simplifiée : (Capital + arriérés) / durée
            # Dans la réalité, il faut calculer avec le taux et l'amortissement
            principal = self.current_outstanding_balance
            if self.capitalize_arrears:
                principal += self.arrears_amount or Decimal("0")

            rate = self.new_interest_rate or self.loan.interest_rate
            months = self.new_duration_months - self.grace_period_months

            if months > 0 and rate:
                # Formule d'amortissement dégressif simplifié
                monthly_rate = rate / Decimal("100") / Decimal("12")
                if monthly_rate > 0:
                    # Mensualité = Principal × [r(1+r)^n] / [(1+r)^n - 1]
                    factor = (1 + float(monthly_rate)) ** months
                    self.new_monthly_installment = (
                        principal * Decimal(str(monthly_rate * factor / (factor - 1)))
                    )
                else:
                    self.new_monthly_installment = principal / Decimal(months)
            else:
                self.new_monthly_installment = None

            # Estimation du surcoût d'intérêts (simplifié)
            if self.new_monthly_installment:
                total_paid_new = self.new_monthly_installment * Decimal(self.new_duration_months)
                total_paid_current = self.current_monthly_installment * Decimal(self.current_remaining_months)
                self.additional_interest_cost = max(
                    Decimal("0"), total_paid_new - total_paid_current
                )

        super().save(*args, **kwargs)

    def execute(self, user):
        """Exécute la restructuration après approbation."""
        if not self.can_be_executed():
            raise ValueError(
                f"La demande ne peut pas être exécutée (statut actuel: {self.status})"
            )

        with transaction.atomic():
            loan = self.loan

            # Mettre à jour les termes du prêt
            if self.new_interest_rate:
                loan.interest_rate = self.new_interest_rate

            # Marquer le prêt comme restructuré (on ajoute un champ métadonnées)
            # Dans une version complète, il faudrait recalculer l'échéancier
            # et créer un nouveau contrat

            # TODO: Implémenter la logique complète de restructuration
            # - Recalculer l'échéancier
            # - Mettre à jour les échéances futures
            # - Créer un avenant au contrat
            # - Notifier le client

            loan.save()

            # Marquer la demande comme exécutée
            self.status = self.Status.EXECUTED
            self.executed_by = user
            self.executed_at = timezone.now()
            self.save()

            logger.warning(
                f"RESTRUCTURATION EXÉCUTÉE: Prêt {loan.pk} restructuré",
                extra={
                    "request_id": self.pk,
                    "loan_id": loan.pk,
                    "application_id": loan.application_id,
                    "old_duration": self.current_remaining_months,
                    "new_duration": self.new_duration_months,
                    "old_installment": float(self.current_monthly_installment),
                    "new_installment": float(self.new_monthly_installment) if self.new_monthly_installment else None,
                    "grace_period": self.grace_period_months,
                    "capitalized_arrears": float(self.arrears_amount) if self.capitalize_arrears else 0,
                    "reason": self.reason,
                    "executed_by": user.pk,
                    "approved_by": self.reviewed_by.pk if self.reviewed_by else None,
                    "requested_by": self.created_by.pk if self.created_by else None,
                    "tenant_id": self.tenant_id,
                },
            )

        return loan

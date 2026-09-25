"""Politique de renouvellement de crédit et gestion de l'historique client."""
from decimal import Decimal

from django.db import models

from apps.common.models import TenantScopedModel


class CreditRenewalPolicy(TenantScopedModel):
    """Politique de renouvellement de crédit paramétrable par filiale.
    
    Définit les règles d'éligibilité et les seuils de validation
    pour le renouvellement de crédit des clients existants.
    """

    # ===================================================================
    # Seuils d'éligibilité au renouvellement
    # ===================================================================
    min_repayment_rate = models.DecimalField(
        "taux de remboursement minimum (%)",
        max_digits=6,
        decimal_places=2,
        default=Decimal("80.00"),
        help_text=(
            "Taux minimum de remboursement sur l'ensemble des crédits antérieurs. "
            "Ex: 80% signifie que le client doit avoir remboursé au moins 80% "
            "du capital emprunté."
        ),
    )

    max_days_late_allowed = models.PositiveIntegerField(
        "nombre maximum de jours de retard toléré",
        default=30,
        help_text=(
            "Retard maximum toléré sur les crédits en cours ou passés. "
            "Au-delà, génère une alerte."
        ),
    )

    min_months_since_last_disbursement = models.PositiveIntegerField(
        "délai minimum depuis le dernier décaissement (mois)",
        default=6,
        help_text=(
            "Nombre de mois minimum entre le dernier décaissement et une nouvelle "
            "demande de crédit."
        ),
    )

    min_months_since_loan_closure = models.PositiveIntegerField(
        "délai minimum depuis la clôture du dernier prêt (mois)",
        default=3,
        help_text=(
            "Nombre de mois minimum entre la clôture du dernier prêt actif "
            "et une nouvelle demande."
        ),
    )

    # ===================================================================
    # Règles de blocage (alertes bloquantes)
    # ===================================================================
    block_if_active_litigation = models.BooleanField(
        "bloquer si contentieux actif",
        default=True,
        help_text="Empêche la création d'un nouveau dossier si contentieux en cours.",
    )

    block_if_active_dation = models.BooleanField(
        "bloquer si dation en cours",
        default=True,
        help_text="Empêche la création d'un nouveau dossier si dation en paiement en cours.",
    )

    block_if_recent_restructuring = models.BooleanField(
        "bloquer si restructuration récente",
        default=False,
        help_text=(
            "Empêche la création si restructuration dans les 12 derniers mois. "
            "Si désactivé, génère seulement un avertissement."
        ),
    )

    block_if_writeoff_history = models.BooleanField(
        "bloquer si historique de write-off",
        default=True,
        help_text="Empêche la création si le client a un crédit passé en perte.",
    )

    block_if_active_loan = models.BooleanField(
        "bloquer si crédit actif en cours",
        default=False,
        help_text=(
            "Empêche la création si le client a déjà un crédit actif. "
            "Si désactivé, permet les crédits multiples simultanés."
        ),
    )

    block_if_below_repayment_threshold = models.BooleanField(
        "bloquer si taux de remboursement insuffisant",
        default=True,
        help_text="Empêche la création si le taux de remboursement < seuil minimum.",
    )

    # ===================================================================
    # Règles d'avertissement (alertes non bloquantes)
    # ===================================================================
    warn_if_late_payment = models.BooleanField(
        "avertir si retard de paiement",
        default=True,
        help_text="Génère une alerte si retards constatés (< max_days_late_allowed).",
    )

    warn_if_high_debt_ratio = models.BooleanField(
        "avertir si taux d'endettement élevé",
        default=True,
        help_text="Génère une alerte si taux d'endettement > seuil (ex: 35%).",
    )

    warn_if_increasing_amount = models.BooleanField(
        "avertir si montant en forte hausse",
        default=True,
        help_text="Génère une alerte si montant demandé > 150% du montant moyen passé.",
    )

    warn_if_multiple_active_loans = models.BooleanField(
        "avertir si plusieurs crédits actifs",
        default=True,
        help_text="Génère une alerte si le client a déjà 2+ crédits actifs ailleurs.",
    )

    # ===================================================================
    # Seuils de comparaison
    # ===================================================================
    significant_change_threshold = models.DecimalField(
        "seuil de changement significatif (%)",
        max_digits=6,
        decimal_places=2,
        default=Decimal("15.00"),
        help_text=(
            "Variation (en %) considérée comme significative pour la comparaison. "
            "Ex: 15% signifie qu'une variation >15% sera mise en évidence."
        ),
    )

    high_debt_ratio_threshold = models.DecimalField(
        "seuil de taux d'endettement élevé (%)",
        max_digits=6,
        decimal_places=2,
        default=Decimal("35.00"),
        help_text="Seuil au-delà duquel le taux d'endettement génère une alerte.",
    )

    max_amount_increase_pct = models.DecimalField(
        "hausse maximale de montant (%)",
        max_digits=6,
        decimal_places=2,
        default=Decimal("150.00"),
        help_text=(
            "Hausse maximale du montant vs moyenne historique avant alerte. "
            "Ex: 150% signifie que si montant demandé > 1.5x moyenne, alerte."
        ),
    )

    class Meta:
        verbose_name = "politique de renouvellement de crédit"
        verbose_name_plural = "politiques de renouvellement de crédit"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                name="unique_credit_renewal_policy_per_tenant",
            )
        ]

    def __str__(self):
        return f"Politique renouvellement — {self.tenant_id}"

    @classmethod
    def for_tenant(cls, tenant_id):
        """Retourne la politique de la filiale, ou des valeurs par défaut."""
        if not tenant_id:
            return cls()
        obj = cls.all_tenants.filter(tenant_id=tenant_id).first()
        if obj is not None:
            return obj
        # Retourne une instance non persistée avec les valeurs par défaut
        return cls(tenant_id=tenant_id)

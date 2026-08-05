"""Catalogue des produits de crédit et référentiels paramétrables."""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import ReferenceModel, TenantScopedModel


class ProductCategory(ReferenceModel):
    """Famille de produits de crédit (ex. Immobilier, Trésorerie, Conso)."""

    class Meta(ReferenceModel.Meta):
        verbose_name = "famille de produits"
        verbose_name_plural = "familles de produits"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="unique_productcategory_code_per_tenant"
            )
        ]


class CreditProduct(ReferenceModel):
    """Produit de crédit proposé par une filiale."""

    class ClientType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Particulier"
        PROFESSIONAL = "PROFESSIONAL", "Professionnel"
        CORPORATE = "CORPORATE", "Entreprise"
        ALL = "ALL", "Tous"

    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="famille",
    )
    client_type = models.CharField(
        max_length=20, choices=ClientType.choices, default=ClientType.ALL
    )
    currency = models.CharField("devise", max_length=3, default="XOF")

    amount_min = models.DecimalField(
        "montant minimum", max_digits=18, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    amount_max = models.DecimalField(
        "montant maximum", max_digits=18, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    duration_min_months = models.PositiveIntegerField("durée min (mois)", default=1)
    duration_max_months = models.PositiveIntegerField("durée max (mois)", default=60)

    interest_rate = models.DecimalField(
        "taux d'intérêt annuel (%)", max_digits=6, decimal_places=3, default=0
    )
    processing_fee_rate = models.DecimalField(
        "frais de dossier (%)", max_digits=6, decimal_places=3, default=0
    )
    requires_guarantee = models.BooleanField("garantie obligatoire", default=False)

    class Meta(ReferenceModel.Meta):
        verbose_name = "produit de crédit"
        verbose_name_plural = "produits de crédit"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="unique_creditproduct_code_per_tenant"
            )
        ]


class RejectReason(ReferenceModel):
    """Motif de rejet paramétrable (référentiel commun pour consolidation)."""

    class Meta(ReferenceModel.Meta):
        verbose_name = "motif de rejet"
        verbose_name_plural = "motifs de rejet"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="unique_rejectreason_code_per_tenant"
            )
        ]


class ChecklistItem(TenantScopedModel):
    """Pièce attendue d'une check-list documentaire, liée à un produit."""

    product = models.ForeignKey(
        CreditProduct,
        on_delete=models.CASCADE,
        related_name="checklist_items",
        verbose_name="produit",
    )
    label = models.CharField("libellé", max_length=255)
    is_mandatory = models.BooleanField("obligatoire", default=True)
    order = models.PositiveIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "pièce de check-list"
        verbose_name_plural = "check-list documentaire"
        ordering = ["order", "label"]

    def __str__(self):
        return self.label

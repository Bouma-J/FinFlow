"""Gestion des garanties et de leur cycle de vie."""
from decimal import Decimal

from django.db import models

from apps.common.files import safe_filename
from apps.common.models import AuthoredModel, TenantScopedModel


def guarantee_file_path(instance, filename):
    """Chemin de stockage des pièces jointes d'une garantie."""
    guarantee_id = getattr(instance, "guarantee_id", None) or instance.id
    return f"guarantees/{instance.tenant_id}/{guarantee_id}/{safe_filename(filename)}"


class DocumentType(models.TextChoices):
    LAND_TITLE = "LAND_TITLE", "Titre foncier"
    ATTRIBUTION_CERT = "ATTRIBUTION_CERT", "Attestation d'attribution"


class MatrimonialRegime(models.TextChoices):
    COMMUNITY = "COMMUNITY", "Communauté de biens"
    SEPARATION = "SEPARATION", "Séparation de biens"


class OccupancyStatus(models.TextChoices):
    FREE = "FREE", "Libre"
    FAMILY_HOME = "FAMILY_HOME", "Domicile familial"
    DEVELOPER = "DEVELOPER", "Occupé par le promoteur"
    RENTED = "RENTED", "En location"


class PledgeCategory(models.TextChoices):
    VEHICLE = "VEHICLE", "Moyen roulant"
    VALUABLE = "VALUABLE", "Objet de valeur"


class FinancialType(models.TextChoices):
    DAT = "DAT", "Dépôt à terme (DAT)"
    SAVINGS = "SAVINGS", "Épargne"
    SECURITY = "SECURITY", "Titre"


class Guarantee(TenantScopedModel, AuthoredModel):
    """Garantie adossée à un ou plusieurs crédits."""

    agency = models.ForeignKey(
        "tenants.Agency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guarantees",
        verbose_name="agence",
    )

    class GuaranteeType(models.TextChoices):
        MORTGAGE = "MORTGAGE", "Hypothèque (garantie réelle immobilière)"
        PLEDGE = "PLEDGE", "Gage (garantie réelle mobilière)"
        FINANCIAL = "FINANCIAL", "Garantie financière"
        LIEN = "LIEN", "Nantissement"
        DEPOSIT = "DEPOSIT", "Dépôt de garantie"
        BANK_GUARANTEE = "BANK_GUARANTEE", "Garantie bancaire"
        DATION = "DATION", "Dation en paiement"
        JOINT = "JOINT", "Garantie solidaire"
        OTHER = "OTHER", "Autre"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        RELEASED = "RELEASED", "Mainlevée"
        REALIZED = "REALIZED", "Réalisée"
        TRANSFERRED = "TRANSFERRED", "Transférée"

    reference = models.CharField("référence", max_length=30, blank=True)
    guarantee_type = models.CharField(max_length=20, choices=GuaranteeType.choices)
    pledge_category = models.CharField(
        "catégorie de gage", max_length=15,
        choices=PledgeCategory.choices, blank=True,
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.PROTECT,
        related_name="guarantees",
        verbose_name="client",
    )
    application = models.ForeignKey(
        "credits.CreditApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guarantees",
        verbose_name="dossier",
    )
    belongs_to_applicant = models.BooleanField(
        "bien appartenant au client demandeur",
        default=True,
        help_text=(
            "Si Non, une caution doit être renseignée (le bien n'appartient "
            "pas au client demandeur du crédit)."
        ),
    )
    surety = models.ForeignKey(
        "sureties.Surety",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guarantees",
        verbose_name="caution (propriétaire du bien)",
        help_text="Obligatoire si le bien n'appartient pas au client demandeur.",
    )
    renewed_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="renewals",
        verbose_name="garantie d'origine (reconduction)",
        help_text=(
            "Si renseigné, cette garantie a été créée par reconduction "
            "d'une garantie antérieure du client."
        ),
    )

    description = models.TextField("description", blank=True)
    owners = models.CharField("propriétaires", max_length=255, blank=True)

    expertise_value = models.DecimalField(
        "valeur d'expertise", max_digits=18, decimal_places=2, default=0
    )
    current_value = models.DecimalField(
        "valeur actualisée", max_digits=18, decimal_places=2, default=0
    )
    is_insured = models.BooleanField("assurée", default=False)
    insurance_reference = models.CharField("réf. assurance", max_length=100, blank=True)

    # ------------------------------------------------------------------ #
    # Propriétaire du bien (hypothèque / gage)
    # ------------------------------------------------------------------ #
    owner_last_name = models.CharField("nom du propriétaire", max_length=100, blank=True)
    owner_first_name = models.CharField(
        "prénom du propriétaire", max_length=100, blank=True
    )
    owner_marital_status = models.CharField(
        "situation matrimoniale du propriétaire", max_length=15, blank=True
    )
    matrimonial_regime = models.CharField(
        "régime matrimonial", max_length=15,
        choices=MatrimonialRegime.choices, blank=True,
    )

    # ------------------------------------------------------------------ #
    # Hypothèque (garantie réelle immobilière)
    # ------------------------------------------------------------------ #
    document_type = models.CharField(
        "type de document", max_length=20, choices=DocumentType.choices, blank=True
    )
    document_number = models.CharField("numéro du document", max_length=100, blank=True)
    document_issue_date = models.DateField(
        "date d'établissement du document", null=True, blank=True
    )
    address = models.CharField("adresse du bien", max_length=255, blank=True)
    expertise_date = models.DateField("date de l'expertise", null=True, blank=True)
    expertise_firm = models.CharField("cabinet d'expertise", max_length=200, blank=True)
    expert_name = models.CharField("nom de l'expert", max_length=200, blank=True)
    value_to_consider = models.DecimalField(
        "valeur à considérer", max_digits=18, decimal_places=2, null=True, blank=True
    )
    ltv_ratio = models.DecimalField(
        "ratio LTV", max_digits=8, decimal_places=4, null=True, blank=True,
        help_text="Valeur à considérer / montant du prêt (calculé).",
    )
    occupancy_status = models.CharField(
        "statut d'occupation", max_length=15, choices=OccupancyStatus.choices, blank=True
    )
    document_scan = models.FileField(
        "scan du document", upload_to=guarantee_file_path, max_length=255, blank=True
    )
    expertise_report_scan = models.FileField(
        "scan du rapport d'expertise", upload_to=guarantee_file_path, max_length=255, blank=True
    )
    lease_contract_scan = models.FileField(
        "scan du contrat de bail", upload_to=guarantee_file_path, max_length=255, blank=True
    )
    legal_situation_certificate_scan = models.FileField(
        "scan certificat de situation juridique", upload_to=guarantee_file_path,
        max_length=255, blank=True,
    )

    # ------------------------------------------------------------------ #
    # Gage — moyen roulant
    # ------------------------------------------------------------------ #
    chassis_number = models.CharField("numéro de châssis", max_length=100, blank=True)
    engine_number = models.CharField("numéro du moteur", max_length=100, blank=True)
    brand = models.CharField("marque", max_length=100, blank=True)
    model_name = models.CharField("modèle", max_length=100, blank=True)
    registration = models.CharField("immatriculation", max_length=50, blank=True)
    power = models.CharField("puissance", max_length=50, blank=True)
    first_registration_year = models.PositiveIntegerField(
        "année de première mise en circulation", null=True, blank=True
    )
    acquisition_date = models.DateField("date d'acquisition", null=True, blank=True)
    acquisition_value = models.DecimalField(
        "valeur d'acquisition", max_digits=18, decimal_places=2, null=True, blank=True
    )
    resale_value = models.DecimalField(
        "valeur estimée à la revente", max_digits=18, decimal_places=2,
        null=True, blank=True,
    )
    estimation_date = models.DateField("date d'estimation", null=True, blank=True)
    registration_card_scan = models.FileField(
        "scan carte grise", upload_to=guarantee_file_path, max_length=255, blank=True
    )
    mechanical_expertise_scan = models.FileField(
        "scan rapport d'expertise mécanique", upload_to=guarantee_file_path, max_length=255, blank=True
    )
    technical_inspection_scan = models.FileField(
        "scan visite technique", upload_to=guarantee_file_path, max_length=255, blank=True
    )
    insurance_scan = models.FileField(
        "scan assurance", upload_to=guarantee_file_path, max_length=255, blank=True
    )
    purchase_invoice_scan = models.FileField(
        "scan facture d'achat", upload_to=guarantee_file_path, max_length=255, blank=True
    )
    additional_info = models.TextField("information complémentaire", blank=True)

    # ------------------------------------------------------------------ #
    # Gage — objet de valeur
    # ------------------------------------------------------------------ #
    raw_material_price = models.DecimalField(
        "cours actuel de la matière première", max_digits=18, decimal_places=2,
        null=True, blank=True,
    )
    expertise_certificate_scan = models.FileField(
        "scan certificat d'expertise", upload_to=guarantee_file_path, max_length=255, blank=True
    )
    origin_certificate_scan = models.FileField(
        "scan certificat d'origine / facture", upload_to=guarantee_file_path, max_length=255, blank=True
    )

    # ------------------------------------------------------------------ #
    # Garantie financière
    # ------------------------------------------------------------------ #
    financial_type = models.CharField(
        "type de garantie financière", max_length=15,
        choices=FinancialType.choices, blank=True,
    )
    account_number = models.CharField("numéro de compte", max_length=100, blank=True)
    balance = models.DecimalField(
        "solde", max_digits=18, decimal_places=2, null=True, blank=True
    )
    remuneration_rate = models.DecimalField(
        "taux de rémunération (%)", max_digits=6, decimal_places=3,
        null=True, blank=True,
    )
    deposit_maturity_date = models.DateField(
        "date d'échéance du dépôt", null=True, blank=True
    )
    isin_code = models.CharField("code ISIN / nom de la valeur", max_length=150, blank=True)
    volatility_history = models.TextField("historique de volatilité", blank=True)
    security_discount = models.DecimalField(
        "décote de sécurité (%)", max_digits=6, decimal_places=3,
        null=True, blank=True,
    )
    pledge_deed_scan = models.FileField(
        "scan acte de nantissement / blocage", upload_to=guarantee_file_path, max_length=255, blank=True
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    last_valuation_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "garantie"
        verbose_name_plural = "garanties"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "status", "guarantee_type"])]

    def __str__(self):
        return f"{self.get_guarantee_type_display()} — {self.reference or self.pk}"

    def _loan_amount(self):
        """Montant du prêt de référence pour le calcul du ratio LTV."""
        if not self.application_id:
            return None
        from apps.credits.amounts import reference_amount

        return reference_amount(self.application)

    def save(self, *args, **kwargs):
        # Valeur actualisée : reflète la valeur la plus pertinente selon le type.
        if self.guarantee_type == self.GuaranteeType.MORTGAGE:
            if self.value_to_consider is not None:
                self.current_value = self.value_to_consider
        elif self.guarantee_type == self.GuaranteeType.PLEDGE:
            if self.pledge_category == PledgeCategory.VEHICLE and self.resale_value is not None:
                self.current_value = self.resale_value
        elif self.guarantee_type == self.GuaranteeType.FINANCIAL:
            if self.balance is not None:
                self.current_value = self.balance
        # Ratio LTV = valeur à considérer / montant du prêt.
        loan = self._loan_amount()
        if self.value_to_consider is not None and loan:
            ratio = (self.value_to_consider / Decimal(loan)).quantize(
                Decimal("0.0001")
            )
            # Le champ accepte 8 chiffres dont 4 décimales (max 9999.9999) :
            # on borne pour éviter une erreur de dépassement.
            if ratio >= Decimal("10000"):
                ratio = Decimal("9999.9999")
            self.ltv_ratio = ratio
        super().save(*args, **kwargs)


class GuaranteePhoto(TenantScopedModel):
    """Photo d'un bien mis en garantie (bien immobilier, objet de valeur…)."""

    guarantee = models.ForeignKey(
        Guarantee,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name="garantie",
    )
    image = models.ImageField(
        "photo", upload_to=guarantee_file_path, max_length=255
    )
    caption = models.CharField("légende", max_length=150, blank=True)

    class Meta:
        verbose_name = "photo de garantie"
        verbose_name_plural = "photos de garantie"
        ordering = ["created_at"]

    def __str__(self):
        return self.caption or f"Photo {self.pk}"


class GuaranteeDocument(TenantScopedModel):
    """Document libre associé à une garantie (intitulé + scan)."""

    guarantee = models.ForeignKey(
        Guarantee,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="garantie",
    )
    title = models.CharField("intitulé", max_length=200)
    file = models.FileField(
        "scan / fichier",
        upload_to=guarantee_file_path,
        max_length=255,
    )

    class Meta:
        verbose_name = "document de garantie"
        verbose_name_plural = "documents de garantie"
        ordering = ["created_at"]

    def __str__(self):
        return self.title or f"Document {self.pk}"


class GuaranteeJewelryItem(TenantScopedModel):
    """Composante d'un gage sur objet de valeur (ex. bague, bracelet, collier).

    Un même gage « bijou » peut être constitué de plusieurs pièces ; chacune
    est décrite ici individuellement (nature, poids, description).
    """

    guarantee = models.ForeignKey(
        Guarantee,
        on_delete=models.CASCADE,
        related_name="jewelry_items",
        verbose_name="garantie",
    )
    nature = models.CharField("nature du bijou", max_length=150)
    weight = models.DecimalField(
        "poids (g)", max_digits=10, decimal_places=3, null=True, blank=True
    )
    description = models.CharField("description", max_length=255, blank=True)

    class Meta:
        verbose_name = "composante de bijou"
        verbose_name_plural = "composantes de bijou"
        ordering = ["id"]

    def __str__(self):
        return self.nature or f"Bijou {self.pk}"


class GuaranteeMovement(TenantScopedModel):
    """Mouvement affectant une garantie (traçabilité complète)."""

    class MovementType(models.TextChoices):
        REVALUATION = "REVALUATION", "Réévaluation"
        RELEASE = "RELEASE", "Mainlevée"
        REALIZATION = "REALIZATION", "Réalisation"
        TRANSFER = "TRANSFER", "Transfert"
        RENEWAL = "RENEWAL", "Reconduction"

    guarantee = models.ForeignKey(
        Guarantee,
        on_delete=models.CASCADE,
        related_name="movements",
        verbose_name="garantie",
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    movement_date = models.DateField("date")
    value = models.DecimalField(
        "valeur", max_digits=18, decimal_places=2, null=True, blank=True
    )
    target_application = models.ForeignKey(
        "credits.CreditApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guarantee_transfers_in",
        verbose_name="dossier cible (transfert)",
    )
    comment = models.TextField("commentaire", blank=True)

    class Meta:
        verbose_name = "mouvement de garantie"
        verbose_name_plural = "mouvements de garantie"
        ordering = ["-movement_date"]

    def __str__(self):
        return f"{self.get_movement_type_display()} — {self.guarantee}"


class GuaranteeReleaseRequest(TenantScopedModel, AuthoredModel):
    """Demande de main levée — processus dédié avec circuit paramétrable."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        IN_APPROVAL = "IN_APPROVAL", "En validation"
        APPROVED = "APPROVED", "Approuvée"
        REJECTED = "REJECTED", "Rejetée"
        RETURNED = "RETURNED", "Retournée"
        COMPLETED = "COMPLETED", "Clôturée"
        CANCELLED = "CANCELLED", "Annulée"
        BLOCKED = "BLOCKED", "Bloquée (CBS)"

    reference = models.CharField("référence", max_length=30, blank=True, db_index=True)
    guarantee = models.ForeignKey(
        Guarantee,
        on_delete=models.PROTECT,
        related_name="release_requests",
        verbose_name="garantie",
    )
    application = models.ForeignKey(
        "credits.CreditApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_requests",
        verbose_name="dossier",
    )
    loan = models.ForeignKey(
        "credits.Loan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_requests",
        verbose_name="prêt",
    )
    agency = models.ForeignKey(
        "tenants.Agency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_requests",
        verbose_name="agence",
    )
    cbs_loan_reference = models.CharField(
        "référence prêt CBS", max_length=100, blank=True
    )
    cbs_client_id = models.CharField(
        "matricule client CBS", max_length=100, blank=True
    )
    cbs_settled = models.BooleanField("prêt soldé (CBS)", null=True, blank=True)
    cbs_outstanding = models.DecimalField(
        "encours CBS", max_digits=18, decimal_places=2, null=True, blank=True
    )
    cbs_currency = models.CharField(max_length=3, blank=True, default="XAF")
    cbs_checked_at = models.DateTimeField("vérifié CBS le", null=True, blank=True)
    cbs_raw = models.JSONField("réponse CBS", default=dict, blank=True)
    request_date = models.DateField(
        "date de la demande", null=True, blank=True
    )
    release_fees = models.DecimalField(
        "frais de main levée",
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    comment = models.TextField("commentaire", blank=True)
    completed_at = models.DateTimeField("clôturée le", null=True, blank=True)

    class Meta:
        verbose_name = "demande de main levée"
        verbose_name_plural = "demandes de main levée"
        ordering = ["-created_at"]
        permissions = [
            (
                "initiate_guaranteereleaserequest",
                "Peut initier une demande de main levée",
            ),
        ]

    def __str__(self):
        return self.reference or f"Main levée {self.pk}"


class DationRequest(TenantScopedModel, AuthoredModel):
    """Demande de dation en paiement — processus dédié avec circuit paramétrable."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        IN_APPROVAL = "IN_APPROVAL", "En validation"
        APPROVED = "APPROVED", "Approuvée"
        REJECTED = "REJECTED", "Rejetée"
        RETURNED = "RETURNED", "Retournée"
        COMPLETED = "COMPLETED", "Clôturée"
        CANCELLED = "CANCELLED", "Annulée"
        BLOCKED = "BLOCKED", "Bloquée (CBS)"

    reference = models.CharField("référence", max_length=30, blank=True, db_index=True)
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.PROTECT,
        related_name="dation_requests",
        verbose_name="client",
    )
    application = models.ForeignKey(
        "credits.CreditApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dation_requests",
        verbose_name="dossier",
    )
    agency = models.ForeignKey(
        "tenants.Agency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dation_requests",
        verbose_name="agence",
    )
    cbs_client_id = models.CharField("identifiant client CBS", max_length=100, blank=True)
    cbs_total_outstanding = models.DecimalField(
        "encours total CBS", max_digits=18, decimal_places=2, null=True, blank=True
    )
    cbs_currency = models.CharField(max_length=3, blank=True, default="XAF")
    cbs_checked_at = models.DateTimeField("vérifié CBS le", null=True, blank=True)
    cbs_raw = models.JSONField("réponse CBS", default=dict, blank=True)
    asset_description = models.TextField("description du bien cédé", blank=True)
    asset_value = models.DecimalField(
        "valeur du bien", max_digits=18, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    comment = models.TextField("commentaire", blank=True)
    resulting_guarantee = models.ForeignKey(
        Guarantee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dation_origins",
        verbose_name="garantie créée",
    )
    completed_at = models.DateTimeField("clôturée le", null=True, blank=True)

    class Meta:
        verbose_name = "demande de dation en paiement"
        verbose_name_plural = "demandes de dation en paiement"
        ordering = ["-created_at"]
        permissions = [
            (
                "initiate_dationrequest",
                "Peut initier une dation en paiement",
            ),
        ]

    def __str__(self):
        return self.reference or f"Dation {self.pk}"

    def assets_total_value(self):
        """Somme des valeurs des biens du dossier (lignes + fallback legacy)."""
        total = Decimal("0")
        has_lines = False
        for line in self.assets.all():
            has_lines = True
            if line.value is not None:
                total += line.value
        if has_lines:
            return total
        return self.asset_value or Decimal("0")

    def covers_claim(self):
        """True si la valeur totale des biens couvre (ou dépasse) la créance CBS."""
        claim = self.cbs_total_outstanding
        if claim is None:
            return None
        return self.assets_total_value() >= claim


class DationAsset(TenantScopedModel):
    """Bien intégré au dossier de dation (garantie existante ou bien additionnel)."""

    class Source(models.TextChoices):
        EXISTING_GUARANTEE = "EXISTING_GUARANTEE", "Garantie existante"
        ADDITIONAL = "ADDITIONAL", "Bien additionnel"

    dation = models.ForeignKey(
        DationRequest,
        on_delete=models.CASCADE,
        related_name="assets",
        verbose_name="demande de dation",
    )
    source = models.CharField(
        max_length=30, choices=Source.choices, default=Source.ADDITIONAL
    )
    guarantee = models.ForeignKey(
        Guarantee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="dation_asset_links",
        verbose_name="garantie source",
    )
    description = models.TextField("description", blank=True)
    value = models.DecimalField(
        "valeur", max_digits=18, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "bien de dation"
        verbose_name_plural = "biens de dation"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["dation", "guarantee"],
                condition=models.Q(guarantee__isnull=False),
                name="uniq_dation_guarantee_asset",
            ),
        ]

    def __str__(self):
        return self.description or f"Bien dation {self.pk}"

"""Recouvrement amiable et contentieux."""
from django.db import models
from django.utils import timezone

from apps.common.models import TenantScopedModel


class CollectionActionType(models.TextChoices):
    CALL = "CALL", "Appel téléphonique"
    SMS = "SMS", "SMS"
    EMAIL = "EMAIL", "Courriel"
    LETTER = "LETTER", "Courrier"
    VISIT = "VISIT", "Visite terrain"
    LEGAL = "LEGAL", "Acte judiciaire"


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
    next_action_date = models.DateField(
        "prochaine action", null=True, blank=True, db_index=True
    )
    next_action_type = models.CharField(
        "type prochaine action",
        max_length=10,
        blank=True,
        choices=CollectionActionType.choices,
    )
    next_action_note = models.CharField(
        "note prochaine action", max_length=255, blank=True
    )
    stage_changed_at = models.DateTimeField(
        "dernier changement de stade", null=True, blank=True
    )

    class Meta:
        verbose_name = "dossier de recouvrement"
        verbose_name_plural = "dossiers de recouvrement"
        ordering = ["-days_overdue"]
        indexes = [
            models.Index(fields=["tenant", "par_class", "stage"]),
            models.Index(
                fields=["tenant", "next_action_date"],
                name="coll_tenant_next_act_idx",
            ),
        ]

    def __str__(self):
        return f"Recouvrement {self.loan}"


class CollectionAction(TenantScopedModel):
    """Action de relance ou de suivi sur un dossier de recouvrement."""

    ActionType = CollectionActionType

    case = models.ForeignKey(
        CollectionCase,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name="dossier",
    )
    action_type = models.CharField(max_length=10, choices=CollectionActionType.choices)
    action_date = models.DateField("date")
    result = models.CharField("résultat", max_length=255, blank=True)
    comment = models.TextField("commentaire", blank=True)
    next_follow_up_date = models.DateField(
        "suivi prévu",
        null=True,
        blank=True,
        help_text="Si renseigné, met à jour la prochaine action du dossier.",
    )

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


class CollectionStageHistory(TenantScopedModel):
    """Historique des changements de stade d'un dossier."""

    case = models.ForeignKey(
        CollectionCase,
        on_delete=models.CASCADE,
        related_name="stage_history",
        verbose_name="dossier",
    )
    from_stage = models.CharField(
        max_length=20, choices=CollectionCase.Stage.choices, blank=True
    )
    to_stage = models.CharField(max_length=20, choices=CollectionCase.Stage.choices)
    reason = models.CharField("motif", max_length=255, blank=True)
    automatic = models.BooleanField("escalade automatique", default=False)
    changed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collection_stage_changes",
        verbose_name="modifié par",
    )

    class Meta:
        verbose_name = "historique de stade"
        verbose_name_plural = "historiques de stade"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.from_stage or '—'} → {self.to_stage}"


class CollectionEscalationRule(TenantScopedModel):
    """
    Règle d'escalade automatique : dès que days_overdue >= seuil,
    le dossier passe au stade cible (uniquement vers le haut).
    """

    min_days_overdue = models.PositiveIntegerField("seuil jours de retard")
    target_stage = models.CharField(
        max_length=20,
        choices=[
            (CollectionCase.Stage.AMICABLE, "Amiable"),
            (CollectionCase.Stage.PRECONTENTIOUS, "Précontentieux"),
            (CollectionCase.Stage.LITIGATION, "Contentieux"),
        ],
    )
    is_active = models.BooleanField("active", default=True)
    label = models.CharField("libellé", max_length=100, blank=True)

    class Meta:
        verbose_name = "règle d'escalade"
        verbose_name_plural = "règles d'escalade"
        ordering = ["min_days_overdue"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "min_days_overdue"],
                name="unique_escalation_days_per_tenant",
            )
        ]

    def __str__(self):
        return f"≥ {self.min_days_overdue}j → {self.target_stage}"


class LegalParty(TenantScopedModel):
    """Intervenant externe : cabinet, avocat, huissier, notaire, expert…"""

    class PartyType(models.TextChoices):
        LAW_FIRM = "LAW_FIRM", "Cabinet d'avocats"
        LAWYER = "LAWYER", "Avocat"
        BAILIFF = "BAILIFF", "Huissier"
        NOTARY = "NOTARY", "Notaire"
        EXPERT = "EXPERT", "Expert"
        OTHER = "OTHER", "Autre"

    party_type = models.CharField(max_length=20, choices=PartyType.choices, db_index=True)
    name = models.CharField("nom / raison sociale", max_length=255)
    registration_no = models.CharField(
        "n° barreau / agrément / RCCM", max_length=100, blank=True
    )
    contact_name = models.CharField("contact principal", max_length=255, blank=True)
    phone = models.CharField("téléphone", max_length=50, blank=True)
    email = models.EmailField("e-mail", blank=True)
    address = models.TextField("adresse", blank=True)
    notes = models.TextField("notes", blank=True)
    is_active = models.BooleanField("actif", default=True, db_index=True)

    class Meta:
        verbose_name = "intervenant juridique"
        verbose_name_plural = "intervenants juridiques"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "party_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_party_type_display()})"


class LitigationFile(TenantScopedModel):
    """Procédure contentieuse liée à un dossier de recouvrement (plusieurs possibles)."""

    class Status(models.TextChoices):
        PRE_LITIGATION = "PRE_LITIGATION", "Précontentieux"
        FILED = "FILED", "Introduite"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        JUDGMENT = "JUDGMENT", "Jugement rendu"
        ENFORCEMENT = "ENFORCEMENT", "Exécution"
        APPEAL = "APPEAL", "Appel / opposition"
        SETTLED = "SETTLED", "Transaction / accord"
        ABANDONED = "ABANDONED", "Abandonnée"
        CLOSED = "CLOSED", "Clôturée"
        # Anciens libellés conservés pour compatibilité API
        OPEN = "OPEN", "Ouvert"
        SUSPENDED = "SUSPENDED", "Suspendu"

    class ActionType(models.TextChoices):
        PAYMENT_ORDER = "PAYMENT_ORDER", "Injonction de payer"
        SUMMONS = "SUMMONS", "Assignation"
        SUMMARY = "SUMMARY", "Référé"
        ATTACHMENT = "ATTACHMENT", "Saisie-arrêt"
        OHADA = "OHADA", "Procédure OHADA"
        APPEAL = "APPEAL", "Appel"
        OTHER = "OTHER", "Autre"

    class JudgmentOutcome(models.TextChoices):
        FAVORABLE = "FAVORABLE", "Favorable"
        PARTIAL = "PARTIAL", "Partiellement favorable"
        UNFAVORABLE = "UNFAVORABLE", "Défavorable"
        SETTLEMENT = "SETTLEMENT", "Transaction"
        PENDING = "PENDING", "En attente"

    case = models.ForeignKey(
        CollectionCase,
        on_delete=models.CASCADE,
        related_name="litigations",
        verbose_name="dossier de recouvrement",
    )
    title = models.CharField("intitulé", max_length=255, blank=True)
    action_type = models.CharField(
        "nature de l'action",
        max_length=20,
        choices=ActionType.choices,
        default=ActionType.SUMMONS,
        blank=True,
    )
    court_name = models.CharField("juridiction", max_length=255, blank=True)
    court_registry = models.CharField("greffe", max_length=255, blank=True)
    case_reference = models.CharField("référence judiciaire / RG", max_length=100, blank=True)
    chamber = models.CharField("chambre", max_length=100, blank=True)

    law_firm = models.ForeignKey(
        LegalParty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="litigations_as_firm",
        verbose_name="cabinet mandaté",
        limit_choices_to={"party_type": LegalParty.PartyType.LAW_FIRM},
    )
    lawyer_party = models.ForeignKey(
        LegalParty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="litigations_as_lawyer",
        verbose_name="avocat référent",
    )
    bailiff_party = models.ForeignKey(
        LegalParty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="litigations_as_bailiff",
        verbose_name="huissier",
    )
    # Texte libre (repli / historique)
    lawyer = models.CharField("avocat (texte)", max_length=255, blank=True)
    bailiff = models.CharField("huissier (texte)", max_length=255, blank=True)

    mandate_start = models.DateField("début mandat", null=True, blank=True)
    mandate_end = models.DateField("fin mandat", null=True, blank=True)
    mandate_fee = models.DecimalField(
        "honoraires forfaitaires",
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    mandate_notes = models.TextField("notes de mission", blank=True)

    claimed_principal = models.DecimalField(
        "capital réclamé", max_digits=18, decimal_places=2, null=True, blank=True
    )
    claimed_interest = models.DecimalField(
        "intérêts réclamés", max_digits=18, decimal_places=2, null=True, blank=True
    )
    claimed_penalties = models.DecimalField(
        "pénalités réclamées", max_digits=18, decimal_places=2, null=True, blank=True
    )
    claimed_costs = models.DecimalField(
        "frais réclamés", max_digits=18, decimal_places=2, null=True, blank=True
    )
    claimed_total = models.DecimalField(
        "total réclamé", max_digits=18, decimal_places=2, null=True, blank=True
    )

    notice_date = models.DateField("date mise en demeure", null=True, blank=True)
    filing_date = models.DateField("date d'introduction", null=True, blank=True)
    service_date = models.DateField("date de signification", null=True, blank=True)
    first_hearing_date = models.DateField("première audience", null=True, blank=True)
    hearing_date = models.DateField(
        "prochaine audience", null=True, blank=True, db_index=True
    )
    hearing_time = models.TimeField("heure audience", null=True, blank=True)
    hearing_location = models.CharField("lieu audience", max_length=255, blank=True)

    judgment_date = models.DateField("date du jugement", null=True, blank=True)
    judgment_outcome = models.CharField(
        "sens du jugement",
        max_length=20,
        choices=JudgmentOutcome.choices,
        blank=True,
    )
    judgment_amount = models.DecimalField(
        "montant accordé", max_digits=18, decimal_places=2, null=True, blank=True
    )
    judgment_enforceable = models.BooleanField("exécutoire", default=False)
    judgment_served_at = models.DateField(
        "date signification jugement", null=True, blank=True
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PRE_LITIGATION, db_index=True
    )
    notes = models.TextField("notes", blank=True)

    related_guarantees = models.ManyToManyField(
        "guarantees.Guarantee",
        blank=True,
        related_name="litigation_files",
        verbose_name="garanties concernées",
    )

    class Meta:
        verbose_name = "dossier contentieux"
        verbose_name_plural = "dossiers contentieux"
        ordering = ["-hearing_date", "-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "hearing_date"]),
        ]

    def __str__(self):
        return self.title or self.case_reference or f"Contentieux {self.pk}"

    def recompute_next_hearing(self):
        """Met à jour hearing_date depuis la prochaine audience planifiée."""
        nxt = (
            self.events.filter(
                event_type=LitigationEvent.EventType.HEARING,
                event_date__gte=timezone.localdate(),
            )
            .order_by("event_date")
            .first()
        )
        if nxt:
            self.hearing_date = nxt.event_date
            self.hearing_time = nxt.event_time
            self.hearing_location = nxt.location or self.hearing_location
            self.save(
                update_fields=[
                    "hearing_date",
                    "hearing_time",
                    "hearing_location",
                    "updated_at",
                ]
            )


class LitigationEvent(TenantScopedModel):
    """Événement du dossier contentieux (audience, saisie, jugement…)."""

    class EventType(models.TextChoices):
        NOTICE = "NOTICE", "Mise en demeure"
        FILING = "FILING", "Introduction / dépôt"
        HEARING = "HEARING", "Audience"
        BRIEF = "BRIEF", "Conclusions / mémoire"
        JUDGMENT = "JUDGMENT", "Jugement / ordonnance"
        SERVICE = "SERVICE", "Signification"
        SEIZURE = "SEIZURE", "Saisie"
        APPEAL = "APPEAL", "Appel / opposition"
        SETTLEMENT = "SETTLEMENT", "Transaction / désistement"
        OTHER = "OTHER", "Autre"

    litigation = models.ForeignKey(
        LitigationFile,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="dossier contentieux",
    )
    event_date = models.DateField("date", db_index=True)
    event_time = models.TimeField("heure", null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    location = models.CharField("lieu", max_length=255, blank=True)
    outcome = models.CharField("résultat", max_length=255, blank=True)
    amount = models.DecimalField(
        "montant lié", max_digits=18, decimal_places=2, null=True, blank=True
    )
    postponed = models.BooleanField("reportée", default=False)
    next_date = models.DateField("date de suite", null=True, blank=True)
    performed_by = models.ForeignKey(
        LegalParty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="litigation_events",
        verbose_name="intervenant",
    )
    comment = models.TextField("commentaire", blank=True)

    class Meta:
        verbose_name = "événement contentieux"
        verbose_name_plural = "événements contentieux"
        ordering = ["-event_date", "-created_at"]

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.event_date}"


class LitigationSeizure(TenantScopedModel):
    """Mesure d'exécution / saisie structurée."""

    class SeizureType(models.TextChoices):
        ATTRIBUTION = "ATTRIBUTION", "Saisie-attribution"
        MOVABLE = "MOVABLE", "Saisie mobilière"
        IMMOVABLE = "IMMOVABLE", "Saisie immobilière"
        SALE = "SALE", "Vente forcée"
        WAGE = "WAGE", "Saisie sur salaire"
        OTHER = "OTHER", "Autre"

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planifiée"
        DONE = "DONE", "Réalisée"
        FAILED = "FAILED", "Échouée"
        CANCELLED = "CANCELLED", "Annulée"

    litigation = models.ForeignKey(
        LitigationFile,
        on_delete=models.CASCADE,
        related_name="seizures",
        verbose_name="dossier contentieux",
    )
    seizure_type = models.CharField(max_length=20, choices=SeizureType.choices)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNED
    )
    seizure_date = models.DateField("date", null=True, blank=True)
    amount = models.DecimalField(
        "montant", max_digits=18, decimal_places=2, null=True, blank=True
    )
    bailiff = models.ForeignKey(
        LegalParty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seizures",
        verbose_name="huissier",
    )
    guarantee = models.ForeignKey(
        "guarantees.Guarantee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="litigation_seizures",
        verbose_name="garantie liée",
    )
    report_reference = models.CharField("réf. PV", max_length=100, blank=True)
    inventory = models.TextField("inventaire / description", blank=True)
    notes = models.TextField("notes", blank=True)

    class Meta:
        verbose_name = "saisie"
        verbose_name_plural = "saisies"
        ordering = ["-seizure_date", "-created_at"]

    def __str__(self):
        return f"{self.get_seizure_type_display()} — {self.seizure_date or '—'}"


class LitigationCost(TenantScopedModel):
    """Frais et honoraires du contentieux."""

    class CostType(models.TextChoices):
        RETAINER = "RETAINER", "Provision"
        FEE = "FEE", "Honoraire"
        REGISTRY = "REGISTRY", "Frais de greffe"
        BAILIFF = "BAILIFF", "Frais d'huissier"
        TRAVEL = "TRAVEL", "Déplacement"
        OTHER = "OTHER", "Autre"

    litigation = models.ForeignKey(
        LitigationFile,
        on_delete=models.CASCADE,
        related_name="costs",
        verbose_name="dossier contentieux",
    )
    cost_type = models.CharField(max_length=20, choices=CostType.choices)
    label = models.CharField("libellé", max_length=255, blank=True)
    amount = models.DecimalField("montant", max_digits=18, decimal_places=2)
    cost_date = models.DateField("date")
    is_paid = models.BooleanField("payé", default=False)
    recoverable = models.BooleanField("récupérable", default=True)
    party = models.ForeignKey(
        LegalParty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="costs",
        verbose_name="bénéficiaire",
    )
    notes = models.CharField("notes", max_length=255, blank=True)

    class Meta:
        verbose_name = "frais contentieux"
        verbose_name_plural = "frais contentieux"
        ordering = ["-cost_date", "-created_at"]

    def __str__(self):
        return f"{self.get_cost_type_display()} — {self.amount}"


class LoanRestructure(TenantScopedModel):
    """Restructuration d'un prêt (nouvel échéancier sur le capital restant dû)."""

    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Appliquée"
        CANCELLED = "CANCELLED", "Annulée"

    case = models.ForeignKey(
        CollectionCase,
        on_delete=models.CASCADE,
        related_name="restructures",
        verbose_name="dossier",
    )
    loan = models.ForeignKey(
        "credits.Loan",
        on_delete=models.CASCADE,
        related_name="restructures",
        verbose_name="prêt",
    )
    effective_date = models.DateField("date d'effet")
    previous_duration_months = models.PositiveIntegerField()
    new_duration_months = models.PositiveIntegerField("nouvelle durée (mois)")
    previous_rate = models.DecimalField(max_digits=6, decimal_places=3)
    new_rate = models.DecimalField("nouveau taux (%)", max_digits=6, decimal_places=3)
    outstanding_principal = models.DecimalField(
        "capital restant dû", max_digits=18, decimal_places=2
    )
    reason = models.CharField("motif", max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.APPLIED
    )
    applied_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan_restructures",
    )

    class Meta:
        verbose_name = "restructuration"
        verbose_name_plural = "restructurations"
        ordering = ["-effective_date", "-created_at"]

    def __str__(self):
        return f"Restructuration {self.loan_id} — {self.effective_date}"


class WriteOff(TenantScopedModel):
    """Passage en perte / défaut d'un prêt."""

    case = models.ForeignKey(
        CollectionCase,
        on_delete=models.CASCADE,
        related_name="write_offs",
        verbose_name="dossier",
    )
    loan = models.ForeignKey(
        "credits.Loan",
        on_delete=models.CASCADE,
        related_name="write_offs",
        verbose_name="prêt",
    )
    amount = models.DecimalField("montant passé en perte", max_digits=18, decimal_places=2)
    write_off_date = models.DateField("date")
    reason = models.CharField("motif", max_length=255, blank=True)
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan_write_offs",
    )

    class Meta:
        verbose_name = "passage en perte"
        verbose_name_plural = "passages en perte"
        ordering = ["-write_off_date", "-created_at"]

    def __str__(self):
        return f"Write-off {self.amount} — {self.write_off_date}"

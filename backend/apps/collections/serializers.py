from rest_framework import serializers

from apps.credits.models import Installment
from apps.guarantees.models import Guarantee

from .models import (
    CollectionAction,
    CollectionCase,
    CollectionEscalationRule,
    CollectionStageHistory,
    LegalParty,
    LitigationCost,
    LitigationEvent,
    LitigationFile,
    LitigationSeizure,
    LoanRestructure,
    PaymentPromise,
    Repayment,
    WriteOff,
)
from .services import record_repayment, set_next_action


class RepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repayment
        fields = [
            "id", "loan", "amount", "payment_date", "reference", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        loan = validated_data["loan"]
        repayment, _ = record_repayment(
            loan=loan,
            amount=validated_data["amount"],
            payment_date=validated_data.get("payment_date"),
            reference=validated_data.get("reference", ""),
            tenant_id=getattr(loan, "tenant_id", None),
        )
        return repayment


class CollectionActionSerializer(serializers.ModelSerializer):
    action_type_display = serializers.CharField(
        source="get_action_type_display", read_only=True
    )

    class Meta:
        model = CollectionAction
        fields = [
            "id", "case", "action_type", "action_type_display",
            "action_date", "result", "comment", "next_follow_up_date",
        ]
        read_only_fields = ["id", "action_type_display"]

    def create(self, validated_data):
        action = super().create(validated_data)
        follow = validated_data.get("next_follow_up_date")
        if follow:
            set_next_action(
                action.case,
                action_date=follow,
                action_type=action.action_type,
                note=action.result or action.comment[:255],
            )
        return action


class PaymentPromiseSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = PaymentPromise
        fields = [
            "id", "case", "amount", "promised_date", "status", "status_display",
        ]
        read_only_fields = ["id", "status_display"]


class CollectionStageHistorySerializer(serializers.ModelSerializer):
    from_stage_display = serializers.SerializerMethodField()
    to_stage_display = serializers.CharField(
        source="get_to_stage_display", read_only=True
    )
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CollectionStageHistory
        fields = [
            "id", "from_stage", "from_stage_display", "to_stage", "to_stage_display",
            "reason", "automatic", "changed_by", "changed_by_name", "created_at",
        ]
        read_only_fields = fields

    def get_from_stage_display(self, obj):
        if not obj.from_stage:
            return "—"
        return obj.get_from_stage_display()

    def get_changed_by_name(self, obj):
        user = obj.changed_by
        if user is None:
            return None
        return user.get_full_name() or user.username


class CollectionEscalationRuleSerializer(serializers.ModelSerializer):
    target_stage_display = serializers.CharField(
        source="get_target_stage_display", read_only=True
    )

    class Meta:
        model = CollectionEscalationRule
        fields = [
            "id", "min_days_overdue", "target_stage", "target_stage_display",
            "is_active", "label", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "target_stage_display", "created_at", "updated_at"]


class GuaranteeBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    guarantee_type = serializers.CharField()
    guarantee_type_display = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    description = serializers.CharField()
    current_value = serializers.DecimalField(max_digits=18, decimal_places=2)


class DationBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    created_at = serializers.DateTimeField()


class CollectionCaseListSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    par_class_display = serializers.CharField(
        source="get_par_class_display", read_only=True
    )
    next_action_type_display = serializers.SerializerMethodField()
    loan_status = serializers.CharField(source="loan.status", read_only=True)
    loan_principal = serializers.DecimalField(
        source="loan.principal", max_digits=18, decimal_places=2, read_only=True
    )
    application_id = serializers.UUIDField(
        source="loan.application_id", read_only=True
    )
    application_reference = serializers.CharField(
        source="loan.application.reference", read_only=True, default=""
    )
    product_name = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    client_id = serializers.SerializerMethodField()
    agency_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()
    pending_promises_count = serializers.SerializerMethodField()
    guarantees_count = serializers.SerializerMethodField()

    class Meta:
        model = CollectionCase
        fields = [
            "id", "loan", "loan_status", "loan_principal",
            "application_id", "application_reference", "product_name",
            "client_id", "client_name", "agency_name",
            "stage", "stage_display", "par_class", "par_class_display",
            "days_overdue", "overdue_amount", "assigned_to", "assigned_to_name",
            "next_action_date", "next_action_type", "next_action_type_display",
            "next_action_note", "stage_changed_at",
            "next_due_date", "pending_promises_count", "guarantees_count",
            "created_at",
        ]
        read_only_fields = fields

    def get_product_name(self, obj):
        product = getattr(obj.loan.application, "product", None)
        return product.label if product else "—"

    def get_client_name(self, obj):
        client = getattr(obj.loan.application, "client", None)
        if client is None:
            return "—"
        return client.display_name

    def get_client_id(self, obj):
        client = getattr(obj.loan.application, "client", None)
        return str(client.id) if client else None

    def get_agency_name(self, obj):
        agency = getattr(obj.loan.application, "agency", None)
        return agency.name if agency else "—"

    def get_assigned_to_name(self, obj):
        user = obj.assigned_to
        if user is None:
            return None
        return user.get_full_name() or user.username

    def get_next_action_type_display(self, obj):
        if not obj.next_action_type:
            return ""
        return obj.get_next_action_type_display()

    def get_next_due_date(self, obj):
        inst = (
            obj.loan.installments.exclude(status=Installment.Status.PAID)
            .order_by("due_date")
            .first()
        )
        return inst.due_date if inst else None

    def get_pending_promises_count(self, obj):
        if hasattr(obj, "pending_promises_count"):
            return obj.pending_promises_count
        return obj.promises.filter(status=PaymentPromise.Status.PENDING).count()

    def get_guarantees_count(self, obj):
        app = obj.loan.application
        if app is None:
            return 0
        return app.guarantees.count()


class LegalPartySerializer(serializers.ModelSerializer):
    party_type_display = serializers.CharField(
        source="get_party_type_display", read_only=True
    )

    class Meta:
        model = LegalParty
        fields = [
            "id", "party_type", "party_type_display", "name", "registration_no",
            "contact_name", "phone", "email", "address", "notes", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "party_type_display", "created_at", "updated_at",
        ]


class LegalPartyBriefSerializer(serializers.ModelSerializer):
    party_type_display = serializers.CharField(
        source="get_party_type_display", read_only=True
    )

    class Meta:
        model = LegalParty
        fields = [
            "id", "party_type", "party_type_display", "name",
            "phone", "email", "is_active",
        ]
        read_only_fields = fields


class LitigationEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(
        source="get_event_type_display", read_only=True
    )
    performed_by_detail = LegalPartyBriefSerializer(
        source="performed_by", read_only=True
    )

    class Meta:
        model = LitigationEvent
        fields = [
            "id", "litigation", "event_date", "event_time", "event_type",
            "event_type_display", "location", "outcome", "amount", "postponed",
            "next_date", "performed_by", "performed_by_detail", "comment",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "event_type_display", "performed_by_detail",
            "created_at", "updated_at",
        ]


class LitigationEventCreateSerializer(serializers.Serializer):
    litigation_id = serializers.UUIDField(required=False, allow_null=True)
    event_date = serializers.DateField()
    event_time = serializers.TimeField(required=False, allow_null=True)
    event_type = serializers.ChoiceField(choices=LitigationEvent.EventType.choices)
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    outcome = serializers.CharField(required=False, allow_blank=True, max_length=255)
    amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    postponed = serializers.BooleanField(required=False, default=False)
    next_date = serializers.DateField(required=False, allow_null=True)
    performed_by = serializers.PrimaryKeyRelatedField(
        # Manager (pas .all()) : le queryset tenant est résolu à la validation.
        queryset=LegalParty.objects, required=False, allow_null=True
    )
    comment = serializers.CharField(required=False, allow_blank=True)


class LitigationSeizureSerializer(serializers.ModelSerializer):
    seizure_type_display = serializers.CharField(
        source="get_seizure_type_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    bailiff_detail = LegalPartyBriefSerializer(source="bailiff", read_only=True)

    class Meta:
        model = LitigationSeizure
        fields = [
            "id", "litigation", "seizure_type", "seizure_type_display",
            "status", "status_display", "seizure_date", "amount",
            "bailiff", "bailiff_detail", "guarantee", "report_reference",
            "inventory", "notes", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "seizure_type_display", "status_display", "bailiff_detail",
            "created_at", "updated_at",
        ]


class LitigationSeizureCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LitigationSeizure
        fields = [
            "seizure_type", "status", "seizure_date", "amount", "bailiff",
            "guarantee", "report_reference", "inventory", "notes",
        ]


class LitigationCostSerializer(serializers.ModelSerializer):
    cost_type_display = serializers.CharField(
        source="get_cost_type_display", read_only=True
    )
    party_detail = LegalPartyBriefSerializer(source="party", read_only=True)

    class Meta:
        model = LitigationCost
        fields = [
            "id", "litigation", "cost_type", "cost_type_display", "label",
            "amount", "cost_date", "is_paid", "recoverable", "party",
            "party_detail", "notes", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "cost_type_display", "party_detail", "created_at", "updated_at",
        ]


class LitigationCostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LitigationCost
        fields = [
            "cost_type", "label", "amount", "cost_date", "is_paid",
            "recoverable", "party", "notes",
        ]


class LitigationFileSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    action_type_display = serializers.CharField(
        source="get_action_type_display", read_only=True
    )
    judgment_outcome_display = serializers.SerializerMethodField()
    law_firm_detail = LegalPartyBriefSerializer(source="law_firm", read_only=True)
    lawyer_party_detail = LegalPartyBriefSerializer(
        source="lawyer_party", read_only=True
    )
    bailiff_party_detail = LegalPartyBriefSerializer(
        source="bailiff_party", read_only=True
    )
    events = LitigationEventSerializer(many=True, read_only=True)
    seizures = LitigationSeizureSerializer(many=True, read_only=True)
    costs = LitigationCostSerializer(many=True, read_only=True)
    related_guarantee_ids = serializers.PrimaryKeyRelatedField(
        source="related_guarantees", many=True, read_only=True
    )

    class Meta:
        model = LitigationFile
        fields = [
            "id", "case", "title", "action_type", "action_type_display",
            "court_name", "court_registry", "case_reference", "chamber",
            "law_firm", "law_firm_detail",
            "lawyer_party", "lawyer_party_detail",
            "bailiff_party", "bailiff_party_detail",
            "lawyer", "bailiff",
            "mandate_start", "mandate_end", "mandate_fee", "mandate_notes",
            "claimed_principal", "claimed_interest", "claimed_penalties",
            "claimed_costs", "claimed_total",
            "notice_date", "filing_date", "service_date",
            "first_hearing_date", "hearing_date", "hearing_time",
            "hearing_location",
            "judgment_date", "judgment_outcome", "judgment_outcome_display",
            "judgment_amount", "judgment_enforceable", "judgment_served_at",
            "status", "status_display", "notes",
            "related_guarantee_ids",
            "events", "seizures", "costs",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "action_type_display", "status_display",
            "judgment_outcome_display",
            "law_firm_detail", "lawyer_party_detail", "bailiff_party_detail",
            "related_guarantee_ids", "events", "seizures", "costs",
            "created_at", "updated_at",
        ]

    def get_judgment_outcome_display(self, obj):
        if not obj.judgment_outcome:
            return ""
        return obj.get_judgment_outcome_display()


class LitigationFileWriteSerializer(serializers.Serializer):
    """Création / mise à jour d'une procédure contentieuse."""

    litigation_id = serializers.UUIDField(required=False, allow_null=True)
    case = serializers.PrimaryKeyRelatedField(
        queryset=CollectionCase.objects, required=False
    )
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    action_type = serializers.ChoiceField(
        choices=LitigationFile.ActionType.choices, required=False
    )
    court_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    court_registry = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    case_reference = serializers.CharField(
        required=False, allow_blank=True, max_length=100
    )
    chamber = serializers.CharField(required=False, allow_blank=True, max_length=100)
    law_firm = serializers.PrimaryKeyRelatedField(
        queryset=LegalParty.objects, required=False, allow_null=True
    )
    lawyer_party = serializers.PrimaryKeyRelatedField(
        queryset=LegalParty.objects, required=False, allow_null=True
    )
    bailiff_party = serializers.PrimaryKeyRelatedField(
        queryset=LegalParty.objects, required=False, allow_null=True
    )
    lawyer = serializers.CharField(required=False, allow_blank=True, max_length=255)
    bailiff = serializers.CharField(required=False, allow_blank=True, max_length=255)
    mandate_start = serializers.DateField(required=False, allow_null=True)
    mandate_end = serializers.DateField(required=False, allow_null=True)
    mandate_fee = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    mandate_notes = serializers.CharField(required=False, allow_blank=True)
    claimed_principal = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    claimed_interest = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    claimed_penalties = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    claimed_costs = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    claimed_total = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    notice_date = serializers.DateField(required=False, allow_null=True)
    filing_date = serializers.DateField(required=False, allow_null=True)
    service_date = serializers.DateField(required=False, allow_null=True)
    first_hearing_date = serializers.DateField(required=False, allow_null=True)
    hearing_date = serializers.DateField(required=False, allow_null=True)
    hearing_time = serializers.TimeField(required=False, allow_null=True)
    hearing_location = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    judgment_date = serializers.DateField(required=False, allow_null=True)
    judgment_outcome = serializers.ChoiceField(
        choices=LitigationFile.JudgmentOutcome.choices,
        required=False,
        allow_blank=True,
    )
    judgment_amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True
    )
    judgment_enforceable = serializers.BooleanField(required=False)
    judgment_served_at = serializers.DateField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=LitigationFile.Status.choices, required=False
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    related_guarantee_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Guarantee.objects,
        required=False,
    )


# Alias rétrocompat pour l'action case/litigation
LitigationUpsertSerializer = LitigationFileWriteSerializer


class LoanRestructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRestructure
        fields = [
            "id", "effective_date", "previous_duration_months",
            "new_duration_months", "previous_rate", "new_rate",
            "outstanding_principal", "reason", "status", "created_at",
        ]
        read_only_fields = fields


class WriteOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = WriteOff
        fields = [
            "id", "amount", "write_off_date", "reason", "created_at",
        ]
        read_only_fields = fields


_CLOSED_LITIGATION_STATUSES = frozenset({
    LitigationFile.Status.CLOSED,
    LitigationFile.Status.ABANDONED,
    LitigationFile.Status.SETTLED,
})


class CollectionCaseSerializer(CollectionCaseListSerializer):
    actions = CollectionActionSerializer(many=True, read_only=True)
    promises = PaymentPromiseSerializer(many=True, read_only=True)
    stage_history = CollectionStageHistorySerializer(many=True, read_only=True)
    restructures = LoanRestructureSerializer(many=True, read_only=True)
    write_offs = WriteOffSerializer(many=True, read_only=True)
    litigations = LitigationFileSerializer(many=True, read_only=True)
    litigation = serializers.SerializerMethodField()
    repayments = serializers.SerializerMethodField()
    installments = serializers.SerializerMethodField()
    guarantees = serializers.SerializerMethodField()
    dation_requests = serializers.SerializerMethodField()
    outstanding_principal = serializers.SerializerMethodField()
    core_banking_reference = serializers.CharField(
        source="loan.core_banking_reference", read_only=True
    )

    class Meta(CollectionCaseListSerializer.Meta):
        fields = CollectionCaseListSerializer.Meta.fields + [
            "actions", "promises", "stage_history", "restructures", "write_offs",
            "litigations", "litigation", "repayments", "installments",
            "guarantees", "dation_requests", "outstanding_principal",
            "core_banking_reference",
        ]

    def get_litigation(self, obj):
        """Dernière procédure ouverte (compat API historique)."""
        prefetched = getattr(obj, "_prefetched_objects_cache", None)
        if prefetched is not None and "litigations" in prefetched:
            open_lits = [
                lit for lit in obj.litigations.all()
                if lit.status not in _CLOSED_LITIGATION_STATUSES
            ]
            open_lits.sort(key=lambda lit: lit.created_at, reverse=True)
            lit = open_lits[0] if open_lits else None
        else:
            lit = (
                obj.litigations.exclude(status__in=_CLOSED_LITIGATION_STATUSES)
                .order_by("-created_at")
                .first()
            )
        if lit is None:
            return None
        return LitigationFileSerializer(lit, context=self.context).data

    def get_outstanding_principal(self, obj):
        from .services import outstanding_principal

        return outstanding_principal(obj.loan)

    def get_repayments(self, obj):
        qs = obj.loan.repayments.all().order_by("-payment_date", "-created_at")
        return RepaymentSerializer(qs, many=True).data

    def get_installments(self, obj):
        rows = []
        for inst in obj.loan.installments.all().order_by("number"):
            rows.append({
                "id": inst.id,
                "number": inst.number,
                "due_date": inst.due_date,
                "total_due": inst.total_due,
                "amount_paid": inst.amount_paid,
                "balance": inst.balance,
                "status": inst.status,
                "status_display": inst.get_status_display(),
            })
        return rows

    def get_guarantees(self, obj):
        app = obj.loan.application
        if app is None:
            return []
        rows = []
        for g in app.guarantees.all().order_by("-created_at")[:20]:
            rows.append({
                "id": g.id,
                "guarantee_type": g.guarantee_type,
                "guarantee_type_display": g.get_guarantee_type_display(),
                "status": g.status,
                "status_display": g.get_status_display(),
                "description": g.description or "",
                "current_value": g.current_value,
            })
        return rows

    def get_dation_requests(self, obj):
        app = obj.loan.application
        if app is None:
            return []
        rows = []
        for d in app.dation_requests.all().order_by("-created_at")[:20]:
            rows.append({
                "id": d.id,
                "status": d.status,
                "status_display": d.get_status_display(),
                "created_at": d.created_at,
            })
        return rows


class CaseRepaymentCreateSerializer(serializers.Serializer):
    """Encaissement saisi depuis la fiche dossier de recouvrement."""

    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=0.01)
    payment_date = serializers.DateField(required=False)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def create(self, validated_data):
        case: CollectionCase = self.context["case"]
        repayment, _ = record_repayment(
            loan=case.loan,
            amount=validated_data["amount"],
            payment_date=validated_data.get("payment_date"),
            reference=validated_data.get("reference", ""),
            tenant_id=case.tenant_id,
        )
        return repayment


class CaseAssignSerializer(serializers.Serializer):
    assigned_to = serializers.UUIDField(allow_null=True, required=False)


class CaseStageSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=CollectionCase.Stage.choices)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class CaseNextActionSerializer(serializers.Serializer):
    next_action_date = serializers.DateField(allow_null=True, required=False)
    next_action_type = serializers.ChoiceField(
        choices=CollectionAction.ActionType.choices,
        required=False,
        allow_blank=True,
    )
    next_action_note = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )

    def save(self, **kwargs):
        case: CollectionCase = self.context["case"]
        data = self.validated_data
        return set_next_action(
            case,
            action_date=data.get("next_action_date"),
            action_type=data.get("next_action_type", ""),
            note=data.get("next_action_note", ""),
        )


class CaseRestructureSerializer(serializers.Serializer):
    new_duration_months = serializers.IntegerField(min_value=1, max_value=360)
    new_rate = serializers.DecimalField(
        max_digits=6, decimal_places=3, required=False, allow_null=True
    )
    first_due_date = serializers.DateField(required=False)
    effective_date = serializers.DateField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class CaseWriteOffSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, required=False, allow_null=True, min_value=0.01
    )
    write_off_date = serializers.DateField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class CaseReminderSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(
        choices=[("EMAIL", "E-mail"), ("SMS", "SMS")],
        default="EMAIL",
    )


class LitigationDocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    category = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="Code catégorie GED (ex. LIT_JUDGMENT). Défaut : LIT_OTHER.",
    )

    def validate_file(self, value):
        from apps.common.upload_validation import (
            resolve_tenant_from_context,
            validate_uploaded_file,
        )

        return validate_uploaded_file(
            value,
            tenant=resolve_tenant_from_context(self.context),
            check_quota=True,
        )

from rest_framework import serializers

from .models import (
    CollectionAction,
    CollectionCase,
    PaymentPromise,
    Repayment,
)
from .services import record_repayment


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
            "action_date", "result", "comment",
        ]
        read_only_fields = ["id", "action_type_display"]


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


class InstallmentBriefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.IntegerField()
    due_date = serializers.DateField()
    total_due = serializers.DecimalField(max_digits=18, decimal_places=2)
    amount_paid = serializers.DecimalField(max_digits=18, decimal_places=2)
    balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    status = serializers.CharField()
    status_display = serializers.CharField()


class CollectionCaseListSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    par_class_display = serializers.CharField(
        source="get_par_class_display", read_only=True
    )
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
    client_name = serializers.SerializerMethodField()
    agency_name = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = CollectionCase
        fields = [
            "id", "loan", "loan_status", "loan_principal",
            "application_id", "application_reference", "client_name", "agency_name",
            "stage", "stage_display", "par_class", "par_class_display",
            "days_overdue", "overdue_amount", "assigned_to", "assigned_to_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_client_name(self, obj):
        client = getattr(obj.loan.application, "client", None)
        if client is None:
            return "—"
        return client.display_name

    def get_agency_name(self, obj):
        agency = getattr(obj.loan.application, "agency", None)
        return agency.name if agency else "—"

    def get_assigned_to_name(self, obj):
        user = obj.assigned_to
        if user is None:
            return None
        return user.get_full_name() or user.username


class CollectionCaseSerializer(CollectionCaseListSerializer):
    actions = CollectionActionSerializer(many=True, read_only=True)
    promises = PaymentPromiseSerializer(many=True, read_only=True)
    repayments = serializers.SerializerMethodField()
    installments = serializers.SerializerMethodField()
    core_banking_reference = serializers.CharField(
        source="loan.core_banking_reference", read_only=True
    )

    class Meta(CollectionCaseListSerializer.Meta):
        fields = CollectionCaseListSerializer.Meta.fields + [
            "actions", "promises", "repayments", "installments",
            "core_banking_reference",
        ]

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

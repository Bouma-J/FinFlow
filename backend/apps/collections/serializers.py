from rest_framework import serializers

from .models import (
    CollectionAction,
    CollectionCase,
    PaymentPromise,
    Repayment,
)


class RepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repayment
        fields = ["id", "loan", "amount", "payment_date", "reference", "created_at"]
        read_only_fields = ["id", "created_at"]


class CollectionActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionAction
        fields = [
            "id", "case", "action_type", "action_date", "result", "comment",
        ]
        read_only_fields = ["id"]


class PaymentPromiseSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPromise
        fields = ["id", "case", "amount", "promised_date", "status"]
        read_only_fields = ["id"]


class CollectionCaseSerializer(serializers.ModelSerializer):
    actions = CollectionActionSerializer(many=True, read_only=True)
    promises = PaymentPromiseSerializer(many=True, read_only=True)
    par_class_display = serializers.CharField(
        source="get_par_class_display", read_only=True
    )

    class Meta:
        model = CollectionCase
        fields = [
            "id", "loan", "stage", "par_class", "par_class_display",
            "days_overdue", "overdue_amount", "assigned_to",
            "actions", "promises", "created_at",
        ]
        read_only_fields = [
            "id", "par_class", "days_overdue", "overdue_amount", "created_at",
        ]

from django.contrib import admin

from .models import (
    AnalysisThreshold,
    CreditApplication,
    CreditDocument,
    CreditInstructionPolicy,
    FieldVisit,
    FinancialAnalysis,
    Installment,
    Loan,
    LoanRestructuringRequest,
    LoanWriteOffRequest,
    StockPhoto,
)


class FinancialAnalysisInline(admin.StackedInline):
    model = FinancialAnalysis
    extra = 0


class StockPhotoInline(admin.TabularInline):
    model = StockPhoto
    extra = 0
    fields = ["image", "caption"]


class CreditDocumentInline(admin.TabularInline):
    model = CreditDocument
    extra = 0
    fields = ["label", "file"]


@admin.register(CreditApplication)
class CreditApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "reference", "client", "product", "amount_requested",
        "status", "tenant", "created_at",
    ]
    list_filter = ["status", "currency", "periodicity", "tenant"]
    search_fields = ["reference"]
    readonly_fields = ["reference", "last_due_date"]
    inlines = [FinancialAnalysisInline, StockPhotoInline, CreditDocumentInline]


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = [
        "application", "principal", "interest_rate",
        "duration_months", "status", "tenant",
    ]
    list_filter = ["status", "tenant"]
    inlines = [InstallmentInline]


@admin.register(FieldVisit)
class FieldVisitAdmin(admin.ModelAdmin):
    list_display = ["application", "visit_date", "visited_by", "tenant"]
    list_filter = ["tenant"]


@admin.register(AnalysisThreshold)
class AnalysisThresholdAdmin(admin.ModelAdmin):
    list_display = [
        "tenant", "max_debt_ratio", "min_dscr", "max_gearing",
        "min_guarantee_coverage", "stress_pct",
        "haircut_mortgage", "haircut_vehicle", "haircut_jewelry",
    ]
    list_filter = ["tenant"]
    fields = [
        "tenant",
        "max_debt_ratio", "min_dscr", "max_leverage_ratio",
        "min_living_wage_per_capita", "min_interest_coverage",
        "max_gearing", "min_financial_autonomy", "min_current_ratio",
        "min_guarantee_coverage", "stress_pct",
        "transferable_quota_fraction", "informal_income_weight",
        "haircut_mortgage", "haircut_vehicle", "haircut_jewelry",
        "haircut_financial_deposit", "haircut_financial_security",
        "haircut_other",
    ]


@admin.register(CreditInstructionPolicy)
class CreditInstructionPolicyAdmin(admin.ModelAdmin):
    list_display = [
        "tenant",
        "collateral_coverage_mode",
        "require_field_visit",
        "kyc_gate",
        "amount_approved_mode",
        "enable_cancel_status",
    ]
    list_filter = ["tenant", "collateral_coverage_mode"]


@admin.register(LoanWriteOffRequest)
class LoanWriteOffRequestAdmin(admin.ModelAdmin):
    """Admin pour les demandes de passage en perte."""

    list_display = [
        "id",
        "loan",
        "status",
        "reason",
        "outstanding_balance",
        "days_past_due",
        "created_by",
        "created_at",
        "reviewed_by",
        "reviewed_at",
        "tenant",
    ]
    list_filter = ["status", "reason", "tenant", "created_at", "reviewed_at"]
    search_fields = [
        "loan__application__reference",
        "loan__application__client__last_name",
        "loan__application__client__company_name",
    ]
    readonly_fields = [
        "created_by",
        "created_at",
        "reviewed_by",
        "reviewed_at",
        "executed_by",
        "executed_at",
    ]
    fieldsets = (
        (
            "Informations générales",
            {
                "fields": (
                    "loan",
                    "status",
                    "reason",
                    "outstanding_balance",
                    "days_past_due",
                )
            },
        ),
        (
            "Détails de la demande",
            {
                "fields": (
                    "justification",
                    "recovery_attempts",
                    "guarantees_status",
                    "accounting_provision_rate",
                )
            },
        ),
        (
            "Validation",
            {
                "fields": (
                    "reviewed_by",
                    "reviewed_at",
                    "review_comment",
                )
            },
        ),
        (
            "Exécution",
            {
                "fields": (
                    "executed_by",
                    "executed_at",
                )
            },
        ),
        (
            "Métadonnées",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "tenant",
                )
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        """Interdire la suppression des demandes exécutées."""
        if obj and obj.status == "EXECUTED":
            return False
        return super().has_delete_permission(request, obj)


@admin.register(LoanRestructuringRequest)
class LoanRestructuringRequestAdmin(admin.ModelAdmin):
    """Admin pour les demandes de restructuration."""

    list_display = [
        "id",
        "loan",
        "status",
        "reason",
        "current_outstanding_balance",
        "new_duration_months",
        "new_monthly_installment",
        "created_by",
        "created_at",
        "reviewed_by",
        "reviewed_at",
        "tenant",
    ]
    list_filter = ["status", "reason", "tenant", "created_at", "reviewed_at"]
    search_fields = [
        "loan__application__reference",
        "loan__application__client__last_name",
        "loan__application__client__company_name",
    ]
    readonly_fields = [
        "created_by",
        "created_at",
        "reviewed_by",
        "reviewed_at",
        "executed_by",
        "executed_at",
        "new_monthly_installment",
        "additional_interest_cost",
    ]
    fieldsets = (
        (
            "Informations générales",
            {
                "fields": (
                    "loan",
                    "status",
                    "reason",
                )
            },
        ),
        (
            "État actuel du prêt",
            {
                "fields": (
                    "current_outstanding_balance",
                    "current_monthly_installment",
                    "current_remaining_months",
                    "current_days_past_due",
                )
            },
        ),
        (
            "Nouveaux termes proposés",
            {
                "fields": (
                    "new_duration_months",
                    "new_interest_rate",
                    "grace_period_months",
                    "capitalize_arrears",
                    "arrears_amount",
                )
            },
        ),
        (
            "Impact financier (calculé automatiquement)",
            {
                "fields": (
                    "new_monthly_installment",
                    "additional_interest_cost",
                )
            },
        ),
        (
            "Analyse de capacité révisée",
            {
                "fields": (
                    "client_revised_income",
                    "client_revised_expenses",
                    "revised_debt_ratio",
                )
            },
        ),
        (
            "Garanties et conditions",
            {
                "fields": (
                    "guarantees_maintained",
                    "guarantees_comment",
                    "special_conditions",
                    "previous_restructuring_count",
                )
            },
        ),
        (
            "Justification",
            {
                "fields": ("justification",)
            },
        ),
        (
            "Validation",
            {
                "fields": (
                    "reviewed_by",
                    "reviewed_at",
                    "review_comment",
                )
            },
        ),
        (
            "Exécution",
            {
                "fields": (
                    "executed_by",
                    "executed_at",
                )
            },
        ),
        (
            "Métadonnées",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "tenant",
                )
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        """Interdire la suppression des demandes exécutées."""
        if obj and obj.status == "EXECUTED":
            return False
        return super().has_delete_permission(request, obj)

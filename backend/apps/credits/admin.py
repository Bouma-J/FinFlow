from django.contrib import admin

from .models import (
    AnalysisThreshold,
    CreditApplication,
    CreditDocument,
    FieldVisit,
    FinancialAnalysis,
    Installment,
    Loan,
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
    ]
    list_filter = ["tenant"]

from django.contrib import admin

from .models import (
    CollectionAction,
    CollectionCase,
    PaymentPromise,
    Repayment,
)


class ActionInline(admin.TabularInline):
    model = CollectionAction
    extra = 0


class PromiseInline(admin.TabularInline):
    model = PaymentPromise
    extra = 0


@admin.register(CollectionCase)
class CollectionCaseAdmin(admin.ModelAdmin):
    list_display = ["loan", "stage", "par_class", "days_overdue", "overdue_amount", "tenant"]
    list_filter = ["stage", "par_class", "tenant"]
    inlines = [ActionInline, PromiseInline]


@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display = ["loan", "amount", "payment_date", "tenant"]
    list_filter = ["tenant"]

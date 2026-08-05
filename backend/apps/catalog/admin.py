from django.contrib import admin

from .models import ChecklistItem, CreditProduct, ProductCategory, RejectReason


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["code", "label", "tenant", "is_active"]
    list_filter = ["is_active", "tenant"]
    search_fields = ["code", "label"]


@admin.register(CreditProduct)
class CreditProductAdmin(admin.ModelAdmin):
    list_display = ["code", "label", "category", "currency", "interest_rate", "is_active"]
    list_filter = ["is_active", "client_type", "tenant"]
    search_fields = ["code", "label"]


@admin.register(RejectReason)
class RejectReasonAdmin(admin.ModelAdmin):
    list_display = ["code", "label", "tenant", "is_active"]
    list_filter = ["is_active", "tenant"]


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ["label", "product", "is_mandatory", "order"]
    list_filter = ["is_mandatory", "tenant"]

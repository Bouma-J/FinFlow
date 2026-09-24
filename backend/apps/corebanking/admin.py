from django.contrib import admin

from .models import CoreBankingConnector, IntegrationLog, CbsOutboxEvent


@admin.register(CoreBankingConnector)
class CoreBankingConnectorAdmin(admin.ModelAdmin):
    list_display = ["name", "protocol", "tenant", "is_active"]
    list_filter = ["protocol", "is_active", "tenant"]
    search_fields = ["name"]


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ["operation", "connector", "status", "attempts", "created_at", "tenant"]
    list_filter = ["status", "direction", "tenant"]
    search_fields = ["operation", "external_reference"]


@admin.register(CbsOutboxEvent)
class CbsOutboxEventAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "event_type",
        "status",
        "entity_type",
        "entity_id",
        "cbs_reference",
        "initiated_at",
        "completed_at",
        "tenant",
    ]
    list_filter = ["event_type", "status", "tenant", "initiated_at"]
    search_fields = ["cbs_reference", "entity_id"]
    readonly_fields = [
        "initiated_at",
        "completed_at",
        "cbs_request_payload",
        "cbs_response",
        "cbs_error",
    ]
    ordering = ["-initiated_at"]
    
    def has_add_permission(self, request):
        # Pas de création manuelle - créé automatiquement par le code
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Permet suppression seulement des COMPLETED/FAILED anciens
        if obj and obj.status in [CbsOutboxEvent.Status.PENDING, CbsOutboxEvent.Status.ORPHAN]:
            return False
        return super().has_delete_permission(request, obj)

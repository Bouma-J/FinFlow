from rest_framework.exceptions import ValidationError

from apps.common.access import apply_related_data_scope
from apps.common.viewsets import AgencyScopedViewSet

from .models import Surety, SuretyEngagement
from .serializers import (
    SuretyEngagementSerializer,
    SuretyListSerializer,
    SuretySerializer,
)


class SuretyViewSet(AgencyScopedViewSet):
    queryset = Surety.objects.select_related("agency").all()
    serializer_class = SuretySerializer
    filterset_fields = ["surety_type", "is_active", "agency"]
    search_fields = [
        "name", "first_name", "last_name", "identifier",
        "national_id", "phone", "email", "activity",
        "company_name", "ifu", "rccm",
        "manager_last_name", "manager_first_name",
    ]
    ordering_fields = ["created_at", "name", "last_name"]

    def get_serializer_class(self):
        if self.action == "list":
            return SuretyListSerializer
        return SuretySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            return qs
        return qs.prefetch_related("engagements", "phones", "documents")


class SuretyEngagementViewSet(AgencyScopedViewSet):
    queryset = SuretyEngagement.objects.select_related("surety", "application").all()
    serializer_class = SuretyEngagementSerializer
    filterset_fields = ["surety", "application", "status"]
    agency_field = ""
    owner_field = ""

    def get_queryset(self):
        qs = super(AgencyScopedViewSet, self).get_queryset()
        user = self.request.user
        if user and user.is_authenticated:
            qs = apply_related_data_scope(qs, user, "application__agency")
        return qs

    def _assert_application_allows_collateral(self, application):
        from apps.credits.access import can_attach_collateral

        if application is None:
            return
        if not can_attach_collateral(application, self.request.user):
            raise ValidationError(
                "Impossible de rattacher ou modifier une caution sur un "
                f"dossier « {application.get_status_display()} »."
            )

    def perform_create(self, serializer):
        surety = serializer.validated_data["surety"]
        amount = serializer.validated_data["amount"]
        application = serializer.validated_data.get("application")
        self._assert_application_allows_collateral(application)
        # Contrôle du plafond uniquement si un plafond a été défini (> 0).
        if surety.commitment_ceiling and amount > surety.available_ceiling:
            raise ValidationError(
                "Le montant dépasse le plafond disponible de la caution."
            )
        serializer.save()

    def perform_update(self, serializer):
        application = serializer.validated_data.get(
            "application", serializer.instance.application
        )
        self._assert_application_allows_collateral(application)
        super().perform_update(serializer)

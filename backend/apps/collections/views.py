import csv
import io

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.common.access import DataScope, get_user_agency_ids
from apps.common.viewsets import TenantScopedViewSet
from apps.documents.models import Document, DocumentCategory
from apps.documents.serializers import DocumentSerializer

from .models import (
    CollectionAction,
    CollectionCase,
    CollectionEscalationRule,
    LegalParty,
    LitigationCost,
    LitigationEvent,
    LitigationFile,
    LitigationSeizure,
    PaymentPromise,
    Repayment,
)
from .serializers import (
    CaseAssignSerializer,
    CaseNextActionSerializer,
    CaseReminderSerializer,
    CaseRepaymentCreateSerializer,
    CaseRestructureSerializer,
    CaseStageSerializer,
    CaseWriteOffSerializer,
    CollectionActionSerializer,
    CollectionCaseListSerializer,
    CollectionCaseSerializer,
    CollectionEscalationRuleSerializer,
    LegalPartySerializer,
    LitigationCostCreateSerializer,
    LitigationCostSerializer,
    LitigationDocumentUploadSerializer,
    LitigationEventCreateSerializer,
    LitigationEventSerializer,
    LitigationFileSerializer,
    LitigationFileWriteSerializer,
    LitigationSeizureCreateSerializer,
    LitigationSeizureSerializer,
    LitigationUpsertSerializer,
    PaymentPromiseSerializer,
    RepaymentSerializer,
)
from .services import (
    agent_dashboard,
    apply_restructure,
    change_case_stage,
    create_litigation,
    ensure_default_escalation_rules,
    ensure_litigation_document_categories,
    litigation_documents,
    send_collection_reminder,
    upcoming_hearings,
    upsert_litigation,
    write_off_case,
)

User = get_user_model()

_CLOSED_LITIGATION_STATUSES = (
    LitigationFile.Status.CLOSED,
    LitigationFile.Status.ABANDONED,
    LitigationFile.Status.SETTLED,
)


def _litigation_write_payload(validated_data: dict) -> dict:
    """Normalise le payload serializer → services create/upsert."""
    data = dict(validated_data)
    data.pop("litigation_id", None)
    data.pop("case", None)
    guarantees = data.pop("related_guarantee_ids", None)
    if guarantees is not None:
        data["related_guarantee_ids"] = [g.pk for g in guarantees]
    return data


class RepaymentViewSet(TenantScopedViewSet):
    queryset = Repayment.objects.select_related("loan").all()
    serializer_class = RepaymentSerializer
    filterset_fields = ["loan"]
    search_fields = ["reference"]


class CollectionCaseViewSet(TenantScopedViewSet):
    queryset = CollectionCase.objects.select_related(
        "loan",
        "loan__application",
        "loan__application__client",
        "loan__application__agency",
        "loan__application__product",
        "assigned_to",
    ).prefetch_related(
        "actions",
        "promises",
        "stage_history",
        "stage_history__changed_by",
        "restructures",
        "write_offs",
        "litigations__events",
        "litigations__events__performed_by",
        "litigations__costs",
        "litigations__costs__party",
        "litigations__seizures",
        "litigations__seizures__bailiff",
        "litigations__law_firm",
        "litigations__lawyer_party",
        "litigations__bailiff_party",
        "litigations__related_guarantees",
        "loan__installments",
        "loan__repayments",
        "loan__application__guarantees",
        "loan__application__dation_requests",
    ).all()
    filterset_fields = ["stage", "par_class", "assigned_to"]
    ordering_fields = [
        "days_overdue", "overdue_amount", "created_at", "next_action_date",
    ]
    search_fields = [
        "loan__application__reference",
        "loan__application__client__last_name",
        "loan__application__client__first_name",
        "loan__core_banking_reference",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return CollectionCaseListSerializer
        return CollectionCaseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if getattr(user, "is_group_level", False):
            pass
        else:
            scope = getattr(user, "data_scope", DataScope.AGENCY)
            if scope == DataScope.AGENCY:
                agency_ids = get_user_agency_ids(user)
                if not agency_ids:
                    return qs.none()
                qs = qs.filter(loan__application__agency_id__in=agency_ids)
            elif scope == DataScope.OWN:
                qs = qs.filter(assigned_to=user)
        # TENANT : toute la filiale (déjà scopée par tenant)
        mine = self.request.query_params.get("mine")
        if mine in {"1", "true", "True"}:
            qs = qs.filter(assigned_to=user)
        open_only = self.request.query_params.get("open")
        if open_only in {"1", "true", "True"}:
            qs = qs.exclude(stage=CollectionCase.Stage.CLOSED)
        followup_due = self.request.query_params.get("followup_due")
        if followup_due in {"1", "true", "True"}:
            from django.utils import timezone

            qs = qs.filter(
                next_action_date__isnull=False,
                next_action_date__lte=timezone.localdate(),
            )
        broken_promises = self.request.query_params.get("broken_promises")
        if broken_promises in {"1", "true", "True"}:
            qs = qs.filter(
                promises__status=PaymentPromise.Status.BROKEN,
            ).distinct()
        if self.action == "list":
            qs = qs.annotate(
                pending_promises_count=Count(
                    "promises",
                    filter=Q(promises__status=PaymentPromise.Status.PENDING),
                )
            )
        return qs

    @action(detail=False, methods=["get"], url_path="agent-dashboard")
    def agent_dashboard_view(self, request):
        """Indicateurs portefeuille de l'agent connecté."""
        tenant_id = getattr(request, "tenant_id", None) or getattr(
            request.user, "tenant_id", None
        )
        data = agent_dashboard(user=request.user, tenant_id=tenant_id)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="hearings-agenda")
    def hearings_agenda(self, request):
        """Agenda des prochaines audiences contentieux."""
        tenant_id = getattr(request, "tenant_id", None) or getattr(
            request.user, "tenant_id", None
        )
        try:
            within_days = int(request.query_params.get("within_days", 30))
        except (TypeError, ValueError):
            within_days = 30
        try:
            limit = int(request.query_params.get("limit", 50))
        except (TypeError, ValueError):
            limit = 50
        return Response(
            upcoming_hearings(
                tenant_id=tenant_id,
                within_days=max(1, min(within_days, 365)),
                limit=max(1, min(limit, 200)),
            )
        )

    @action(detail=True, methods=["post"], url_path="repayments")
    def add_repayment(self, request, pk=None):
        """Enregistre un encaissement et l'applique à l'échéancier."""
        case = self.get_object()
        serializer = CaseRepaymentCreateSerializer(
            data=request.data, context={"case": case, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        case.refresh_from_db()
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        """Affecte (ou retire) l'agent de recouvrement."""
        case = self.get_object()
        serializer = CaseAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data.get("assigned_to")
        if user_id is None:
            case.assigned_to = None
        else:
            try:
                agent = User.objects.get(pk=user_id)
            except User.DoesNotExist as exc:
                raise ValidationError({
                    "assigned_to": "Utilisateur introuvable."
                }) from exc
            if (
                not getattr(agent, "is_group_level", False)
                and agent.tenant_id
                and agent.tenant_id != case.tenant_id
            ):
                raise ValidationError({
                    "assigned_to": "L'agent doit appartenir à la filiale."
                })
            case.assigned_to = agent
        case.save(update_fields=["assigned_to"])
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="set-stage")
    def set_stage(self, request, pk=None):
        """Change le stade du dossier (amiable / précontentieux / …)."""
        case = self.get_object()
        serializer = CaseStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        change_case_stage(
            case,
            serializer.validated_data["stage"],
            user=request.user,
            reason=serializer.validated_data.get("reason", ""),
            automatic=False,
        )
        case.refresh_from_db()
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="set-next-action")
    def set_next_action_view(self, request, pk=None):
        """Planifie la prochaine action / visite."""
        case = self.get_object()
        serializer = CaseNextActionSerializer(
            data=request.data, context={"case": case}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        case.refresh_from_db()
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="restructure")
    def restructure(self, request, pk=None):
        """Restructure le prêt (nouvel échéancier sur capital restant dû)."""
        case = self.get_object()
        serializer = CaseRestructureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            apply_restructure(
                case,
                user=request.user,
                **serializer.validated_data,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        case.refresh_from_db()
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="write-off")
    def write_off(self, request, pk=None):
        """Passe le prêt en perte / défaut et clôture le dossier."""
        case = self.get_object()
        serializer = CaseWriteOffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            write_off_case(
                case,
                user=request.user,
                **serializer.validated_data,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        case.refresh_from_db()
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="send-reminder")
    def send_reminder(self, request, pk=None):
        """Envoie immédiatement une relance EMAIL ou SMS (force)."""
        case = self.get_object()
        serializer = CaseReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = send_collection_reminder(
            case,
            channel=serializer.validated_data["channel"],
            force=True,
        )
        case.refresh_from_db()
        return Response({
            "reminder": result,
            "case": CollectionCaseSerializer(
                case, context={"request": request}
            ).data,
        })

    @action(detail=True, methods=["post", "put", "patch"], url_path="litigation")
    def litigation(self, request, pk=None):
        """Crée / met à jour une procédure contentieuse (optionnel : litigation_id)."""
        case = self.get_object()
        serializer = LitigationUpsertSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        litigation_id = serializer.validated_data.get("litigation_id")
        payload = _litigation_write_payload(serializer.validated_data)
        try:
            upsert_litigation(
                case, data=payload, litigation_id=litigation_id
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        case.refresh_from_db()
        return Response(
            CollectionCaseSerializer(case, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="litigation-events")
    def litigation_events(self, request, pk=None):
        """Ajoute un événement à une procédure (optionnel : litigation_id)."""
        case = self.get_object()
        serializer = LitigationEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        litigation_id = data.pop("litigation_id", None)
        lit = None
        if litigation_id:
            lit = LitigationFile.objects.filter(case=case, pk=litigation_id).first()
            if lit is None:
                raise ValidationError({
                    "litigation_id": "Dossier contentieux introuvable."
                })
        if lit is None:
            lit = (
                case.litigations.exclude(status__in=_CLOSED_LITIGATION_STATUSES)
                .order_by("-created_at")
                .first()
            )
        if lit is None:
            lit = upsert_litigation(case, data={})
        event = LitigationEvent.objects.create(
            tenant_id=case.tenant_id,
            litigation=lit,
            **data,
        )
        if event.event_type == LitigationEvent.EventType.HEARING:
            lit.recompute_next_hearing()
        return Response(
            LitigationEventSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"], url_path="export")
    def export_csv(self, request):
        """Export CSV du portefeuille filtré (max 5000 lignes)."""
        qs = self.filter_queryset(self.get_queryset()).select_related(
            "loan__application__client",
            "loan__application__product",
            "assigned_to",
        )[:5000]
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow([
            "id",
            "reference",
            "client",
            "produit",
            "stade",
            "par",
            "jours_retard",
            "montant_impaye",
            "prochaine_action",
            "type_action",
            "agent",
        ])
        for c in qs:
            app = c.loan.application
            client = getattr(app, "client", None)
            product = getattr(app, "product", None)
            agent = c.assigned_to
            writer.writerow([
                str(c.id),
                app.reference or "",
                client.display_name if client else "",
                product.label if product else "",
                c.stage,
                c.par_class,
                c.days_overdue,
                str(c.overdue_amount),
                c.next_action_date.isoformat() if c.next_action_date else "",
                c.next_action_type or "",
                (agent.get_full_name() or agent.username) if agent else "",
            ])
        response = HttpResponse(
            buffer.getvalue().encode("utf-8-sig"),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = (
            'attachment; filename="recouvrement.csv"'
        )
        return response


class CollectionActionViewSet(TenantScopedViewSet):
    queryset = CollectionAction.objects.select_related("case").all()
    serializer_class = CollectionActionSerializer
    filterset_fields = ["case", "action_type"]


class PaymentPromiseViewSet(TenantScopedViewSet):
    queryset = PaymentPromise.objects.select_related("case").all()
    serializer_class = PaymentPromiseSerializer
    filterset_fields = ["case", "status"]


class CollectionEscalationRuleViewSet(TenantScopedViewSet):
    queryset = CollectionEscalationRule.objects.all()
    serializer_class = CollectionEscalationRuleSerializer
    filterset_fields = ["is_active", "target_stage"]
    ordering_fields = ["min_days_overdue"]

    def list(self, request, *args, **kwargs):
        tenant = getattr(request, "tenant", None)
        if tenant is None and getattr(request.user, "tenant_id", None):
            from apps.tenants.models import Tenant

            tenant = Tenant.objects.filter(pk=request.user.tenant_id).first()
        if tenant is not None:
            ensure_default_escalation_rules(tenant)
        return super().list(request, *args, **kwargs)


class LegalPartyViewSet(TenantScopedViewSet):
    queryset = LegalParty.objects.all()
    serializer_class = LegalPartySerializer
    filterset_fields = ["party_type", "is_active"]
    search_fields = ["name", "contact_name", "registration_no", "email", "phone"]
    ordering_fields = ["name", "party_type", "created_at"]


class LitigationFileViewSet(TenantScopedViewSet):
    queryset = LitigationFile.objects.select_related(
        "case",
        "law_firm",
        "lawyer_party",
        "bailiff_party",
    ).prefetch_related(
        "events",
        "events__performed_by",
        "costs",
        "costs__party",
        "seizures",
        "seizures__bailiff",
        "related_guarantees",
    ).all()
    serializer_class = LitigationFileSerializer
    filterset_fields = ["case", "status", "action_type", "law_firm"]
    search_fields = ["title", "case_reference", "court_name", "lawyer", "bailiff"]
    ordering_fields = ["hearing_date", "filing_date", "created_at", "status"]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return LitigationFileWriteSerializer
        return LitigationFileSerializer

    def create(self, request, *args, **kwargs):
        serializer = LitigationFileWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case = serializer.validated_data.get("case")
        if case is None:
            raise ValidationError({"case": "Dossier de recouvrement requis."})
        payload = _litigation_write_payload(serializer.validated_data)
        lit = create_litigation(case, data=payload)
        return Response(
            LitigationFileSerializer(lit, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        lit = self.get_object()
        serializer = LitigationFileWriteSerializer(
            data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        payload = _litigation_write_payload(serializer.validated_data)
        try:
            lit = upsert_litigation(
                lit.case, data=payload, litigation_id=lit.pk
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(
            LitigationFileSerializer(lit, context={"request": request}).data
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=["get", "post"], url_path="events")
    def events(self, request, pk=None):
        lit = self.get_object()
        if request.method == "GET":
            qs = lit.events.select_related("performed_by").all()
            return Response(LitigationEventSerializer(qs, many=True).data)
        serializer = LitigationEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("litigation_id", None)
        event = LitigationEvent.objects.create(
            tenant_id=lit.tenant_id,
            litigation=lit,
            **data,
        )
        if event.event_type == LitigationEvent.EventType.HEARING:
            lit.recompute_next_hearing()
        return Response(
            LitigationEventSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"], url_path="seizures")
    def seizures(self, request, pk=None):
        lit = self.get_object()
        if request.method == "GET":
            qs = lit.seizures.select_related("bailiff", "guarantee").all()
            return Response(LitigationSeizureSerializer(qs, many=True).data)
        serializer = LitigationSeizureCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seizure = LitigationSeizure.objects.create(
            tenant_id=lit.tenant_id,
            litigation=lit,
            **serializer.validated_data,
        )
        return Response(
            LitigationSeizureSerializer(seizure).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"], url_path="costs")
    def costs(self, request, pk=None):
        lit = self.get_object()
        if request.method == "GET":
            qs = lit.costs.select_related("party").all()
            return Response(LitigationCostSerializer(qs, many=True).data)
        serializer = LitigationCostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cost = LitigationCost.objects.create(
            tenant_id=lit.tenant_id,
            litigation=lit,
            **serializer.validated_data,
        )
        return Response(
            LitigationCostSerializer(cost).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"], url_path="documents")
    def documents(self, request, pk=None):
        lit = self.get_object()
        if request.method == "GET":
            docs = litigation_documents(lit).select_related(
                "category", "uploaded_by"
            )
            return Response(DocumentSerializer(docs, many=True).data)

        ensure_litigation_document_categories(lit.tenant)
        serializer = LitigationDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        name = (serializer.validated_data.get("name") or "").strip() or upload.name
        category_code = (
            serializer.validated_data.get("category") or ""
        ).strip() or "LIT_OTHER"
        category = DocumentCategory.objects.filter(
            tenant_id=lit.tenant_id, code=category_code, is_active=True
        ).first()
        if category is None:
            category = DocumentCategory.objects.filter(
                tenant_id=lit.tenant_id, code="LIT_OTHER"
            ).first()
        if category is None:
            raise ValidationError({
                "category": "Catégorie documentaire introuvable."
            })
        ct = ContentType.objects.get_for_model(LitigationFile)
        doc = Document(
            tenant_id=lit.tenant_id,
            category=category,
            name=name,
            file=upload,
            content_type=ct,
            object_id=lit.id,
            uploaded_by=request.user,
        )
        doc.mime_type = getattr(upload, "content_type", "") or ""
        doc.save()
        doc.compute_hash()
        doc.save(update_fields=["mime_type", "sha256", "size_bytes"])
        from apps.documents.quotas import bump_ged_usage

        bump_ged_usage(doc.tenant_id, doc.size_bytes)
        return Response(
            DocumentSerializer(doc).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="ensure-categories")
    def ensure_categories(self, request, pk=None):
        lit = self.get_object()
        created = ensure_litigation_document_categories(lit.tenant)
        return Response({"created": created})

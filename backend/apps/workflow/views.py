from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.catalog.models import RejectReason
from apps.common.viewsets import (
    TenantMandatoryMixin,
    TenantScopedReadOnlyViewSet,
    TenantScopedViewSet,
)

from .models import (
    ApprovalCondition,
    ApprovalStep,
    ApprovalTask,
    WorkflowDefinition,
    WorkflowInstance,
)
from .serializers import (
    ApprovalConditionSerializer,
    ApprovalStepSerializer,
    ApprovalTaskSerializer,
    ConditionActionSerializer,
    DecisionSerializer,
    WorkflowDefinitionSerializer,
    WorkflowInstanceSerializer,
)
from .services import (
    WorkflowError,
    ensure_definition_editable,
    lift_condition,
    process_decision,
    return_lift,
    validate_condition,
)


class WorkflowDefinitionViewSet(TenantMandatoryMixin, TenantScopedViewSet):
    queryset = WorkflowDefinition.objects.prefetch_related("steps").all()
    serializer_class = WorkflowDefinitionSerializer
    filterset_fields = ["target_type", "is_active"]
    search_fields = ["code", "name"]


class ApprovalStepViewSet(TenantMandatoryMixin, TenantScopedViewSet):
    queryset = ApprovalStep.objects.select_related("definition", "required_group").all()
    serializer_class = ApprovalStepSerializer
    filterset_fields = ["definition"]

    def _guard_editable(self, definition):
        try:
            ensure_definition_editable(definition)
        except WorkflowError as exc:
            raise ValidationError(str(exc))

    def perform_create(self, serializer):
        self._guard_editable(serializer.validated_data["definition"])
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._guard_editable(serializer.instance.definition)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        self._guard_editable(instance.definition)
        instance.delete()


class WorkflowInstanceViewSet(TenantScopedReadOnlyViewSet):
    queryset = WorkflowInstance.objects.prefetch_related("tasks").all()
    serializer_class = WorkflowInstanceSerializer
    filterset_fields = ["status", "definition"]


class ApprovalConditionViewSet(TenantScopedReadOnlyViewSet):
    queryset = ApprovalCondition.objects.select_related(
        "application", "task", "task__step",
        "issued_by", "lifted_by", "validated_by",
    ).all()
    serializer_class = ApprovalConditionSerializer
    # Décisions métier (émetteur / initiateur) contrôlées dans les services.
    action_perms = {
        "lift": [],
        "validate": [],
        "return_lift": [],
    }
    filterset_fields = ["application", "status", "task"]

    @action(detail=True, methods=["post"])
    def lift(self, request, pk=None):
        condition = self.get_object()
        payload = ConditionActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            lift_condition(
                condition,
                request.user,
                comment=payload.validated_data.get("comment", ""),
            )
        except WorkflowError as exc:
            raise ValidationError(str(exc))
        condition.refresh_from_db()
        return Response(
            ApprovalConditionSerializer(condition, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        condition = self.get_object()
        payload = ConditionActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            validate_condition(
                condition,
                request.user,
                comment=payload.validated_data.get("comment", ""),
            )
        except WorkflowError as exc:
            raise ValidationError(str(exc))
        condition.refresh_from_db()
        return Response(
            ApprovalConditionSerializer(condition, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def return_lift(self, request, pk=None):
        """Renvoie la levée au chargé de dossier pour complément (émetteur)."""
        condition = self.get_object()
        payload = ConditionActionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            return_lift(
                condition,
                request.user,
                comment=payload.validated_data.get("comment", ""),
            )
        except WorkflowError as exc:
            raise ValidationError(str(exc))
        condition.refresh_from_db()
        return Response(
            ApprovalConditionSerializer(condition, context={"request": request}).data
        )


class ApprovalTaskViewSet(TenantScopedReadOnlyViewSet):
    queryset = ApprovalTask.objects.select_related("step", "instance", "acted_by").all()
    serializer_class = ApprovalTaskSerializer
    # decide : groupe d'étape (user_can_act) — pas un codename Django.
    action_perms = {
        "my_pending": ["workflow.view_approvaltask"],
        "my_dossiers": ["workflow.view_approvaltask"],
        "decide": [],
    }
    filterset_fields = ["status", "instance", "step"]

    @action(detail=False, methods=["get"])
    def my_pending(self, request):
        """Tâches en attente pour les rôles de l'utilisateur connecté."""
        group_ids = request.user.groups.values_list("id", flat=True)
        qs = self.get_queryset().filter(
            status=ApprovalTask.Status.PENDING,
            step__required_group_id__in=group_ids,
        )
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page or qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_dossiers(self, request):
        """Tous les dossiers / processus en circuit concernant l'utilisateur.

        Inclut les dossiers de crédit, les demandes de main levée et les
        dations en paiement. Un enregistrement concerne l'utilisateur dès
        lors qu'une étape du circuit implique l'un de ses groupes.
        """
        from apps.credits.models import CreditApplication
        from apps.guarantees.models import DationRequest, GuaranteeReleaseRequest

        user = request.user
        group_ids = set(user.groups.values_list("id", flat=True))
        see_all = user.is_superuser or getattr(user, "is_group_level", False)

        instances = (
            WorkflowInstance.objects.select_related("definition")
            .prefetch_related("definition__steps", "tasks", "tasks__step")
            .order_by("-created_at")
        )

        rows = []
        seen_keys = set()
        for inst in instances:
            target = inst.target
            if target is None:
                continue

            if isinstance(target, CreditApplication):
                target_kind = "CREDIT"
                detail_path = f"/dossiers/{target.id}"
                row_id = str(target.id)
                reference = target.reference
                client = target.client
                amount = str(target.amount_requested)
                amount_proposed = (
                    str(target.amount_proposed)
                    if target.amount_proposed is not None
                    else None
                )
                currency = target.currency
                status = target.status
                status_display = target.get_status_display()
                product_label = (
                    target.product.label if target.product_id else ""
                )
                created_by = target.created_by
                created_at = target.created_at
            elif isinstance(target, GuaranteeReleaseRequest):
                target_kind = "MAIN_LEVEE"
                detail_path = f"/mains-levees/{target.id}"
                row_id = str(target.id)
                reference = target.reference
                client = target.guarantee.client if target.guarantee_id else None
                amount = str(target.cbs_outstanding or 0)
                amount_proposed = None
                currency = target.cbs_currency or "XAF"
                status = target.status
                status_display = target.get_status_display()
                product_label = "Main levée"
                created_by = target.created_by
                created_at = target.created_at
            elif isinstance(target, DationRequest):
                target_kind = "DATION"
                detail_path = f"/dations/{target.id}"
                row_id = str(target.id)
                reference = target.reference
                client = target.client
                amount = str(
                    target.asset_value
                    if target.asset_value is not None
                    else target.cbs_total_outstanding or 0
                )
                amount_proposed = None
                currency = target.cbs_currency or "XAF"
                status = target.status
                status_display = target.get_status_display()
                product_label = "Dation en paiement"
                created_by = target.created_by
                created_at = target.created_at
            else:
                continue

            seen_key = f"{target_kind}:{row_id}"
            if seen_key in seen_keys:
                continue

            steps = list(inst.definition.steps.all())
            step_group_ids = {s.required_group_id for s in steps}
            if not see_all and group_ids.isdisjoint(step_group_ids):
                continue

            seen_keys.add(seen_key)

            my_task = None
            for t in inst.tasks.all():
                if not t.step or t.step.required_group_id not in group_ids:
                    continue
                if t.status == ApprovalTask.Status.PENDING:
                    my_task = t
                    break
                if my_task is None or (
                    (t.acted_at or timezone.now())
                    > (my_task.acted_at or timezone.now())
                ):
                    my_task = t

            current_step = next(
                (s for s in steps if s.order == inst.current_order), None
            )
            rows.append(
                {
                    "id": row_id,
                    "target_kind": target_kind,
                    "detail_path": detail_path,
                    "reference": reference,
                    "client_display": getattr(
                        client, "display_name", str(client) if client else ""
                    ),
                    "client_type": getattr(client, "client_type", "") if client else "",
                    "client_type_display": (
                        client.get_client_type_display()
                        if client and client.client_type
                        else ""
                    ),
                    "amount_requested": amount,
                    "amount_proposed": amount_proposed,
                    "currency": currency,
                    "status": status,
                    "status_display": status_display,
                    "product_label": product_label,
                    "created_by_display": (
                        str(created_by) if created_by else ""
                    ),
                    "created_at": created_at.isoformat() if created_at else None,
                    "definition_name": inst.definition.name,
                    "instance_status": inst.status,
                    "current_step_name": (
                        current_step.name if current_step else ""
                    ),
                    "current_order": inst.current_order,
                    "my_task_status": my_task.status if my_task else None,
                    "my_step_name": (
                        my_task.step.name if my_task and my_task.step else ""
                    ),
                    "my_step_order": (
                        my_task.step.order if my_task and my_task.step else None
                    ),
                    "my_task_due_at": (
                        my_task.due_at.isoformat()
                        if my_task and my_task.due_at
                        else None
                    ),
                    "is_actionable": bool(
                        my_task
                        and my_task.status == ApprovalTask.Status.PENDING
                    ),
                }
            )

        return Response({"results": rows})

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        """Prend une décision sur la tâche (approuver / rejeter / retourner)."""
        task = self.get_object()
        payload = DecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        reject_reason = None
        if data.get("reject_reason"):
            reject_reason = RejectReason.objects.filter(
                id=data["reject_reason"]
            ).first()

        try:
            instance = process_decision(
                task=task,
                user=request.user,
                decision=data["decision"],
                comment=data.get("comment", ""),
                reject_reason=reject_reason,
                proposed_amount=data.get("proposed_amount"),
                opinion=data.get("opinion") or None,
                reserves=data.get("reserves"),
                return_to_submitter=data.get("return_to_submitter", False),
            )
        except WorkflowError as exc:
            raise ValidationError(str(exc))

        return Response(WorkflowInstanceSerializer(instance).data)

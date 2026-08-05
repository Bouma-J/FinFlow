"""Test du moteur de workflow (approbation d'un dossier)."""
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from apps.accounts.models import User
from apps.credits.models import CreditApplication
from apps.credits.services import submit_application
from apps.common.tenancy import tenant_context
from apps.workflow.models import (
    ApprovalCondition,
    ApprovalStep,
    ApprovalTask,
    WorkflowDefinition,
    WorkflowInstance,
)
from apps.workflow.services import (
    WorkflowError,
    lift_condition,
    process_decision,
    validate_condition,
)

pytestmark = pytest.mark.django_db


def test_single_step_approval(tenant_a, product_a, client_a):
    role = Group.objects.create(name="Validateur A")
    validator = User.objects.create(username="val_a", tenant=tenant_a)
    validator.groups.add(role)

    submitter = User.objects.create(username="sub_a", tenant=tenant_a)

    with tenant_context(tenant_a.id):
        definition = WorkflowDefinition.objects.create(
            tenant=tenant_a, code="WF", version=1, is_active=True
        )
        ApprovalStep.objects.create(
            tenant=tenant_a, definition=definition, name="Validation",
            order=1, required_group=role, sla_hours=24,
            step_kind=ApprovalStep.StepKind.DECISIONAL,
        )
        application = CreditApplication.objects.create(
            tenant=tenant_a, reference="D1", client=client_a, product=product_a,
            amount_requested=Decimal("500000"), duration_months=12, risk_level=1,
            submitted_by=submitter,
        )

        submit_application(application, submitter)
        application.refresh_from_db()
        assert application.status == CreditApplication.Status.IN_APPROVAL

        task = ApprovalTask.objects.get(instance__object_id=application.id)
        process_decision(
            task, validator, ApprovalTask.Status.APPROVED,
            opinion=ApprovalTask.Opinion.FAVORABLE,
        )

        application.refresh_from_db()
        assert application.status == CreditApplication.Status.APPROVED


def test_self_validation_blocked(tenant_a, product_a, client_a):
    role = Group.objects.create(name="Validateur B")
    user = User.objects.create(username="val_b", tenant=tenant_a)
    user.groups.add(role)

    with tenant_context(tenant_a.id):
        definition = WorkflowDefinition.objects.create(
            tenant=tenant_a, code="WF2", version=1, is_active=True
        )
        ApprovalStep.objects.create(
            tenant=tenant_a, definition=definition, name="Validation",
            order=1, required_group=role, sla_hours=24,
        )
        application = CreditApplication.objects.create(
            tenant=tenant_a, reference="D2", client=client_a, product=product_a,
            amount_requested=Decimal("500000"), duration_months=12, risk_level=1,
        )
        submit_application(application, user)
        task = ApprovalTask.objects.get(instance__object_id=application.id)

        with pytest.raises(WorkflowError):
            process_decision(
                task, user, ApprovalTask.Status.APPROVED,
                opinion=ApprovalTask.Opinion.FAVORABLE,
            )


def test_reserve_blocks_final_approval(tenant_a, product_a, client_a):
    role = Group.objects.create(name="Validateur C")
    validator = User.objects.create(username="val_c", tenant=tenant_a)
    validator.groups.add(role)
    submitter = User.objects.create(username="sub_c", tenant=tenant_a)

    with tenant_context(tenant_a.id):
        definition = WorkflowDefinition.objects.create(
            tenant=tenant_a, code="WF3", version=1, is_active=True
        )
        ApprovalStep.objects.create(
            tenant=tenant_a, definition=definition, name="Comité",
            order=1, required_group=role, sla_hours=24,
            step_kind=ApprovalStep.StepKind.DECISIONAL,
        )
        application = CreditApplication.objects.create(
            tenant=tenant_a, reference="D3", client=client_a, product=product_a,
            amount_requested=Decimal("500000"), duration_months=12, risk_level=1,
            submitted_by=submitter,
        )
        submit_application(application, submitter)
        task = ApprovalTask.objects.get(instance__object_id=application.id)

        process_decision(
            task, validator, ApprovalTask.Status.APPROVED,
            opinion=ApprovalTask.Opinion.FAVORABLE_SOUS_RESERVE,
            reserves=["Fournir garantie complémentaire"],
        )

        application.refresh_from_db()
        assert application.status == CreditApplication.Status.IN_APPROVAL
        instance = WorkflowInstance.objects.get(object_id=application.id)
        assert instance.status == WorkflowInstance.Status.AWAITING_CONDITIONS

        condition = ApprovalCondition.objects.get(application=application)
        lift_condition(condition, submitter, comment="Garantie fournie")
        validate_condition(condition, validator, comment="Conforme")

        application.refresh_from_db()
        assert application.status == CreditApplication.Status.APPROVED

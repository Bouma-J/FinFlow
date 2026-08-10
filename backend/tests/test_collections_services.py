"""Tests du moteur de recouvrement (allocation des encaissements / PAR)."""
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.collections.models import (
    CollectionCase,
    CollectionEscalationRule,
    CollectionStageHistory,
    LitigationFile,
    PaymentPromise,
)
from apps.collections.services import (
    apply_restructure,
    ensure_default_escalation_rules,
    outstanding_principal,
    record_repayment,
    refresh_broken_promises,
    refresh_loan_overdue,
    send_collection_reminder,
    set_next_action,
    upsert_litigation,
    write_off_case,
)
from apps.common.tenancy import tenant_context
from apps.credits.models import CreditApplication, Installment, Loan
from apps.notifications.models import NotificationLog, TenantNotificationSettings


def test_apply_repayment_fifo_and_close_case(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        app = CreditApplication.objects.create(
            tenant=tenant_a,
            client=client_a,
            product=product_a,
            amount_requested=Decimal("100000"),
            duration_months=2,
            risk_level=1,
            reference="REF-COL-1",
            status=CreditApplication.Status.APPROVED,
        )
        loan = Loan.objects.create(
            tenant=tenant_a,
            application=app,
            principal=Decimal("100000"),
            interest_rate=Decimal("12"),
            duration_months=2,
            disbursed_at=date.today() - timedelta(days=60),
            first_due_date=date.today() - timedelta(days=40),
            status=Loan.Status.ACTIVE,
        )
        Installment.objects.create(
            tenant=tenant_a,
            loan=loan,
            number=1,
            due_date=date.today() - timedelta(days=40),
            principal_due=Decimal("50000"),
            interest_due=Decimal("1000"),
            total_due=Decimal("51000"),
            amount_paid=Decimal("0"),
            status=Installment.Status.OVERDUE,
        )
        Installment.objects.create(
            tenant=tenant_a,
            loan=loan,
            number=2,
            due_date=date.today() - timedelta(days=10),
            principal_due=Decimal("50000"),
            interest_due=Decimal("500"),
            total_due=Decimal("50500"),
            amount_paid=Decimal("0"),
            status=Installment.Status.OVERDUE,
        )

        repayment, case = record_repayment(
            loan=loan,
            amount=Decimal("51000"),
            payment_date=date.today(),
            reference="ENC-1",
        )
        assert repayment.pk
        i1 = loan.installments.get(number=1)
        i2 = loan.installments.get(number=2)
        assert i1.status == Installment.Status.PAID
        assert i1.amount_paid == Decimal("51000")
        assert i2.status == Installment.Status.OVERDUE
        assert case is not None
        assert case.overdue_amount == Decimal("50500")

        _, case2 = record_repayment(
            loan=loan,
            amount=Decimal("50500"),
            payment_date=date.today(),
        )
        loan.refresh_from_db()
        assert loan.status == Loan.Status.CLOSED
        case2.refresh_from_db()
        assert case2.stage == CollectionCase.Stage.CLOSED
        assert case2.days_overdue == 0


def test_promise_kept_on_repayment(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        app = CreditApplication.objects.create(
            tenant=tenant_a,
            client=client_a,
            product=product_a,
            amount_requested=Decimal("10000"),
            duration_months=1,
            risk_level=1,
            reference="REF-COL-2",
            status=CreditApplication.Status.APPROVED,
        )
        loan = Loan.objects.create(
            tenant=tenant_a,
            application=app,
            principal=Decimal("10000"),
            interest_rate=Decimal("10"),
            duration_months=1,
            disbursed_at=date.today() - timedelta(days=40),
            first_due_date=date.today() - timedelta(days=20),
            status=Loan.Status.ACTIVE,
        )
        Installment.objects.create(
            tenant=tenant_a,
            loan=loan,
            number=1,
            due_date=date.today() - timedelta(days=20),
            principal_due=Decimal("10000"),
            interest_due=Decimal("0"),
            total_due=Decimal("10000"),
            status=Installment.Status.OVERDUE,
        )
        case = CollectionCase.objects.create(
            tenant=tenant_a,
            loan=loan,
            days_overdue=20,
            overdue_amount=Decimal("10000"),
            par_class=CollectionCase.ParClass.PAR1,
        )
        promise = PaymentPromise.objects.create(
            tenant=tenant_a,
            case=case,
            amount=Decimal("10000"),
            promised_date=timezone.localdate(),
            status=PaymentPromise.Status.PENDING,
        )
        record_repayment(loan=loan, amount=Decimal("10000"))
        promise.refresh_from_db()
        assert promise.status == PaymentPromise.Status.KEPT


def test_escalation_to_precontentious_and_history(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        ensure_default_escalation_rules(tenant_a)
        app = CreditApplication.objects.create(
            tenant=tenant_a,
            client=client_a,
            product=product_a,
            amount_requested=Decimal("20000"),
            duration_months=1,
            risk_level=1,
            reference="REF-COL-ESC",
            status=CreditApplication.Status.APPROVED,
        )
        loan = Loan.objects.create(
            tenant=tenant_a,
            application=app,
            principal=Decimal("20000"),
            interest_rate=Decimal("10"),
            duration_months=1,
            disbursed_at=date.today() - timedelta(days=50),
            first_due_date=date.today() - timedelta(days=40),
            status=Loan.Status.ACTIVE,
        )
        Installment.objects.create(
            tenant=tenant_a,
            loan=loan,
            number=1,
            due_date=date.today() - timedelta(days=40),
            principal_due=Decimal("20000"),
            interest_due=Decimal("0"),
            total_due=Decimal("20000"),
            status=Installment.Status.OVERDUE,
        )
        case = refresh_loan_overdue(loan)
        assert case is not None
        assert case.days_overdue >= 31
        assert case.stage == CollectionCase.Stage.PRECONTENTIOUS
        assert CollectionStageHistory.objects.filter(
            case=case, to_stage=CollectionCase.Stage.PRECONTENTIOUS
        ).exists()


def test_escalation_only_upwards(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        CollectionEscalationRule.objects.create(
            tenant=tenant_a,
            min_days_overdue=10,
            target_stage=CollectionCase.Stage.AMICABLE,
            is_active=True,
        )
        CollectionEscalationRule.objects.create(
            tenant=tenant_a,
            min_days_overdue=31,
            target_stage=CollectionCase.Stage.PRECONTENTIOUS,
            is_active=True,
        )
        app = CreditApplication.objects.create(
            tenant=tenant_a,
            client=client_a,
            product=product_a,
            amount_requested=Decimal("5000"),
            duration_months=1,
            risk_level=1,
            reference="REF-COL-UP",
            status=CreditApplication.Status.APPROVED,
        )
        loan = Loan.objects.create(
            tenant=tenant_a,
            application=app,
            principal=Decimal("5000"),
            interest_rate=Decimal("10"),
            duration_months=1,
            disbursed_at=date.today() - timedelta(days=20),
            first_due_date=date.today() - timedelta(days=15),
            status=Loan.Status.ACTIVE,
        )
        Installment.objects.create(
            tenant=tenant_a,
            loan=loan,
            number=1,
            due_date=date.today() - timedelta(days=15),
            principal_due=Decimal("5000"),
            interest_due=Decimal("0"),
            total_due=Decimal("5000"),
            status=Installment.Status.OVERDUE,
        )
        case = CollectionCase.objects.create(
            tenant=tenant_a,
            loan=loan,
            stage=CollectionCase.Stage.LITIGATION,
            days_overdue=15,
            overdue_amount=Decimal("5000"),
            par_class=CollectionCase.ParClass.PAR1,
        )
        refreshed = refresh_loan_overdue(loan)
        refreshed.refresh_from_db()
        assert refreshed.stage == CollectionCase.Stage.LITIGATION


def test_broken_promises_and_next_action(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        app = CreditApplication.objects.create(
            tenant=tenant_a,
            client=client_a,
            product=product_a,
            amount_requested=Decimal("8000"),
            duration_months=1,
            risk_level=1,
            reference="REF-COL-PR",
            status=CreditApplication.Status.APPROVED,
        )
        loan = Loan.objects.create(
            tenant=tenant_a,
            application=app,
            principal=Decimal("8000"),
            interest_rate=Decimal("10"),
            duration_months=1,
            disbursed_at=date.today() - timedelta(days=30),
            first_due_date=date.today() - timedelta(days=20),
            status=Loan.Status.ACTIVE,
        )
        case = CollectionCase.objects.create(
            tenant=tenant_a,
            loan=loan,
            days_overdue=20,
            overdue_amount=Decimal("8000"),
        )
        promise = PaymentPromise.objects.create(
            tenant=tenant_a,
            case=case,
            amount=Decimal("1000"),
            promised_date=timezone.localdate() - timedelta(days=2),
            status=PaymentPromise.Status.PENDING,
        )
        assert refresh_broken_promises() >= 1
        promise.refresh_from_db()
        assert promise.status == PaymentPromise.Status.BROKEN

        set_next_action(
            case,
            action_date=timezone.localdate() + timedelta(days=3),
            action_type="VISIT",
            note="Visite terrain",
        )
        case.refresh_from_db()
        assert case.next_action_type == "VISIT"
        assert case.next_action_note == "Visite terrain"


def _overdue_loan(tenant, product, client, *, days=40, principal="10000", ref="REF"):
    app = CreditApplication.objects.create(
        tenant=tenant,
        client=client,
        product=product,
        amount_requested=Decimal(principal),
        duration_months=6,
        risk_level=1,
        reference=ref,
        status=CreditApplication.Status.APPROVED,
    )
    loan = Loan.objects.create(
        tenant=tenant,
        application=app,
        principal=Decimal(principal),
        interest_rate=Decimal("12"),
        duration_months=6,
        disbursed_at=date.today() - timedelta(days=days + 10),
        first_due_date=date.today() - timedelta(days=days),
        status=Loan.Status.ACTIVE,
    )
    Installment.objects.create(
        tenant=tenant,
        loan=loan,
        number=1,
        due_date=date.today() - timedelta(days=days),
        principal_due=Decimal(principal),
        interest_due=Decimal("0"),
        total_due=Decimal(principal),
        status=Installment.Status.OVERDUE,
    )
    case = refresh_loan_overdue(loan)
    return loan, case


def test_apply_restructure_rebuilds_schedule(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        loan, case = _overdue_loan(
            tenant_a, product_a, client_a, days=20, principal="12000", ref="REF-RST"
        )
        before = outstanding_principal(loan)
        assert before == Decimal("12000")
        record = apply_restructure(
            case,
            new_duration_months=3,
            new_rate=Decimal("10"),
            reason="Accord amiable",
        )
        assert record.outstanding_principal == Decimal("12000")
        loan.refresh_from_db()
        assert loan.duration_months == 3
        assert loan.interest_rate == Decimal("10")
        unpaid = loan.installments.exclude(status=Installment.Status.PAID)
        assert unpaid.count() == 3
        case.refresh_from_db()
        # Plus d'impayé après restructuration → dossier clôturé, prêt actif
        assert case.stage == CollectionCase.Stage.CLOSED
        assert loan.status == Loan.Status.ACTIVE
        assert case.restructures.filter(status="APPLIED").exists()


def test_write_off_defaults_loan(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        loan, case = _overdue_loan(
            tenant_a, product_a, client_a, days=100, principal="5000", ref="REF-WO"
        )
        wo = write_off_case(case, reason="Irrécouvrable")
        loan.refresh_from_db()
        case.refresh_from_db()
        assert wo.amount == Decimal("5000")
        assert loan.status == Loan.Status.DEFAULTED
        assert case.stage == CollectionCase.Stage.CLOSED


def test_litigation_upsert(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        _, case = _overdue_loan(
            tenant_a, product_a, client_a, days=100, principal="7000", ref="REF-LIT"
        )
        lit = upsert_litigation(
            case,
            data={
                "court_name": "TGI Bamako",
                "case_reference": "RG-1",
                "status": LitigationFile.Status.OPEN,
            },
        )
        assert lit.court_name == "TGI Bamako"
        case.refresh_from_db()
        assert case.stage == CollectionCase.Stage.LITIGATION


def test_reminder_email_skipped_without_client_email(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        prefs = TenantNotificationSettings.for_tenant(tenant_a)
        prefs.notify_collection_email = True
        prefs.enabled = True
        prefs.save()
        client_a.email = ""
        client_a.save(update_fields=["email"])
        _, case = _overdue_loan(
            tenant_a, product_a, client_a, days=15, principal="3000", ref="REF-REM"
        )
        result = send_collection_reminder(case, channel="EMAIL", force=True)
        assert result["status"] == "SKIPPED"
        assert NotificationLog.objects.filter(
            kind=NotificationLog.Kind.COLLECTION_REMINDER
        ).exists()


def test_reminder_sms_stub(tenant_a, product_a, client_a):
    with tenant_context(tenant_a.id):
        client_a.phone = "+22370000000"
        client_a.save(update_fields=["phone"])
        _, case = _overdue_loan(
            tenant_a, product_a, client_a, days=15, principal="3000", ref="REF-SMS"
        )
        result = send_collection_reminder(case, channel="SMS", force=True)
        assert result["status"] == "SKIPPED"
        assert result["channel"] == "SMS"

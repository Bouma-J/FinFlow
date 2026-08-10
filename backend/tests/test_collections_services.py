"""Tests du moteur de recouvrement (allocation des encaissements / PAR)."""
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.collections.models import CollectionCase, PaymentPromise
from apps.collections.services import record_repayment
from apps.common.tenancy import tenant_context
from apps.credits.models import CreditApplication, Installment, Loan


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

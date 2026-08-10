"""Services de recouvrement : PAR, retards, allocation des encaissements."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.credits.models import Installment, Loan

from .models import CollectionCase, PaymentPromise, Repayment


def classify_par(days_overdue):
    """Classe un prêt dans une catégorie de portefeuille à risque (PAR)."""
    if days_overdue <= 0:
        return CollectionCase.ParClass.HEALTHY
    if days_overdue <= 30:
        return CollectionCase.ParClass.PAR1
    if days_overdue <= 90:
        return CollectionCase.ParClass.PAR30
    if days_overdue <= 180:
        return CollectionCase.ParClass.PAR90
    return CollectionCase.ParClass.PAR180


def _loan_fully_settled(loan: Loan) -> bool:
    unpaid = loan.installments.exclude(status=Installment.Status.PAID).exists()
    return not unpaid


@transaction.atomic
def refresh_loan_overdue(loan: Loan, as_of=None):
    """
    Recalcule le retard d'un prêt, met à jour le statut des échéances et
    crée/actualise le dossier de recouvrement associé.
    """
    as_of = as_of or date.today()

    # Remet à PENDING les échéances futures encore marquées OVERDUE/PARTIAL
    # si elles sont entièrement payées (déjà géré ailleurs) — ici on traite
    # surtout les échéances échues non soldées.
    overdue_qs = loan.installments.filter(
        due_date__lt=as_of,
    ).exclude(status=Installment.Status.PAID)

    for inst in overdue_qs:
        remaining = inst.total_due - inst.amount_paid
        if remaining <= 0:
            inst.status = Installment.Status.PAID
            inst.amount_paid = inst.total_due
        elif inst.amount_paid > 0:
            inst.status = Installment.Status.PARTIAL
        else:
            inst.status = Installment.Status.OVERDUE
        inst.save(update_fields=["status", "amount_paid"])

    overdue_qs = loan.installments.filter(
        due_date__lt=as_of,
    ).exclude(status=Installment.Status.PAID)

    agg = overdue_qs.aggregate(total=Sum("total_due"), paid=Sum("amount_paid"))
    overdue_amount = (agg["total"] or Decimal("0")) - (agg["paid"] or Decimal("0"))

    oldest = overdue_qs.order_by("due_date").first()
    days_overdue = (as_of - oldest.due_date).days if oldest else 0

    if days_overdue <= 0 and overdue_amount <= 0:
        CollectionCase.objects.filter(loan=loan).update(
            days_overdue=0,
            overdue_amount=0,
            par_class=CollectionCase.ParClass.HEALTHY,
            stage=CollectionCase.Stage.CLOSED,
        )
        if _loan_fully_settled(loan) and loan.status == Loan.Status.ACTIVE:
            loan.status = Loan.Status.CLOSED
            loan.save(update_fields=["status"])
        return CollectionCase.objects.filter(loan=loan).first()

    case, created = CollectionCase.objects.get_or_create(
        loan=loan, defaults={"tenant_id": loan.tenant_id}
    )
    case.days_overdue = max(days_overdue, 0)
    case.overdue_amount = max(overdue_amount, 0)
    case.par_class = classify_par(case.days_overdue)
    # Rouvrir un dossier clôturé s'il y a de nouveau du retard
    if case.stage == CollectionCase.Stage.CLOSED or created:
        case.stage = CollectionCase.Stage.AMICABLE
    case.save()
    return case


@transaction.atomic
def apply_repayment_to_schedule(repayment: Repayment, *, as_of=None):
    """
    Alloue un encaissement sur les échéances du prêt (FIFO par date d'échéance).
    Puis recalcule le retard / dossier de recouvrement.
    """
    as_of = as_of or repayment.payment_date or date.today()
    remaining = Decimal(repayment.amount)
    if remaining <= 0:
        return refresh_loan_overdue(repayment.loan, as_of=as_of)

    installments = (
        repayment.loan.installments.exclude(status=Installment.Status.PAID)
        .order_by("due_date", "number")
        .select_for_update()
    )

    for inst in installments:
        if remaining <= 0:
            break
        balance = Decimal(inst.total_due) - Decimal(inst.amount_paid)
        if balance <= 0:
            inst.status = Installment.Status.PAID
            inst.amount_paid = inst.total_due
            inst.save(update_fields=["status", "amount_paid"])
            continue
        pay = min(remaining, balance)
        inst.amount_paid = Decimal(inst.amount_paid) + pay
        remaining -= pay
        if inst.amount_paid >= inst.total_due:
            inst.amount_paid = inst.total_due
            inst.status = Installment.Status.PAID
        elif inst.due_date < as_of:
            inst.status = Installment.Status.PARTIAL
        else:
            inst.status = Installment.Status.PARTIAL
        inst.save(update_fields=["status", "amount_paid"])

    _mark_kept_promises(repayment)
    return refresh_loan_overdue(repayment.loan, as_of=as_of)


def _mark_kept_promises(repayment: Repayment):
    """Marque les promesses PENDING couvertes par un encaissement récent."""
    case = getattr(repayment.loan, "collection_case", None)
    if case is None:
        return
    pending = case.promises.filter(status=PaymentPromise.Status.PENDING).order_by(
        "promised_date"
    )
    leftover = Decimal(repayment.amount)
    for promise in pending:
        if leftover <= 0:
            break
        if Decimal(promise.amount) <= leftover:
            promise.status = PaymentPromise.Status.KEPT
            promise.save(update_fields=["status"])
            leftover -= Decimal(promise.amount)


@transaction.atomic
def refresh_broken_promises(as_of=None):
    """Passe en BROKEN les promesses PENDING dont la date est dépassée."""
    as_of = as_of or timezone.localdate()
    return PaymentPromise.objects.filter(
        status=PaymentPromise.Status.PENDING,
        promised_date__lt=as_of,
    ).update(status=PaymentPromise.Status.BROKEN)


def record_repayment(
    *,
    loan: Loan,
    amount,
    payment_date=None,
    reference="",
    tenant_id=None,
) -> tuple[Repayment, CollectionCase | None]:
    """Crée un encaissement et l'applique immédiatement à l'échéancier."""
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("Le montant de l'encaissement doit être positif.")
    payment_date = payment_date or date.today()
    repayment = Repayment.objects.create(
        tenant_id=tenant_id or loan.tenant_id,
        loan=loan,
        amount=amount,
        payment_date=payment_date,
        reference=reference or "",
    )
    case = apply_repayment_to_schedule(repayment, as_of=payment_date)
    return repayment, case

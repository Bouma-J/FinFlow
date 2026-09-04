"""Services de recouvrement : PAR, encaissements, escalade, tableau de bord agent."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.credits.models import Installment, Loan

from .models import (
    CollectionAction,
    CollectionActionType,
    CollectionCase,
    CollectionEscalationRule,
    CollectionStageHistory,
    LitigationFile,
    LoanRestructure,
    PaymentPromise,
    Repayment,
    WriteOff,
)

STAGE_RANK = {
    CollectionCase.Stage.AMICABLE: 0,
    CollectionCase.Stage.PRECONTENTIOUS: 1,
    CollectionCase.Stage.LITIGATION: 2,
    CollectionCase.Stage.CLOSED: -1,
}

DEFAULT_ESCALATION_RULES = (
    (31, CollectionCase.Stage.PRECONTENTIOUS, "Précontentieux dès 31 j"),
    (91, CollectionCase.Stage.LITIGATION, "Contentieux dès 91 j"),
)


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
    return not loan.installments.exclude(status=Installment.Status.PAID).exists()


def ensure_default_escalation_rules(tenant) -> int:
    """Crée les règles d'escalade par défaut si absentes."""
    created = 0
    # all_tenants : hors ContextVar tenant (ex. sync_role_packs).
    for days, stage, label in DEFAULT_ESCALATION_RULES:
        _, was_created = CollectionEscalationRule.all_tenants.get_or_create(
            tenant=tenant,
            min_days_overdue=days,
            defaults={
                "target_stage": stage,
                "label": label,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
    return created


@transaction.atomic
def change_case_stage(
    case: CollectionCase,
    to_stage: str,
    *,
    user=None,
    reason: str = "",
    automatic: bool = False,
) -> CollectionCase:
    """Change le stade et enregistre l'historique."""
    from_stage = case.stage or ""
    if from_stage == to_stage:
        return case
    case.stage = to_stage
    case.stage_changed_at = timezone.now()
    case.save(update_fields=["stage", "stage_changed_at"])
    CollectionStageHistory.objects.create(
        tenant_id=case.tenant_id,
        case=case,
        from_stage=from_stage,
        to_stage=to_stage,
        reason=reason or ("Escalade automatique" if automatic else ""),
        automatic=automatic,
        changed_by=user if user and getattr(user, "is_authenticated", False) else None,
    )
    return case


def suggested_stage_for_days(tenant_id, days_overdue: int) -> str | None:
    """Retourne le stade cible le plus élevé applicable selon les règles actives."""
    ensure_default_escalation_rules_by_id(tenant_id)
    rules = (
        CollectionEscalationRule.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            min_days_overdue__lte=days_overdue,
        )
        .order_by("-min_days_overdue")
    )
    best = None
    best_rank = -1
    for rule in rules:
        rank = STAGE_RANK.get(rule.target_stage, -1)
        if rank > best_rank:
            best_rank = rank
            best = rule.target_stage
    return best


def ensure_default_escalation_rules_by_id(tenant_id) -> None:
    from apps.tenants.models import Tenant

    tenant = Tenant.objects.filter(pk=tenant_id).first()
    if tenant:
        ensure_default_escalation_rules(tenant)


def apply_escalation_rules(case: CollectionCase) -> CollectionCase:
    """Escalade uniquement vers le haut (jamais de baisse automatique)."""
    if case.stage == CollectionCase.Stage.CLOSED:
        return case
    target = suggested_stage_for_days(case.tenant_id, case.days_overdue)
    if not target:
        return case
    current_rank = STAGE_RANK.get(case.stage, -1)
    target_rank = STAGE_RANK.get(target, -1)
    if target_rank > current_rank:
        return change_case_stage(
            case,
            target,
            automatic=True,
            reason=f"Seuil DPD {case.days_overdue} j",
        )
    return case


@transaction.atomic
def refresh_loan_overdue(loan: Loan, as_of=None):
    """
    Recalcule le retard d'un prêt, met à jour le statut des échéances et
    crée/actualise le dossier de recouvrement associé.
    """
    as_of = as_of or date.today()

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
        case = CollectionCase.objects.filter(loan=loan).first()
        if case:
            case.days_overdue = 0
            case.overdue_amount = 0
            case.par_class = CollectionCase.ParClass.HEALTHY
            case.save(update_fields=["days_overdue", "overdue_amount", "par_class"])
            if case.stage != CollectionCase.Stage.CLOSED:
                change_case_stage(
                    case,
                    CollectionCase.Stage.CLOSED,
                    automatic=True,
                    reason="Plus d'impayé",
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
    case.save(update_fields=["days_overdue", "overdue_amount", "par_class"])

    if created:
        case.stage_changed_at = timezone.now()
        case.save(update_fields=["stage_changed_at"])
        CollectionStageHistory.objects.create(
            tenant_id=case.tenant_id,
            case=case,
            from_stage="",
            to_stage=CollectionCase.Stage.AMICABLE,
            reason="Nouveau retard",
            automatic=True,
        )
    elif case.stage == CollectionCase.Stage.CLOSED:
        change_case_stage(
            case,
            CollectionCase.Stage.AMICABLE,
            automatic=True,
            reason="Réouverture",
        )
        case.refresh_from_db()

    return apply_escalation_rules(case)


@transaction.atomic
def apply_repayment_to_schedule(repayment: Repayment, *, as_of=None):
    """Alloue un encaissement sur les échéances (FIFO) puis recalcule le retard."""
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
        else:
            inst.status = Installment.Status.PARTIAL
        inst.save(update_fields=["status", "amount_paid"])

    _mark_kept_promises(repayment)
    return refresh_loan_overdue(repayment.loan, as_of=as_of)


def _mark_kept_promises(repayment: Repayment):
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
def refresh_broken_promises(as_of=None) -> int:
    """Passe en BROKEN les promesses PENDING dont la date est dépassée."""
    as_of = as_of or timezone.localdate()
    # all_tenants : appelé depuis Celery hors ContextVar tenant.
    return PaymentPromise.all_tenants.filter(
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


def set_next_action(
    case: CollectionCase,
    *,
    action_date=None,
    action_type: str = "",
    note: str = "",
) -> CollectionCase:
    case.next_action_date = action_date
    case.next_action_type = action_type or ""
    case.next_action_note = note or ""
    case.save(
        update_fields=["next_action_date", "next_action_type", "next_action_note"]
    )
    return case


def agent_dashboard(*, user, tenant_id=None) -> dict:
    """Indicateurs portefeuille agent (ou filiale si admin sans filtre mine)."""
    today = timezone.localdate()
    month_start = today.replace(day=1)
    qs = CollectionCase.objects.exclude(stage=CollectionCase.Stage.CLOSED)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if user and not getattr(user, "is_group_level", False):
        # Portefeuille personnel si demandé côté vue ; ici base = assigné + non assignés visibles
        pass

    assigned_qs = qs.filter(assigned_to=user) if user else qs.none()
    followups = assigned_qs.filter(
        next_action_date__isnull=False,
        next_action_date__lte=today,
    ).count()
    pending_promises = PaymentPromise.objects.filter(
        case__in=assigned_qs,
        status=PaymentPromise.Status.PENDING,
    ).count()
    broken_promises = PaymentPromise.objects.filter(
        case__in=assigned_qs,
        status=PaymentPromise.Status.BROKEN,
        promised_date__gte=today - timedelta(days=30),
    ).count()
    repay_agg = Repayment.objects.filter(
        loan__collection_case__assigned_to=user,
        payment_date__gte=month_start,
    ).aggregate(count=Count("id"), total=Sum("amount"))

    by_par = {
        row["par_class"]: row["n"]
        for row in assigned_qs.values("par_class").annotate(n=Count("id"))
    }
    by_stage = {
        row["stage"]: row["n"]
        for row in assigned_qs.values("stage").annotate(n=Count("id"))
    }

    due_cases = list(
        assigned_qs.filter(next_action_date__isnull=False)
        .order_by("next_action_date")
        .select_related(
            "loan__application__client",
            "loan__application",
        )[:10]
    )
    due_followups = []
    for c in due_cases:
        app = c.loan.application
        client = getattr(app, "client", None)
        due_followups.append({
            "id": str(c.id),
            "application_reference": app.reference or "",
            "client_name": client.display_name if client else "—",
            "next_action_date": c.next_action_date.isoformat() if c.next_action_date else None,
            "next_action_type": c.next_action_type,
            "next_action_note": c.next_action_note,
            "days_overdue": c.days_overdue,
            "overdue_amount": str(c.overdue_amount),
            "par_class": c.par_class,
            "stage": c.stage,
        })

    return {
        "assigned_open": assigned_qs.count(),
        "followups_due": followups,
        "pending_promises": pending_promises,
        "broken_promises_30d": broken_promises,
        "repayments_this_month_count": repay_agg["count"] or 0,
        "repayments_this_month_amount": str(repay_agg["total"] or Decimal("0")),
        "by_par_class": by_par,
        "by_stage": by_stage,
        "due_followups": due_followups,
        "as_of": today.isoformat(),
    }


def outstanding_principal(loan: Loan) -> Decimal:
    """Capital restant dû approximé (intérêt / épargne d'abord sur les paiements partiels)."""
    total = Decimal("0")
    for inst in loan.installments.exclude(status=Installment.Status.PAID):
        interest_and_savings = Decimal(inst.interest_due) + Decimal(inst.savings_due)
        principal_paid = max(
            Decimal("0"), Decimal(inst.amount_paid) - interest_and_savings
        )
        principal_left = max(
            Decimal("0"), Decimal(inst.principal_due) - principal_paid
        )
        total += principal_left
    return total


@transaction.atomic
def apply_restructure(
    case: CollectionCase,
    *,
    new_duration_months: int,
    new_rate=None,
    first_due_date=None,
    effective_date=None,
    reason: str = "",
    user=None,
) -> LoanRestructure:
    """
    Remplace les échéances non soldées par un nouvel échéancier
    calculé sur le capital restant dû.
    """
    from apps.credits.models import RepaymentMechanism
    from apps.credits.services import compute_amortization_schedule

    loan = case.loan
    if loan.status != Loan.Status.ACTIVE:
        raise ValueError("Seuls les prêts actifs peuvent être restructurés.")
    if case.stage == CollectionCase.Stage.CLOSED:
        raise ValueError("Le dossier de recouvrement est clôturé.")
    new_duration_months = int(new_duration_months)
    if new_duration_months < 1:
        raise ValueError("La durée doit être d'au moins 1 mois.")

    outstanding = outstanding_principal(loan)
    if outstanding <= 0:
        raise ValueError("Aucun capital restant dû à restructurer.")

    effective_date = effective_date or timezone.localdate()
    first_due_date = first_due_date or (effective_date + timedelta(days=30))
    previous_rate = Decimal(loan.interest_rate)
    new_rate = Decimal(str(new_rate if new_rate is not None else previous_rate))
    previous_duration = loan.duration_months

    app = loan.application
    mechanism = getattr(app, "repayment_mechanism", None) or RepaymentMechanism.DEGRESSIVE
    periodicity = getattr(app, "periodicity", None) or "MONTHLY"

    schedule = compute_amortization_schedule(
        principal=outstanding,
        annual_rate=new_rate,
        duration_months=new_duration_months,
        periodicity=periodicity,
        start_date=effective_date,
        first_due_date=first_due_date,
        savings_rate=loan.mandatory_savings_rate or 0,
        mechanism=mechanism,
    )
    if not schedule:
        raise ValueError("Impossible de générer le nouvel échéancier.")

    unpaid = loan.installments.exclude(status=Installment.Status.PAID)
    unpaid.delete()

    start_number = (
        loan.installments.order_by("-number").values_list("number", flat=True).first()
        or 0
    ) + 1
    for row in schedule:
        Installment.objects.create(
            tenant_id=loan.tenant_id,
            loan=loan,
            number=start_number + row["number"] - 1,
            due_date=row["due_date"],
            principal_due=row["principal"],
            interest_due=row["interest"],
            savings_due=row.get("savings") or 0,
            total_due=row["total"],
            amount_paid=0,
            status=Installment.Status.PENDING,
        )

    loan.duration_months = new_duration_months
    loan.interest_rate = new_rate
    loan.first_due_date = first_due_date
    loan.save(update_fields=["duration_months", "interest_rate", "first_due_date"])

    record = LoanRestructure.objects.create(
        tenant_id=case.tenant_id,
        case=case,
        loan=loan,
        effective_date=effective_date,
        previous_duration_months=previous_duration,
        new_duration_months=new_duration_months,
        previous_rate=previous_rate,
        new_rate=new_rate,
        outstanding_principal=outstanding,
        reason=reason or "",
        status=LoanRestructure.Status.APPLIED,
        applied_by=user if user and getattr(user, "is_authenticated", False) else None,
    )

    CollectionAction.objects.create(
        tenant_id=case.tenant_id,
        case=case,
        action_type=CollectionActionType.LETTER,
        action_date=effective_date,
        result="Restructuration appliquée",
        comment=(
            f"Capital {outstanding} — durée {new_duration_months} mois — "
            f"taux {new_rate}% — {reason}"
        ).strip(" —"),
    )

    if case.stage != CollectionCase.Stage.AMICABLE:
        change_case_stage(
            case,
            CollectionCase.Stage.AMICABLE,
            user=user,
            reason="Restructuration",
            automatic=False,
        )

    refresh_loan_overdue(loan, as_of=effective_date)
    return record


@transaction.atomic
def write_off_case(
    case: CollectionCase,
    *,
    amount=None,
    write_off_date=None,
    reason: str = "",
    user=None,
) -> WriteOff:
    """Passe le prêt en perte (DEFAULTED) et clôture le dossier de recouvrement."""
    loan = case.loan
    if loan.status == Loan.Status.CLOSED:
        raise ValueError("Le prêt est déjà soldé.")
    if loan.status == Loan.Status.DEFAULTED:
        raise ValueError("Le prêt est déjà passé en perte.")

    write_off_date = write_off_date or timezone.localdate()
    if amount is None:
        amount = case.overdue_amount or outstanding_principal(loan)
    amount = Decimal(str(amount))
    if amount <= 0:
        amount = outstanding_principal(loan)

    record = WriteOff.objects.create(
        tenant_id=case.tenant_id,
        case=case,
        loan=loan,
        amount=amount,
        write_off_date=write_off_date,
        reason=reason or "",
        approved_by=user if user and getattr(user, "is_authenticated", False) else None,
    )

    loan.status = Loan.Status.DEFAULTED
    loan.save(update_fields=["status"])

    case.next_action_date = None
    case.next_action_type = ""
    case.next_action_note = ""
    case.days_overdue = 0
    case.save(
        update_fields=[
            "next_action_date",
            "next_action_type",
            "next_action_note",
            "days_overdue",
        ]
    )
    if case.stage != CollectionCase.Stage.CLOSED:
        change_case_stage(
            case,
            CollectionCase.Stage.CLOSED,
            user=user,
            reason=reason or "Passage en perte",
            automatic=False,
        )

    CollectionAction.objects.create(
        tenant_id=case.tenant_id,
        case=case,
        action_type=CollectionActionType.LEGAL,
        action_date=write_off_date,
        result="Passage en perte",
        comment=f"Montant {amount} — {reason}".strip(" —"),
    )
    return record


LITIGATION_SCALAR_FIELDS = (
    "title",
    "action_type",
    "court_name",
    "court_registry",
    "case_reference",
    "chamber",
    "lawyer",
    "bailiff",
    "mandate_start",
    "mandate_end",
    "mandate_fee",
    "mandate_notes",
    "claimed_principal",
    "claimed_interest",
    "claimed_penalties",
    "claimed_costs",
    "claimed_total",
    "notice_date",
    "filing_date",
    "service_date",
    "first_hearing_date",
    "hearing_date",
    "hearing_time",
    "hearing_location",
    "judgment_date",
    "judgment_outcome",
    "judgment_amount",
    "judgment_enforceable",
    "judgment_served_at",
    "status",
    "notes",
)

LITIGATION_FK_FIELDS = ("law_firm_id", "lawyer_party_id", "bailiff_party_id")


def _mark_case_litigation(case: CollectionCase) -> None:
    if case.stage not in (
        CollectionCase.Stage.LITIGATION,
        CollectionCase.Stage.CLOSED,
    ):
        change_case_stage(
            case,
            CollectionCase.Stage.LITIGATION,
            automatic=False,
            reason="Ouverture dossier contentieux",
        )


def _apply_litigation_data(lit: LitigationFile, data: dict) -> LitigationFile:
    updated = []
    for name in LITIGATION_SCALAR_FIELDS:
        if name in data:
            setattr(lit, name, data[name])
            updated.append(name)
    for name in ("law_firm", "lawyer_party", "bailiff_party"):
        if name in data:
            setattr(lit, name, data[name])
            updated.append(name)
        key = f"{name}_id"
        if key in data:
            setattr(lit, key, data[key])
            updated.append(key)
    # Total réclamé auto si non fourni
    if "claimed_total" not in data:
        parts = [
            lit.claimed_principal,
            lit.claimed_interest,
            lit.claimed_penalties,
            lit.claimed_costs,
        ]
        if any(p is not None for p in parts):
            total = sum((p or Decimal("0")) for p in parts)
            lit.claimed_total = total
            updated.append("claimed_total")
    if updated:
        lit.save(update_fields=list(dict.fromkeys(updated + ["updated_at"])))
    guarantee_ids = data.get("related_guarantee_ids")
    if guarantee_ids is not None:
        lit.related_guarantees.set(guarantee_ids)
    return lit


@transaction.atomic
def create_litigation(case: CollectionCase, *, data: dict) -> LitigationFile:
    """Crée une nouvelle procédure contentieuse sur le dossier."""
    lit = LitigationFile.objects.create(
        tenant_id=case.tenant_id,
        case=case,
        title=data.get("title") or "",
        status=data.get("status") or LitigationFile.Status.PRE_LITIGATION,
    )
    _apply_litigation_data(lit, data)
    _mark_case_litigation(case)
    return lit


@transaction.atomic
def upsert_litigation(
    case: CollectionCase,
    *,
    data: dict,
    litigation_id=None,
) -> LitigationFile:
    """
    Met à jour une procédure existante (id) ou la plus récente,
    sinon en crée une nouvelle.
    """
    lit = None
    if litigation_id:
        lit = LitigationFile.objects.filter(case=case, pk=litigation_id).first()
        if lit is None:
            raise ValueError("Dossier contentieux introuvable.")
    if lit is None:
        lit = (
            case.litigations.exclude(
                status__in=[
                    LitigationFile.Status.CLOSED,
                    LitigationFile.Status.ABANDONED,
                    LitigationFile.Status.SETTLED,
                ]
            )
            .order_by("-created_at")
            .first()
        )
    if lit is None:
        return create_litigation(case, data=data)
    _apply_litigation_data(lit, data)
    _mark_case_litigation(case)
    return lit


def ensure_litigation_document_categories(tenant) -> int:
    """Crée les catégories GED contentieux si absentes."""
    from apps.documents.category_seed import ensure_document_categories

    return ensure_document_categories(
        tenant,
        (
            ("LIT_ASSIGNATION", "Assignation / requête"),
            ("LIT_CONCLUSIONS", "Conclusions / mémoire"),
            ("LIT_JUDGMENT", "Jugement / ordonnance"),
            ("LIT_PV_HUISSIER", "PV huissier / saisie"),
            ("LIT_MISE_EN_DEMEURE", "Mise en demeure"),
            ("LIT_PIECE_ADVERSE", "Pièce adverse"),
            ("LIT_FACTURE", "Facture honoraires / frais"),
            ("LIT_OTHER", "Autre pièce contentieux"),
        ),
    )


def litigation_documents(litigation: LitigationFile):
    from django.contrib.contenttypes.models import ContentType

    from apps.documents.models import Document

    ct = ContentType.objects.get_for_model(LitigationFile)
    return Document.objects.filter(content_type=ct, object_id=litigation.id)


def upcoming_hearings(*, tenant_id=None, within_days: int = 30, limit: int = 50):
    """Agenda des prochaines audiences (toutes procédures ouvertes)."""
    today = timezone.localdate()
    until = today + timedelta(days=within_days)
    qs = (
        LitigationFile.objects.exclude(
            status__in=[
                LitigationFile.Status.CLOSED,
                LitigationFile.Status.ABANDONED,
            ]
        )
        .filter(hearing_date__isnull=False, hearing_date__gte=today, hearing_date__lte=until)
        .select_related(
            "case__loan__application__client",
            "law_firm",
            "lawyer_party",
        )
        .order_by("hearing_date")
    )
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    rows = []
    for lit in qs[:limit]:
        app = lit.case.loan.application
        client = getattr(app, "client", None)
        rows.append({
            "id": str(lit.id),
            "case_id": str(lit.case_id),
            "title": lit.title or lit.case_reference or "",
            "case_reference": lit.case_reference,
            "application_reference": app.reference or "",
            "client_name": client.display_name if client else "—",
            "hearing_date": lit.hearing_date.isoformat() if lit.hearing_date else None,
            "hearing_time": lit.hearing_time.isoformat() if lit.hearing_time else None,
            "hearing_location": lit.hearing_location,
            "court_name": lit.court_name,
            "status": lit.status,
            "law_firm_name": lit.law_firm.name if lit.law_firm_id else "",
        })
    return rows


def notify_upcoming_hearings(*, within_days: int = 7) -> dict:
    """
    Alerte e-mail interne (agents assignés) pour audiences à J-within_days.
    Utilise le SMTP filiale ; journalise en NotificationLog.
    """
    from apps.notifications.mail import send_email_for_tenant
    from apps.notifications.models import NotificationLog, TenantNotificationSettings

    today = timezone.localdate()
    target = today + timedelta(days=within_days)
    # all_tenants : tâche Celery hors ContextVar tenant.
    qs = (
        LitigationFile.all_tenants.filter(hearing_date=target)
        .exclude(
            status__in=[
                LitigationFile.Status.CLOSED,
                LitigationFile.Status.ABANDONED,
            ]
        )
        .select_related(
            "tenant",
            "case__assigned_to",
            "case__loan__application",
        )
    )
    sent = skipped = failed = 0
    from apps.common.tenancy import tenant_context

    for lit in qs.iterator():
        with tenant_context(lit.tenant_id):
            prefs = TenantNotificationSettings.for_tenant(lit.tenant)
            agent = lit.case.assigned_to
            email = (getattr(agent, "email", None) or "").strip()
            if not email or not prefs or not prefs.enabled:
                skipped += 1
                continue
            ref = lit.case_reference or lit.title or str(lit.id)
            subject = f"Audience contentieux le {lit.hearing_date} — {ref}"
            text = (
                f"Rappel : audience prévue le {lit.hearing_date}"
                f"{(' à ' + lit.hearing_time.strftime('%H:%M')) if lit.hearing_time else ''}"
                f" — {lit.court_name or 'juridiction n/c'}\n"
                f"Dossier recouvrement : {lit.case_id}\n"
                f"Lieu : {lit.hearing_location or '—'}"
            )
            try:
                send_email_for_tenant(
                    tenant=lit.tenant,
                    subject=subject,
                    text_body=text,
                    recipients=[email],
                    prefs=prefs,
                )
                status = NotificationLog.Status.SENT
                sent += 1
                err = ""
            except Exception as exc:  # noqa: BLE001
                status = NotificationLog.Status.FAILED
                failed += 1
                err = str(exc)
            NotificationLog.objects.create(
                tenant_id=lit.tenant_id,
                kind=NotificationLog.Kind.COLLECTION_REMINDER,
                status=status,
                subject=subject,
                recipients=[email],
                body_preview=text[:500],
                error_message=err,
            )
    return {"sent": sent, "skipped": skipped, "failed": failed, "as_of": target.isoformat()}


def send_sms_stub(*, tenant, phone: str, message: str) -> tuple[str, str]:
    """
    Stub SMS — aucun provider branché.
    Retourne (status, error_message) avec status SKIPPED.
    """
    if not phone:
        return "SKIPPED", "Aucun numéro de téléphone."
    return (
        "SKIPPED",
        "Provider SMS non configuré (stub). Message non envoyé.",
    )


def _collection_reminder_body(case: CollectionCase) -> tuple[str, str, str]:
    app = case.loan.application
    client = getattr(app, "client", None)
    name = client.display_name if client else "Client"
    ref = app.reference or str(app.id)
    amount = case.overdue_amount
    days = case.days_overdue
    subject = f"Relance de paiement — dossier {ref}"
    text = (
        f"Bonjour {name},\n\n"
        f"Nous vous rappelons qu'un impayé de {amount} est constaté "
        f"sur votre dossier {ref} ({days} jour(s) de retard).\n"
        f"Merci de régulariser votre situation dans les meilleurs délais.\n\n"
        f"Cordialement,\nLe service recouvrement"
    )
    html = (
        f"<p>Bonjour {name},</p>"
        f"<p>Nous vous rappelons qu'un impayé de <strong>{amount}</strong> "
        f"est constaté sur votre dossier <strong>{ref}</strong> "
        f"({days} jour(s) de retard).</p>"
        f"<p>Merci de régulariser votre situation dans les meilleurs délais.</p>"
        f"<p>Cordialement,<br/>Le service recouvrement</p>"
    )
    return subject, text, html


def send_collection_reminder(
    case: CollectionCase,
    *,
    channel: str = "EMAIL",
    force: bool = False,
) -> dict:
    """
    Envoie une relance EMAIL (SMTP filiale) ou SMS (stub).
    Crée une CollectionAction et un NotificationLog.
    """
    from apps.notifications.mail import send_email_for_tenant
    from apps.notifications.models import NotificationLog, TenantNotificationSettings

    channel = (channel or "EMAIL").upper()
    if case.stage == CollectionCase.Stage.CLOSED:
        return {"status": "SKIPPED", "reason": "Dossier clôturé"}

    tenant = case.tenant
    prefs = TenantNotificationSettings.for_tenant(tenant)
    client = getattr(case.loan.application, "client", None)
    subject, text, html = _collection_reminder_body(case)
    today = timezone.localdate()

    if channel == "EMAIL":
        if not force and (not prefs.enabled or not prefs.notify_collection_email):
            return {"status": "SKIPPED", "reason": "Relances e-mail désactivées"}
        email = (getattr(client, "email", None) or "").strip()
        if not email:
            log = NotificationLog.objects.create(
                tenant_id=case.tenant_id,
                kind=NotificationLog.Kind.COLLECTION_REMINDER,
                status=NotificationLog.Status.SKIPPED,
                subject=subject,
                recipients=[],
                body_preview=text[:500],
                error_message="Client sans e-mail",
            )
            return {"status": "SKIPPED", "reason": "Client sans e-mail", "log_id": str(log.id)}
        try:
            send_email_for_tenant(
                tenant=tenant,
                subject=subject,
                text_body=text,
                html_body=html,
                recipients=[email],
                prefs=prefs,
            )
            status = NotificationLog.Status.SENT
            error = ""
        except Exception as exc:  # noqa: BLE001
            status = NotificationLog.Status.FAILED
            error = str(exc)
        log = NotificationLog.objects.create(
            tenant_id=case.tenant_id,
            kind=NotificationLog.Kind.COLLECTION_REMINDER,
            status=status,
            subject=subject,
            recipients=[email],
            body_preview=text[:500],
            error_message=error,
        )
        if status == NotificationLog.Status.SENT:
            CollectionAction.objects.create(
                tenant_id=case.tenant_id,
                case=case,
                action_type=CollectionActionType.EMAIL,
                action_date=today,
                result="Relance automatique",
                comment=subject,
            )
        return {"status": status, "log_id": str(log.id), "channel": "EMAIL"}

    if channel == "SMS":
        if not force and (not prefs.enabled or not prefs.notify_collection_sms):
            return {"status": "SKIPPED", "reason": "Relances SMS désactivées"}
        phone = (getattr(client, "phone", None) or "").strip()
        sms_status, sms_error = send_sms_stub(
            tenant=tenant, phone=phone, message=text[:160]
        )
        log = NotificationLog.objects.create(
            tenant_id=case.tenant_id,
            kind=NotificationLog.Kind.COLLECTION_REMINDER,
            status=sms_status,
            subject=f"SMS — {subject}"[:255],
            recipients=[phone] if phone else [],
            body_preview=text[:160],
            error_message=sms_error,
        )
        CollectionAction.objects.create(
            tenant_id=case.tenant_id,
            case=case,
            action_type=CollectionActionType.SMS,
            action_date=today,
            result="Relance SMS (stub)",
            comment=sms_error,
        )
        return {"status": sms_status, "log_id": str(log.id), "channel": "SMS"}

    return {"status": "SKIPPED", "reason": f"Canal inconnu: {channel}"}


def send_due_collection_reminders(*, as_of=None) -> dict:
    """Relances auto pour les prochaines actions EMAIL/SMS dues."""
    as_of = as_of or timezone.localdate()
    # all_tenants : tâche Celery hors ContextVar tenant.
    qs = (
        CollectionCase.all_tenants.exclude(stage=CollectionCase.Stage.CLOSED)
        .filter(
            next_action_date__isnull=False,
            next_action_date__lte=as_of,
            next_action_type__in=[
                CollectionActionType.EMAIL,
                CollectionActionType.SMS,
            ],
        )
        .select_related(
            "tenant",
            "loan__application__client",
        )
    )
    stats = {"email_sent": 0, "sms_stub": 0, "skipped": 0, "failed": 0}
    from apps.common.tenancy import tenant_context

    for case in qs.iterator():
        with tenant_context(case.tenant_id):
            result = send_collection_reminder(case, channel=case.next_action_type)
            status = result.get("status")
            if status == "SENT":
                stats["email_sent"] += 1
                set_next_action(case, action_date=None, action_type="", note="")
            elif status == "SKIPPED" and case.next_action_type == CollectionActionType.SMS:
                stats["sms_stub"] += 1
                set_next_action(case, action_date=None, action_type="", note="")
            elif status == "FAILED":
                stats["failed"] += 1
            else:
                stats["skipped"] += 1
    return stats

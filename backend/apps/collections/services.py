"""Services de recouvrement : classification PAR et mise à jour des retards."""
from datetime import date

from django.db import transaction
from django.db.models import Sum

from apps.credits.models import Installment, Loan

from .models import CollectionCase


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

    # Marque les échéances impayées échues comme en retard
    overdue_qs.update(status=Installment.Status.OVERDUE)

    agg = overdue_qs.aggregate(total=Sum("total_due"), paid=Sum("amount_paid"))
    overdue_amount = (agg["total"] or 0) - (agg["paid"] or 0)

    oldest = overdue_qs.order_by("due_date").first()
    days_overdue = (as_of - oldest.due_date).days if oldest else 0

    if days_overdue <= 0 and overdue_amount <= 0:
        # Rien à recouvrer : on clôture un éventuel dossier existant
        CollectionCase.objects.filter(loan=loan).update(
            days_overdue=0,
            overdue_amount=0,
            par_class=CollectionCase.ParClass.HEALTHY,
        )
        return None

    case, _ = CollectionCase.objects.get_or_create(
        loan=loan, defaults={"tenant_id": loan.tenant_id}
    )
    case.days_overdue = max(days_overdue, 0)
    case.overdue_amount = max(overdue_amount, 0)
    case.par_class = classify_par(case.days_overdue)
    case.save()
    return case

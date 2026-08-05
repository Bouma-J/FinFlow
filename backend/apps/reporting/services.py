"""
Agrégations pour le reporting.

Deux niveaux :
- opérationnel (filiale) : périmètre d'un seul tenant ;
- consolidé Groupe : agrégation multi-filiales avec filtres combinables
  (filiale, pays, zone, produit, segment, devise, période, statut…).

Les vues consolidées s'appuient sur le manager `all_tenants` puis
appliquent des filtres explicites (l'isolation implicite est levée
uniquement pour les utilisateurs de niveau Groupe habilités).
"""
from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
)
from django.db.models.functions import TruncMonth
from dateutil.relativedelta import relativedelta

from apps.clients.models import Client
from apps.collections.models import CollectionCase
from apps.common.access import apply_data_scope, apply_related_data_scope
from apps.contracts.models import GeneratedContract
from apps.corebanking.models import IntegrationLog
from apps.credits.models import CreditApplication, Installment, Loan
from apps.guarantees.models import Guarantee
from apps.workflow.models import ApprovalCondition, ApprovalTask, WorkflowInstance

# Axes de filtrage supportés
FILTER_FIELDS = {
    "tenant": "tenant_id",
    "country": "tenant__country",
    "zone": "tenant__zone",
    "product": "product_id",
    "product_category": "product__category_id",
    "client_type": "client__client_type",
    "currency": "currency",
    "agency": "agency_id",
    "status": "status",
    "risk_level": "risk_level",
    "owner": "created_by_id",
    "created_by": "created_by_id",
}

APPROVED_STATUSES = [
    CreditApplication.Status.APPROVED,
    CreditApplication.Status.CONTRACT_GENERATED,
    CreditApplication.Status.DISBURSEMENT_PENDING,
    CreditApplication.Status.DISBURSED,
]

PENDING_STATUSES = [
    CreditApplication.Status.DRAFT,
    CreditApplication.Status.SUBMITTED,
    CreditApplication.Status.IN_APPROVAL,
    CreditApplication.Status.RETURNED,
]

OPEN_INSTALLMENT_STATUSES = [
    Installment.Status.PENDING,
    Installment.Status.PARTIAL,
    Installment.Status.OVERDUE,
]

TREND_MONTHS = 6
RECENT_LIMIT = 8
TOP_PRODUCTS = 6


def _param(params, key):
    if params is None:
        return None
    getter = getattr(params, "get", None)
    if callable(getter):
        return getter(key)
    return params.get(key) if isinstance(params, dict) else None


def _apply_filters(qs, params):
    """Applique les filtres d'axes présents dans les paramètres de requête."""
    for key, field in FILTER_FIELDS.items():
        value = _param(params, key)
        if value:
            qs = qs.filter(**{field: value})
    date_from = _param(params, "date_from")
    date_to = _param(params, "date_to")
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


def _apply_user_scope(applications, user):
    """Honore data_scope pour les utilisateurs filiale (pas Groupe)."""
    if not user or not user.is_authenticated:
        return applications
    if getattr(user, "is_group_level", False):
        return applications
    return apply_data_scope(applications, user, agency_field="agency", owner_field="created_by")


def credit_kpis(application_qs):
    """Indicateurs synthétiques sur un ensemble de dossiers."""
    agg = application_qs.aggregate(
        total=Count("id"),
        amount_requested=Sum("amount_requested"),
        approved_amount=Sum(
            "amount_approved", filter=Q(status__in=APPROVED_STATUSES)
        ),
        approved_count=Count("id", filter=Q(status__in=APPROVED_STATUSES)),
        rejected_count=Count(
            "id", filter=Q(status=CreditApplication.Status.REJECTED)
        ),
        returned_count=Count(
            "id", filter=Q(status=CreditApplication.Status.RETURNED)
        ),
        draft_count=Count(
            "id", filter=Q(status=CreditApplication.Status.DRAFT)
        ),
        disbursed_count=Count(
            "id", filter=Q(status=CreditApplication.Status.DISBURSED)
        ),
        disbursed_amount=Sum(
            "amount_approved",
            filter=Q(status=CreditApplication.Status.DISBURSED),
        ),
        pending_count=Count("id", filter=Q(status__in=PENDING_STATUSES)),
        in_approval_count=Count(
            "id", filter=Q(status=CreditApplication.Status.IN_APPROVAL)
        ),
        contract_generated_count=Count(
            "id",
            filter=Q(status=CreditApplication.Status.CONTRACT_GENERATED),
        ),
        disbursement_pending_count=Count(
            "id",
            filter=Q(status=CreditApplication.Status.DISBURSEMENT_PENDING),
        ),
        disbursement_pending_amount=Sum(
            "amount_approved",
            filter=Q(status=CreditApplication.Status.DISBURSEMENT_PENDING),
        ),
    )
    agg["amount_approved"] = agg.pop("approved_amount")
    by_status = list(
        application_qs.values("status")
        .annotate(count=Count("id"), amount=Sum("amount_requested"))
        .order_by("-count")
    )
    by_product = list(
        application_qs.exclude(product__isnull=True)
        .values("product__label")
        .annotate(count=Count("id"), amount=Sum("amount_requested"))
        .order_by("-count")[:TOP_PRODUCTS]
    )
    by_product = [
        {
            "product": row["product__label"],
            "count": row["count"],
            "amount": row["amount"],
        }
        for row in by_product
    ]
    by_agency = list(
        application_qs.exclude(agency__isnull=True)
        .values("agency_id", "agency__name", "agency__code")
        .annotate(count=Count("id"), amount=Sum("amount_requested"))
        .order_by("-count")[:8]
    )
    by_agency = [
        {
            "agency_id": str(row["agency_id"]),
            "agency": row["agency__name"] or row["agency__code"] or "—",
            "count": row["count"],
            "amount": row["amount"],
        }
        for row in by_agency
    ]
    return {
        "summary": agg,
        "by_status": by_status,
        "by_product": by_product,
        "by_agency": by_agency,
    }


def monthly_trend(application_qs):
    """Nombre de dossiers et montant demandé par mois (N derniers mois)."""
    today = date.today()
    start = (today.replace(day=1)) - relativedelta(months=TREND_MONTHS - 1)
    rows = (
        application_qs.filter(created_at__date__gte=start)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"), amount=Sum("amount_requested"))
        .order_by("month")
    )
    indexed = {}
    for row in rows:
        month = row["month"]
        key = f"{month.year:04d}-{month.month:02d}"
        indexed[key] = {"count": row["count"], "amount": row["amount"] or 0}
    series = []
    for i in range(TREND_MONTHS):
        m = start + relativedelta(months=i)
        key = f"{m.year:04d}-{m.month:02d}"
        entry = indexed.get(key, {"count": 0, "amount": 0})
        series.append(
            {"month": key, "count": entry["count"], "amount": entry["amount"]}
        )
    return series


def recent_applications(application_qs):
    """Derniers dossiers créés (fil d'activité)."""
    rows = application_qs.select_related(
        "client", "product", "created_by", "agency"
    ).order_by("-created_at")[:RECENT_LIMIT]
    result = []
    for app in rows:
        result.append({
            "id": str(app.id),
            "reference": app.reference,
            "client": app.client.display_name if app.client_id else "—",
            "product": app.product.label if app.product_id else "—",
            "amount": app.amount_requested,
            "status": app.status,
            "created_at": app.created_at,
            "owner": str(app.created_by) if app.created_by_id else "—",
            "agency": app.agency.name if app.agency_id else "—",
        })
    return result


def portfolio_kpis(loan_qs, installment_qs):
    """Encours et santé du portefeuille de prêts."""
    outstanding = installment_qs.filter(
        status__in=OPEN_INSTALLMENT_STATUSES
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                F("total_due") - F("amount_paid"),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
        )
    )["total"] or 0
    return {
        "active_loans": loan_qs.filter(status=Loan.Status.ACTIVE).count(),
        "total_loans": loan_qs.count(),
        "disbursed_total": loan_qs.aggregate(total=Sum("principal"))["total"] or 0,
        "outstanding": outstanding,
        "overdue_installments": installment_qs.filter(
            status=Installment.Status.OVERDUE
        ).count(),
    }


def client_kpis(client_qs, params=None):
    """Répartition et acquisition de la clientèle."""
    date_from = _param(params, "date_from")
    date_to = _param(params, "date_to")
    if date_from or date_to:
        period_qs = client_qs
        if date_from:
            period_qs = period_qs.filter(created_at__date__gte=date_from)
        if date_to:
            period_qs = period_qs.filter(created_at__date__lte=date_to)
        new_in_period = period_qs.count()
        new_label = "period"
    else:
        first_of_month = date.today().replace(day=1)
        new_in_period = client_qs.filter(
            created_at__date__gte=first_of_month
        ).count()
        new_label = "month"
    by_type = list(
        client_qs.values("client_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return {
        "total": client_qs.count(),
        "by_type": by_type,
        "new_this_month": new_in_period,
        "new_period_label": new_label,
    }


def par_kpis(case_qs):
    """Répartition du portefeuille à risque."""
    open_cases = case_qs.exclude(stage=CollectionCase.Stage.CLOSED)
    return {
        "by_par_class": list(
            case_qs.values("par_class")
            .annotate(count=Count("id"), amount=Sum("overdue_amount"))
            .order_by("par_class")
        ),
        "by_stage": list(
            open_cases.values("stage")
            .annotate(count=Count("id"), amount=Sum("overdue_amount"))
            .order_by("stage")
        ),
        "open_cases": open_cases.count(),
        "total_overdue": case_qs.aggregate(total=Sum("overdue_amount"))["total"]
        or 0,
    }


def guarantee_kpis(guarantee_qs):
    active = guarantee_qs.filter(status=Guarantee.Status.ACTIVE)
    return {
        "count": guarantee_qs.count(),
        "active_count": active.count(),
        "total_current_value": guarantee_qs.aggregate(
            total=Sum("current_value")
        )["total"]
        or 0,
        "active_value": active.aggregate(total=Sum("current_value"))["total"] or 0,
    }


def contract_kpis(contract_qs):
    return {
        "generated": contract_qs.filter(
            status=GeneratedContract.Status.GENERATED
        ).count(),
        "signed": contract_qs.filter(
            status=GeneratedContract.Status.SIGNED
        ).count(),
        "total": contract_qs.exclude(
            status=GeneratedContract.Status.CANCELLED
        ).count(),
    }


def workflow_kpis(application_qs, user=None):
    """Tâches et réserves liées aux dossiers du périmètre."""
    app_ids = application_qs.values_list("id", flat=True)
    ct = ContentType.objects.get_for_model(CreditApplication)
    instances = WorkflowInstance.all_tenants.filter(
        content_type=ct,
        object_id__in=app_ids,
        status__in=[
            WorkflowInstance.Status.IN_PROGRESS,
            WorkflowInstance.Status.AWAITING_CONDITIONS,
        ],
    )
    pending_tasks = ApprovalTask.all_tenants.filter(
        instance__in=instances,
        status=ApprovalTask.Status.PENDING,
    )
    my_pending = 0
    if user and user.is_authenticated and not getattr(user, "is_group_level", False):
        group_ids = list(user.groups.values_list("id", flat=True))
        if group_ids:
            my_pending = pending_tasks.filter(
                step__required_group_id__in=group_ids
            ).count()
    conditions_pending = ApprovalCondition.all_tenants.filter(
        application_id__in=app_ids,
        status__in=[
            ApprovalCondition.Status.PENDING,
            ApprovalCondition.Status.LIFTED,
        ],
    ).count()
    return {
        "pending_tasks": pending_tasks.count(),
        "my_pending_tasks": my_pending,
        "conditions_pending": conditions_pending,
    }


def cbs_kpis(tenant_id):
    if not tenant_id:
        qs = IntegrationLog.all_tenants.all()
    else:
        qs = IntegrationLog.all_tenants.filter(tenant_id=tenant_id)
    return {
        "failed": qs.filter(status=IntegrationLog.Status.FAILED).count(),
        "pending": qs.filter(status=IntegrationLog.Status.PENDING).count(),
        "retry": qs.filter(status=IntegrationLog.Status.RETRY).count(),
    }


def build_dashboard(tenant_id=None, params=None, user=None):
    """Construit un tableau de bord (filiale si tenant_id fourni, sinon Groupe)."""
    params = params or {}
    applications = CreditApplication.all_tenants.all()
    guarantees = Guarantee.all_tenants.all()
    cases = CollectionCase.all_tenants.all()
    clients = Client.all_tenants.all()
    loans = Loan.all_tenants.all()
    installments = Installment.all_tenants.all()
    contracts = GeneratedContract.all_tenants.all()

    if tenant_id is not None:
        applications = applications.filter(tenant_id=tenant_id)
        guarantees = guarantees.filter(tenant_id=tenant_id)
        cases = cases.filter(tenant_id=tenant_id)
        clients = clients.filter(tenant_id=tenant_id)
        loans = loans.filter(tenant_id=tenant_id)
        installments = installments.filter(tenant_id=tenant_id)
        contracts = contracts.filter(tenant_id=tenant_id)

    applications = _apply_user_scope(applications, user)
    applications = _apply_filters(applications, params)

    # Cascade des filtres dossiers → objets liés
    app_subq = applications.values("id")
    loans = loans.filter(application_id__in=app_subq)
    installments = installments.filter(loan__application_id__in=app_subq)
    contracts = contracts.filter(application_id__in=app_subq)
    cases = cases.filter(loan__application_id__in=app_subq)

    agency = _param(params, "agency")
    client_type = _param(params, "client_type")
    if agency:
        guarantees = guarantees.filter(
            Q(agency_id=agency) | Q(application_id__in=app_subq)
        )
        clients = clients.filter(agency_id=agency)
    else:
        guarantees = guarantees.filter(
            Q(application_id__in=app_subq) | Q(application__isnull=True)
        )
        if user and not getattr(user, "is_group_level", False):
            guarantees = apply_data_scope(
                guarantees, user, agency_field="agency", owner_field="created_by"
            )
            clients = apply_data_scope(
                clients, user, agency_field="agency", owner_field="created_by"
            )
    if client_type:
        clients = clients.filter(client_type=client_type)
        guarantees = guarantees.filter(client__client_type=client_type)

    if user and not getattr(user, "is_group_level", False):
        cases = apply_related_data_scope(cases, user, "loan__application__agency")

    credits = credit_kpis(applications)
    credits["monthly"] = monthly_trend(applications)
    credits["recent"] = recent_applications(applications)

    include_cbs = bool(
        user
        and (
            getattr(user, "is_superuser", False)
            or getattr(user, "is_group_level", False)
            or user.has_perm("corebanking.view_integrationlog")
        )
    )

    payload = {
        "scope": "FILIALE" if tenant_id else "GROUPE",
        "filters_applied": {
            k: _param(params, k)
            for k in (
                "date_from",
                "date_to",
                "agency",
                "owner",
                "created_by",
                "status",
                "product",
                "client_type",
                "currency",
                "risk_level",
            )
            if _param(params, k)
        },
        "credits": credits,
        "portfolio": portfolio_kpis(loans, installments),
        "clients": client_kpis(clients, params),
        "guarantees": guarantee_kpis(guarantees),
        "contracts": contract_kpis(contracts),
        "workflow": workflow_kpis(applications, user=user),
        "risk": par_kpis(cases),
    }
    if include_cbs:
        payload["cbs"] = cbs_kpis(tenant_id)
    return payload


def build_group_breakdown(params, dimension="tenant"):
    """Décomposition consolidée Groupe selon un axe (drill-down)."""
    field = FILTER_FIELDS.get(dimension, "tenant_id")
    qs = _apply_filters(CreditApplication.all_tenants.all(), params)
    return list(
        qs.values(field)
        .annotate(
            count=Count("id"),
            amount_requested=Sum("amount_requested"),
            amount_approved=Sum(
                "amount_approved", filter=Q(status__in=APPROVED_STATUSES)
            ),
        )
        .order_by("-count")
    )

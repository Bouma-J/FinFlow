"""Services métier : main levée et dation en paiement."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.corebanking.services import (
    CoreBankingError,
    assert_client_outstanding_for_dation,
    assert_loan_settled,
    get_client_outstanding,
    get_loan_status,
)
from apps.credits.amounts import reference_amount
from apps.workflow.models import WorkflowDefinition
from apps.workflow.services import WorkflowError, start_workflow

from .models import (
    DationAsset,
    DationRequest,
    Guarantee,
    GuaranteeMovement,
    GuaranteeReleaseRequest,
)


class ProcessError(Exception):
    """Erreur métier des processus main levée / dation."""


def _next_reference(prefix: str, model, tenant_id) -> str:
    today = timezone.now().strftime("%Y%m%d")
    count = (
        model.all_tenants.filter(tenant_id=tenant_id, created_at__date=date.today())
        .count()
        + 1
    )
    return f"{prefix}-{today}-{count:04d}"


def _resolve_loan_ref(guarantee, loan=None, cbs_loan_reference="") -> tuple:
    """Retourne (loan, cbs_ref)."""
    ref = (cbs_loan_reference or "").strip()
    resolved_loan = loan
    if resolved_loan is None and guarantee.application_id:
        resolved_loan = getattr(guarantee.application, "loan", None)
    if not ref and resolved_loan is not None:
        ref = (resolved_loan.core_banking_reference or "").strip()
    if not ref and guarantee.application_id:
        app = guarantee.application
        ref = (getattr(app, "client_account_number", None) or "").strip()
    return resolved_loan, ref


@transaction.atomic
def initiate_release_request(
    *,
    guarantee,
    user,
    comment="",
    cbs_loan_reference="",
    loan=None,
    request_date=None,
    release_fees=None,
    cbs_client_id="",
):
    """Vérifie CBS (prêt soldé) puis démarre le circuit MAIN_LEVEE."""
    if guarantee.status != Guarantee.Status.ACTIVE:
        raise ProcessError(
            "Seule une garantie active peut faire l'objet d'une main levée."
        )
    if GuaranteeReleaseRequest.objects.filter(
        guarantee=guarantee,
        status__in=[
            GuaranteeReleaseRequest.Status.DRAFT,
            GuaranteeReleaseRequest.Status.IN_APPROVAL,
            GuaranteeReleaseRequest.Status.RETURNED,
        ],
    ).exists():
        raise ProcessError(
            "Une demande de main levée est déjà en cours pour cette garantie."
        )

    loan_obj, loan_ref = _resolve_loan_ref(guarantee, loan, cbs_loan_reference)
    if not loan_ref:
        raise ProcessError(
            "Référence prêt CBS manquante : sélectionnez un crédit soldé "
            "ou renseignez la référence CBS."
        )
    currency = "XAF"
    if guarantee.application_id and getattr(guarantee.application, "currency", None):
        currency = guarantee.application.currency

    try:
        cbs = assert_loan_settled(
            guarantee.tenant_id, loan_ref, currency=currency
        )
    except CoreBankingError as exc:
        raise ProcessError(str(exc)) from exc

    fees = None
    if release_fees not in (None, ""):
        try:
            fees = Decimal(str(release_fees))
        except (InvalidOperation, TypeError) as exc:
            raise ProcessError("Frais de main levée invalides.") from exc

    parsed_date = request_date
    if isinstance(request_date, str) and request_date.strip():
        try:
            parsed_date = date.fromisoformat(request_date.strip()[:10])
        except ValueError as exc:
            raise ProcessError("Date de demande invalide.") from exc
    elif not request_date:
        parsed_date = timezone.now().date()

    cbs_id = (
        cbs_client_id
        or getattr(guarantee.client, "cbs_client_id", "")
        or ""
    ).strip()

    req = GuaranteeReleaseRequest(
        guarantee=guarantee,
        application_id=guarantee.application_id
        or getattr(loan_obj, "application_id", None),
        loan=loan_obj,
        agency_id=guarantee.agency_id,
        cbs_loan_reference=loan_ref,
        cbs_client_id=cbs_id,
        cbs_settled=cbs["settled"],
        cbs_outstanding=cbs["outstanding"],
        cbs_currency=cbs["currency"],
        cbs_checked_at=timezone.now(),
        cbs_raw=cbs.get("raw") or {},
        request_date=parsed_date,
        release_fees=fees,
        status=GuaranteeReleaseRequest.Status.IN_APPROVAL,
        comment=comment or "",
        created_by=user,
        updated_by=user,
    )
    req.reference = _next_reference("ML", GuaranteeReleaseRequest, guarantee.tenant_id)
    req.save()

    amount = fees if fees is not None else (
        guarantee.current_value or guarantee.expertise_value or 0
    )
    try:
        start_workflow(
            req,
            amount=amount,
            risk_level=None,
            target_type=WorkflowDefinition.TargetType.MAIN_LEVEE,
        )
    except WorkflowError as exc:
        raise ProcessError(str(exc)) from exc

    return req


def release_client_context(*, client, tenant_id=None) -> dict:
    """
    Contexte pour composer une main levée :
    - matricule CBS (fiche client) ;
    - garanties actives Fin Flow ;
    - crédits / prêts du client avec statut CBS (soldé / actif).
    """
    from apps.credits.models import CreditApplication, Loan
    from apps.guarantees.serializers import GuaranteeSerializer

    tid = tenant_id or client.tenant_id
    cbs_id = (getattr(client, "cbs_client_id", "") or "").strip()

    open_statuses = [
        GuaranteeReleaseRequest.Status.DRAFT,
        GuaranteeReleaseRequest.Status.IN_APPROVAL,
        GuaranteeReleaseRequest.Status.RETURNED,
        GuaranteeReleaseRequest.Status.APPROVED,
        GuaranteeReleaseRequest.Status.BLOCKED,
    ]
    busy_ids = set(
        GuaranteeReleaseRequest.objects.filter(
            guarantee__client_id=client.pk,
            status__in=open_statuses,
        ).values_list("guarantee_id", flat=True)
    )
    guarantees_qs = (
        Guarantee.objects.filter(
            client_id=client.pk,
            status=Guarantee.Status.ACTIVE,
        )
        .exclude(id__in=busy_ids)
        .select_related("application", "agency")
        .order_by("-created_at")
    )

    apps = (
        CreditApplication.objects.filter(client_id=client.pk)
        .select_related("product")
        .order_by("-created_at")
    )
    loans_by_app = {
        loan.application_id: loan
        for loan in Loan.objects.filter(application__client_id=client.pk)
    }

    credits = []
    for app in apps:
        loan = loans_by_app.get(app.pk)
        currency = getattr(app, "currency", None) or "XAF"
        loan_ref = ""
        if loan and loan.core_banking_reference:
            loan_ref = loan.core_banking_reference.strip()
        elif getattr(app, "client_account_number", None):
            loan_ref = (app.client_account_number or "").strip()

        cbs_info = {
            "cbs_loan_reference": loan_ref,
            "cbs_settled": None,
            "cbs_outstanding": None,
            "cbs_currency": currency,
            "cbs_error": None,
            "cbs_status_label": "Non vérifié",
        }
        if loan_ref:
            try:
                cbs = get_loan_status(tid, loan_ref, currency=currency)
                cbs_info.update(
                    {
                        "cbs_settled": cbs["settled"],
                        "cbs_outstanding": str(cbs["outstanding"]),
                        "cbs_currency": cbs["currency"],
                        "cbs_status_label": "Soldé" if cbs["settled"] else "Actif",
                    }
                )
            except CoreBankingError as exc:
                cbs_info["cbs_error"] = str(exc)
                cbs_info["cbs_status_label"] = "Erreur CBS"

        credits.append(
            {
                "application_id": str(app.pk),
                "application_reference": app.reference,
                "application_status": app.status,
                "application_status_display": app.get_status_display(),
                "product_label": getattr(app.product, "label", "") if app.product_id else "",
                "amount": str(reference_amount(app) or 0),
                "currency": currency,
                "loan_id": str(loan.pk) if loan else None,
                "loan_status": loan.status if loan else None,
                "loan_status_display": loan.get_status_display() if loan else None,
                "disbursed_at": loan.disbursed_at.isoformat() if loan and loan.disbursed_at else None,
                **cbs_info,
            }
        )

    return {
        "client_id": str(client.pk),
        "client_display": getattr(client, "display_name", str(client)),
        "cbs_client_id": cbs_id,
        "guarantees": GuaranteeSerializer(guarantees_qs, many=True).data,
        "credits": credits,
    }


@transaction.atomic
def complete_release_request(request: GuaranteeReleaseRequest):
    """Re-vérifie CBS puis applique la main levée sur la garantie."""
    guarantee = request.guarantee
    currency = request.cbs_currency or "XAF"
    try:
        cbs = assert_loan_settled(
            request.tenant_id,
            request.cbs_loan_reference,
            currency=currency,
        )
    except CoreBankingError as exc:
        request.status = GuaranteeReleaseRequest.Status.BLOCKED
        request.cbs_settled = False
        request.cbs_checked_at = timezone.now()
        request.comment = (
            (request.comment + "\n" if request.comment else "")
            + f"[CBS] {exc}"
        )
        request.save()
        return request

    request.cbs_settled = cbs["settled"]
    request.cbs_outstanding = cbs["outstanding"]
    request.cbs_currency = cbs["currency"]
    request.cbs_checked_at = timezone.now()
    request.cbs_raw = cbs.get("raw") or {}

    GuaranteeMovement.objects.create(
        guarantee=guarantee,
        movement_type=GuaranteeMovement.MovementType.RELEASE,
        movement_date=timezone.now().date(),
        value=guarantee.current_value,
        comment=f"Main levée {request.reference}",
    )
    guarantee.status = Guarantee.Status.RELEASED
    guarantee.save(update_fields=["status", "updated_at"])

    request.status = GuaranteeReleaseRequest.Status.COMPLETED
    request.completed_at = timezone.now()
    request.save()
    return request


@transaction.atomic
def initiate_dation_request(
    *,
    client,
    user,
    asset_description="",
    asset_value=None,
    application=None,
    comment="",
    cbs_client_id="",
    guarantee_ids=None,
    additional_assets=None,
):
    """
    Vérifie l'encours CBS client puis démarre le circuit DATION.

    Le dossier peut combiner :
    - des garanties existantes du client (`guarantee_ids`) ;
    - des biens additionnels (`additional_assets`: [{description, value}]).
    """
    cbs_id = (cbs_client_id or getattr(client, "cbs_client_id", "") or "").strip()
    currency = "XAF"
    if application is not None and getattr(application, "currency", None):
        currency = application.currency

    try:
        cbs = assert_client_outstanding_for_dation(
            client.tenant_id, cbs_id, currency=currency
        )
    except CoreBankingError as exc:
        raise ProcessError(str(exc)) from exc

    lines = _build_dation_asset_lines(
        client=client,
        guarantee_ids=guarantee_ids or [],
        additional_assets=additional_assets or [],
        legacy_description=asset_description or "",
        legacy_value=asset_value,
    )
    if not lines:
        raise ProcessError(
            "Ajoutez au moins une garantie existante ou un bien additionnel "
            "au dossier de dation."
        )

    total_value = sum((line["value"] or Decimal("0")) for line in lines)
    summary = " | ".join(
        (line["description"] or "Bien").strip() for line in lines
    )[:2000]

    req = DationRequest(
        client=client,
        application=application,
        agency_id=getattr(application, "agency_id", None) if application else None,
        cbs_client_id=cbs_id,
        cbs_total_outstanding=cbs["total_outstanding"],
        cbs_currency=cbs["currency"],
        cbs_checked_at=timezone.now(),
        cbs_raw=cbs.get("raw") or {},
        asset_description=summary,
        asset_value=total_value,
        status=DationRequest.Status.IN_APPROVAL,
        comment=comment or "",
        created_by=user,
        updated_by=user,
    )
    req.reference = _next_reference("DAT", DationRequest, client.tenant_id)
    req.save()

    for line in lines:
        DationAsset.objects.create(
            tenant_id=client.tenant_id,
            dation=req,
            source=line["source"],
            guarantee=line.get("guarantee"),
            description=line["description"],
            value=line["value"],
        )

    amount = total_value or cbs["total_outstanding"] or 0
    try:
        start_workflow(
            req,
            amount=amount,
            risk_level=None,
            target_type=WorkflowDefinition.TargetType.DATION,
        )
    except WorkflowError as exc:
        raise ProcessError(str(exc)) from exc

    return req


def _to_decimal_or_none(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ProcessError(f"Valeur numérique invalide : {value}") from exc


def _build_dation_asset_lines(
    *,
    client,
    guarantee_ids,
    additional_assets,
    legacy_description="",
    legacy_value=None,
):
    """Construit la liste normalisée des biens du dossier."""
    lines = []
    seen = set()

    for raw_id in guarantee_ids:
        gid = str(raw_id).strip()
        if not gid or gid in seen:
            continue
        seen.add(gid)
        try:
            guarantee = Guarantee.objects.get(pk=gid, client_id=client.pk)
        except Guarantee.DoesNotExist as exc:
            raise ProcessError(
                f"Garantie introuvable pour ce client : {gid}."
            ) from exc
        if guarantee.status != Guarantee.Status.ACTIVE:
            raise ProcessError(
                f"La garantie {guarantee.reference or gid} n'est pas active."
            )
        value = (
            guarantee.current_value
            or guarantee.value_to_consider
            or guarantee.expertise_value
        )
        label = guarantee.get_guarantee_type_display()
        ref = guarantee.reference or str(guarantee.pk)[:8]
        desc = f"{label} — {ref}"
        if guarantee.description:
            desc = f"{desc} : {guarantee.description}"
        lines.append(
            {
                "source": DationAsset.Source.EXISTING_GUARANTEE,
                "guarantee": guarantee,
                "description": desc,
                "value": value,
            }
        )

    for item in additional_assets:
        if not isinstance(item, dict):
            raise ProcessError("Chaque bien additionnel doit être un objet.")
        desc = (item.get("description") or "").strip()
        value = _to_decimal_or_none(item.get("value"))
        if not desc and value is None:
            continue
        if not desc:
            raise ProcessError(
                "La description est obligatoire pour un bien additionnel."
            )
        lines.append(
            {
                "source": DationAsset.Source.ADDITIONAL,
                "guarantee": None,
                "description": desc,
                "value": value,
            }
        )

    # Compatibilité ancien formulaire (un seul bien libre).
    if not lines and (legacy_description or legacy_value not in (None, "")):
        lines.append(
            {
                "source": DationAsset.Source.ADDITIONAL,
                "guarantee": None,
                "description": (legacy_description or "").strip() or "Bien cédé",
                "value": _to_decimal_or_none(legacy_value),
            }
        )
    return lines


def preview_dation_cbs(*, tenant_id, cbs_client_id, currency="XAF") -> dict:
    """Lecture encours CBS (créance) sans créer de demande."""
    try:
        return get_client_outstanding(
            tenant_id, cbs_client_id, currency=currency
        )
    except CoreBankingError as exc:
        raise ProcessError(str(exc)) from exc


@transaction.atomic
def complete_dation_request(request: DationRequest):
    """Re-vérifie l'encours CBS puis enregistre la garantie type DATION."""
    currency = request.cbs_currency or "XAF"
    try:
        cbs = assert_client_outstanding_for_dation(
            request.tenant_id,
            request.cbs_client_id,
            currency=currency,
        )
    except CoreBankingError as exc:
        request.status = DationRequest.Status.BLOCKED
        request.cbs_checked_at = timezone.now()
        request.comment = (
            (request.comment + "\n" if request.comment else "")
            + f"[CBS] {exc}"
        )
        request.save()
        return request

    request.cbs_total_outstanding = cbs["total_outstanding"]
    request.cbs_currency = cbs["currency"]
    request.cbs_checked_at = timezone.now()
    request.cbs_raw = cbs.get("raw") or {}

    value = request.assets_total_value() or cbs["total_outstanding"]
    description = request.asset_description or (
        f"Dation en paiement {request.reference}"
    )
    guarantee = Guarantee.objects.create(
        client=request.client,
        application=request.application,
        agency_id=request.agency_id,
        guarantee_type=Guarantee.GuaranteeType.DATION,
        description=description,
        expertise_value=value or 0,
        current_value=value or 0,
        status=Guarantee.Status.ACTIVE,
        created_by=request.created_by,
        updated_by=request.updated_by,
    )
    guarantee.reference = _next_reference("GAR-DAT", Guarantee, request.tenant_id)
    guarantee.save(update_fields=["reference", "updated_at"])

    request.resulting_guarantee = guarantee
    request.asset_value = value
    request.status = DationRequest.Status.COMPLETED
    request.completed_at = timezone.now()
    request.save()
    return request

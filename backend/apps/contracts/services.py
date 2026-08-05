"""Logique métier : statut de contractualisation et blocage du décaissement."""
from __future__ import annotations


def required_templates_for(application):
    """Modèles obligatoires (actifs) applicables à un dossier donné."""
    from .models import ContractTemplate

    templates = ContractTemplate.all_tenants.filter(
        tenant_id=application.tenant_id, is_active=True, is_required=True
    ).select_related("product")
    return [t for t in templates if t.applies_to_application(application)]


def missing_required_contracts(application) -> list[str]:
    """Retourne les intitulés des contrats obligatoires non encore générés."""
    from .models import GeneratedContract

    generated_template_ids = set(
        application.generated_contracts.exclude(
            status=GeneratedContract.Status.CANCELLED
        ).values_list("template_id", flat=True)
    )
    return [
        t.name
        for t in required_templates_for(application)
        if t.id not in generated_template_ids
    ]


def refresh_contract_status(application, user=None):
    """Passe le dossier en CONTRACT_GENERATED si tous les contrats requis sont là.

    N'intervient que sur un dossier approuvé (ou déjà en contractualisation),
    afin de ne pas court-circuiter le circuit d'approbation.
    """
    from apps.credits.models import CreditApplication

    from .models import GeneratedContract

    if application.status not in (
        CreditApplication.Status.APPROVED,
        CreditApplication.Status.CONTRACT_GENERATED,
    ):
        return

    has_any = application.generated_contracts.exclude(
        status=GeneratedContract.Status.CANCELLED
    ).exists()

    if has_any and not missing_required_contracts(application):
        if application.status != CreditApplication.Status.CONTRACT_GENERATED:
            application.status = CreditApplication.Status.CONTRACT_GENERATED
            application.save(update_fields=["status", "updated_at"])

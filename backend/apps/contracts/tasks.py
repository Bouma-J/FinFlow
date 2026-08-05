"""Tâches Celery — génération de contrats."""
import logging

from celery import shared_task
from django.db import transaction

from apps.common.tenancy import tenant_context

logger = logging.getLogger("finflow")


@shared_task(bind=True, ignore_result=False)
def generate_contract_task(
    self,
    application_id: str,
    template_id: str,
    user_id: str,
    extra_values: dict | None = None,
    tenant_id: str | None = None,
):
    """Génère un contrat hors requête HTTP."""
    from apps.accounts.models import User
    from apps.contracts.context import build_context
    from apps.contracts.models import ContractTemplate, GeneratedContract
    from apps.contracts.rendering import ContractRenderError, render_template
    from apps.contracts.services import refresh_contract_status
    from apps.credits.models import CreditApplication

    extra_values = extra_values or {}
    with tenant_context(tenant_id):
        try:
            application = CreditApplication.all_tenants.get(pk=application_id)
            template = ContractTemplate.all_tenants.get(pk=template_id)
            user = User.objects.get(pk=user_id)
        except Exception:
            logger.exception("generate_contract_task : entité introuvable")
            raise

        context = build_context(application, extra_values)
        try:
            rendered = render_template(template, context)
        except ContractRenderError:
            logger.exception("Échec rendu contrat app=%s", application_id)
            raise

        with transaction.atomic():
            application.generated_contracts.filter(template=template).exclude(
                status=GeneratedContract.Status.CANCELLED
            ).update(status=GeneratedContract.Status.CANCELLED)
            gc = GeneratedContract(
                application=application,
                template=template,
                template_name=template.name,
                category=template.category,
                context_snapshot=context,
                extra_values=extra_values,
                created_by=user,
                updated_by=user,
                tenant_id=application.tenant_id,
            )
            gc.file.save(rendered.name, rendered, save=False)
            gc.save()
            refresh_contract_status(application, user)
        return str(gc.id)

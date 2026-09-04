"""Services de provisionnement d'une nouvelle filiale."""

from apps.accounts.services import (
    DEFAULT_ROLE_PACKS,
    FILIALE_ADMIN_ROLE_NAME,
    ensure_default_role_packs,
)

DEFAULT_TENANT_ROLES = (
    FILIALE_ADMIN_ROLE_NAME,
    *DEFAULT_ROLE_PACKS.keys(),
)


def bootstrap_tenant(tenant):
    """Crée les rôles métier, référentiels catalogue, packs RBAC et connecteur Perfect."""
    from apps.catalog.defaults import ensure_catalog_defaults
    from apps.corebanking.perfect_defaults import ensure_perfect_connector
    from apps.workflow.defaults import ensure_process_workflows

    ensure_default_role_packs(tenant)
    ensure_catalog_defaults(tenant)
    ensure_perfect_connector(tenant, demo=False)
    ensure_process_workflows(tenant)

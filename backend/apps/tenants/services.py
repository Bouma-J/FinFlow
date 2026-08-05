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
    """Crée les rôles métier par défaut et synchronise leurs packs RBAC."""
    ensure_default_role_packs(tenant)

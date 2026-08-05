"""Managers et QuerySets appliquant l'isolation multi-tenants."""
from django.db import models

from .tenancy import get_current_tenant_id, is_group_context


class TenantQuerySet(models.QuerySet):
    """QuerySet filtrant automatiquement sur le tenant courant."""

    def for_current_tenant(self):
        tenant_id = get_current_tenant_id()
        # En contexte Groupe, aucune restriction implicite : les vues
        # de consolidation appliquent leurs propres filtres explicites.
        if is_group_context():
            return self
        if tenant_id is None:
            # Aucun tenant résolu : par sécurité, on ne renvoie rien.
            return self.none()
        return self.filter(tenant_id=tenant_id)


class TenantManager(models.Manager):
    """Manager par défaut : renvoie uniquement les données du tenant courant."""

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db).for_current_tenant()


class AllTenantsManager(models.Manager):
    """Manager d'échappement explicite (admin, migrations, tâches système)."""

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

"""
Enregistrement automatique de la piste d'audit.

Tout modèle héritant de `TenantScopedModel` est audité automatiquement
(création / modification / suppression), sans code supplémentaire dans
les modules métier.
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common.models import TenantScopedModel

from .context import get_current_ip, get_current_user
from .models import AuditLog


def _iter_audited_models():
    for model in TenantScopedModel.__subclasses__():
        # On ignore les classes encore abstraites.
        if not model._meta.abstract:
            yield model


def _serialize_instance(instance):
    data = {}
    for field in instance._meta.fields:
        if field.name in ("created_at", "updated_at"):
            continue
        value = getattr(instance, field.attname, None)
        data[field.name] = str(value) if value is not None else None
    return data


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    if not isinstance(instance, TenantScopedModel) or sender is AuditLog:
        return
    AuditLog.objects.create(
        tenant_id=getattr(instance, "tenant_id", None),
        user=get_current_user(),
        action=AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE,
        model_label=instance._meta.label,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=_serialize_instance(instance),
        ip_address=get_current_ip(),
    )


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if not isinstance(instance, TenantScopedModel) or sender is AuditLog:
        return
    AuditLog.objects.create(
        tenant_id=getattr(instance, "tenant_id", None),
        user=get_current_user(),
        action=AuditLog.Action.DELETE,
        model_label=instance._meta.label,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        ip_address=get_current_ip(),
    )

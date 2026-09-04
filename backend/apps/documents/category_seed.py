"""Création idempotente des catégories GED par processus métier."""


def ensure_document_categories(tenant, codes) -> int:
    """
    Crée les catégories (code, label) absentes pour la filiale.

    Utilise ``all_tenants`` pour rester fiable hors ContextVar
    (ex. sync_role_packs, Celery).
    """
    from apps.documents.models import DocumentCategory

    created = 0
    for code, label in codes:
        _, was = DocumentCategory.all_tenants.get_or_create(
            tenant=tenant,
            code=code,
            defaults={"label": label, "is_active": True},
        )
        if was:
            created += 1
    return created

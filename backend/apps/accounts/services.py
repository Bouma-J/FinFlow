"""Services liés aux comptes et rôles filiale."""
import uuid

from django.contrib.auth.models import Group, Permission
from django.db import transaction

FILIALE_ADMIN_ROLE_NAME = "Administrateur filiale"

# Rôles métier bootstrap (créés / synchronisés à chaque filiale).
CHARGE_AFFAIRE_ROLE_NAME = "Chargé d'affaire"
CHEF_AGENCE_ROLE_NAME = "Chef d'agence"
RESP_EXPLOITATION_ROLE_NAME = "Responsable exploitation"
RESP_CREDIT_RISQUE_ROLE_NAME = "Responsable crédit et risque"
ANALYSTE_CREDIT_RISQUE_ROLE_NAME = "Analyste crédit et risque"
CREDIT_COMMITTEE_ROLE_NAME = "Comité de crédit"
RESP_RETAILS_ROLE_NAME = "Responsable retails"
DIRECTEUR_GENERAL_ROLE_NAME = "Directeur Général"
RESP_JURIDIQUE_ROLE_NAME = "Responsable Juridique"
ASSISTANT_JURIDIQUE_ROLE_NAME = "Assistant juridique"
RESP_OPERATIONS_ROLE_NAME = "Responsable des opérations"
ASSISTANT_OPERATIONS_ROLE_NAME = "Assistant des opérations"
RESP_CONTROLE_INTERNE_ROLE_NAME = "Responsable contrôle interne"
ASSISTANT_CONTROLE_INTERNE_ROLE_NAME = "Assistant Contrôle Interne"
ASSISTANT_AUDIT_ROLE_NAME = "Assistant Audit"
RESP_AUDIT_ROLE_NAME = "Responsable Audit"
ASSISTANT_RECOUVREMENT_ROLE_NAME = "Assistant recouvrement"
RESP_RECOUVREMENT_ROLE_NAME = "Responsable recouvrement"
RESP_ADMIN_FINANCIER_ROLE_NAME = "Responsable administratif et financier"
CHEF_COMPTABLE_ROLE_NAME = "Chef comptable"
COMPTABLE_ROLE_NAME = "Comptable"
LECTEUR_ROLE_NAME = "Lecteur"

# Anciens rôles bootstrap — retirés, supprimés s'ils n'ont plus d'utilisateur.
LEGACY_BOOTSTRAP_ROLE_NAMES = (
    "Analyste crédit",
    "Responsable agence",
)

# Permissions Django nécessaires pour administrer une filiale
# (catalogue, crédit, GED, workflow, CBS, garanties, etc.).
FILIALE_ADMIN_APP_LABELS = (
    "accounts",
    "tenants",
    "catalog",
    "clients",
    "credits",
    "workflow",
    "documents",
    "guarantees",
    "sureties",
    "contracts",
    "corebanking",
    "collections",
    "audit",
    "notifications",
    "reporting",
)

# Permissions custom hors CRUD standard
FILIALE_ADMIN_EXTRA_PERMS = (
    ("guarantees", "initiate_dationrequest"),
    ("guarantees", "initiate_guaranteereleaserequest"),
    ("guarantees", "initiate_guaranteeformalizationrequest"),
    ("credits", "disburse_creditapplication"),
    ("credits", "initiate_disburse_creditapplication"),
)

# ---------------------------------------------------------------------------
# Blocs de permissions réutilisables
# ---------------------------------------------------------------------------

_VIEW_CLIENTS = (
    ("clients", "view_client"),
)

_VIEW_CREDIT = (
    ("credits", "view_creditapplication"),
    ("credits", "view_financialanalysis"),
    ("credits", "view_fieldvisit"),
    ("credits", "view_creditdocument"),
    ("credits", "view_analysisthreshold"),
    ("credits", "view_loan"),
)

_VIEW_GUARANTEES = (
    ("guarantees", "view_guarantee"),
    ("guarantees", "view_guaranteemovement"),
    ("guarantees", "view_guaranteereleaserequest"),
    ("guarantees", "view_dationrequest"),
    ("guarantees", "view_guaranteeformalizationrequest"),
    ("sureties", "view_surety"),
    ("sureties", "view_suretyengagement"),
)

_VIEW_CATALOG = (
    ("catalog", "view_creditproduct"),
    ("catalog", "view_productcategory"),
    ("catalog", "view_rejectreason"),
    ("catalog", "view_checklistitem"),
)

_VIEW_DOCS = (
    ("documents", "view_document"),
    ("documents", "view_documentcategory"),
)

_VIEW_CONTRACTS = (
    ("contracts", "view_contracttemplate"),
    ("contracts", "view_generatedcontract"),
)

_VIEW_WORKFLOW = (
    ("workflow", "view_approvaltask"),
    ("workflow", "view_workflowinstance"),
    ("workflow", "view_workflowdefinition"),
    ("workflow", "view_approvalstep"),
    ("workflow", "view_approvalcondition"),
)

_VIEW_CBS = (
    ("corebanking", "view_corebankingconnector"),
    ("corebanking", "view_integrationlog"),
)

_VIEW_COLLECTIONS = (
    ("collections", "view_repayment"),
    ("collections", "view_collectioncase"),
    ("collections", "view_collectionaction"),
    ("collections", "view_paymentpromise"),
    ("collections", "view_collectionstagehistory"),
    ("collections", "view_collectionescalationrule"),
    ("collections", "view_litigationfile"),
    ("collections", "view_litigationevent"),
    ("collections", "view_legalparty"),
    ("collections", "view_litigationseizure"),
    ("collections", "view_litigationcost"),
    ("collections", "view_loanrestructure"),
    ("collections", "view_writeoff"),
)

_VIEW_TRANSVERSE = (
    ("tenants", "view_agency"),
    ("audit", "view_auditlog"),
    ("notifications", "view_notificationlog"),
    ("notifications", "view_tenantnotificationsettings"),
    ("reporting", "view_dashboard"),
)

_WRITE_INSTRUCTION = (
    ("clients", "add_client"),
    ("clients", "change_client"),
    ("credits", "add_creditapplication"),
    ("credits", "change_creditapplication"),
    ("credits", "delete_creditapplication"),
    ("credits", "add_financialanalysis"),
    ("credits", "change_financialanalysis"),
    ("credits", "delete_financialanalysis"),
    ("credits", "add_fieldvisit"),
    ("credits", "change_fieldvisit"),
    ("credits", "delete_fieldvisit"),
    ("credits", "add_creditdocument"),
    ("credits", "change_creditdocument"),
    ("credits", "delete_creditdocument"),
    ("guarantees", "add_guarantee"),
    ("guarantees", "change_guarantee"),
    ("guarantees", "delete_guarantee"),
    ("guarantees", "add_guaranteemovement"),
    ("sureties", "add_surety"),
    ("sureties", "change_surety"),
    ("sureties", "delete_surety"),
    ("sureties", "add_suretyengagement"),
    ("sureties", "change_suretyengagement"),
    ("sureties", "delete_suretyengagement"),
    ("documents", "add_document"),
    ("documents", "change_document"),
    ("contracts", "add_generatedcontract"),
    ("contracts", "change_generatedcontract"),
)

_WRITE_ANALYSIS = (
    ("credits", "add_financialanalysis"),
    ("credits", "change_financialanalysis"),
    ("credits", "delete_financialanalysis"),
    ("credits", "add_fieldvisit"),
    ("credits", "change_fieldvisit"),
    ("credits", "delete_fieldvisit"),
    ("credits", "add_creditdocument"),
    ("credits", "change_creditdocument"),
    ("documents", "add_document"),
    ("documents", "change_document"),
)

_WRITE_OPERATIONS = (
    ("contracts", "add_generatedcontract"),
    ("contracts", "change_generatedcontract"),
    ("documents", "add_document"),
    ("documents", "change_document"),
    ("guarantees", "add_guarantee"),
    ("guarantees", "change_guarantee"),
    ("guarantees", "initiate_guaranteereleaserequest"),
    ("guarantees", "initiate_dationrequest"),
    ("guarantees", "initiate_guaranteeformalizationrequest"),
    ("sureties", "add_suretyengagement"),
    ("sureties", "change_suretyengagement"),
    ("credits", "disburse_creditapplication"),
    ("credits", "initiate_disburse_creditapplication"),
)

_WRITE_OPS_ASSISTANT = (
    ("contracts", "add_generatedcontract"),
    ("contracts", "change_generatedcontract"),
    ("documents", "add_document"),
    ("documents", "change_document"),
    ("guarantees", "add_guarantee"),
    ("guarantees", "change_guarantee"),
    ("sureties", "add_suretyengagement"),
    ("sureties", "change_suretyengagement"),
    ("credits", "initiate_disburse_creditapplication"),
)

_WRITE_LEGAL = (
    ("guarantees", "add_guarantee"),
    ("guarantees", "change_guarantee"),
    ("guarantees", "add_guaranteemovement"),
    ("guarantees", "initiate_guaranteereleaserequest"),
    ("guarantees", "initiate_dationrequest"),
    ("guarantees", "initiate_guaranteeformalizationrequest"),
    ("sureties", "add_surety"),
    ("sureties", "change_surety"),
    ("sureties", "add_suretyengagement"),
    ("sureties", "change_suretyengagement"),
    ("contracts", "add_generatedcontract"),
    ("contracts", "change_generatedcontract"),
    ("documents", "add_document"),
    ("documents", "change_document"),
)

_WRITE_LEGAL_ASSIST = (
    ("guarantees", "add_guarantee"),
    ("guarantees", "change_guarantee"),
    ("sureties", "add_surety"),
    ("sureties", "change_surety"),
    ("sureties", "add_suretyengagement"),
    ("sureties", "change_suretyengagement"),
    ("contracts", "add_generatedcontract"),
    ("contracts", "change_generatedcontract"),
    ("documents", "add_document"),
    ("documents", "change_document"),
)

# Contentieux : pilotage juridique (dossiers, intervenants, saisies, frais).
_WRITE_LEGAL_CONTENTIEUX = (
    ("collections", "add_litigationfile"),
    ("collections", "change_litigationfile"),
    ("collections", "add_litigationevent"),
    ("collections", "change_litigationevent"),
    ("collections", "add_legalparty"),
    ("collections", "change_legalparty"),
    ("collections", "add_litigationseizure"),
    ("collections", "change_litigationseizure"),
    ("collections", "add_litigationcost"),
    ("collections", "change_litigationcost"),
)

_WRITE_LEGAL_CONTENTIEUX_ASSIST = (
    ("collections", "add_litigationfile"),
    ("collections", "change_litigationfile"),
    ("collections", "add_litigationevent"),
    ("collections", "add_legalparty"),
    ("collections", "change_legalparty"),
    ("collections", "add_litigationseizure"),
    ("collections", "add_litigationcost"),
)

_WRITE_COLLECTIONS_MGR = (
    ("collections", "add_repayment"),
    ("collections", "change_repayment"),
    ("collections", "add_collectioncase"),
    ("collections", "change_collectioncase"),
    ("collections", "delete_collectioncase"),
    ("collections", "add_collectionaction"),
    ("collections", "change_collectionaction"),
    ("collections", "add_paymentpromise"),
    ("collections", "change_paymentpromise"),
    ("collections", "delete_paymentpromise"),
    ("collections", "add_collectionescalationrule"),
    ("collections", "change_collectionescalationrule"),
    ("collections", "delete_collectionescalationrule"),
    ("collections", "add_litigationfile"),
    ("collections", "change_litigationfile"),
    ("collections", "add_litigationevent"),
    ("collections", "change_litigationevent"),
    ("collections", "add_legalparty"),
    ("collections", "change_legalparty"),
    ("collections", "add_litigationseizure"),
    ("collections", "change_litigationseizure"),
    ("collections", "add_litigationcost"),
    ("collections", "change_litigationcost"),
    ("collections", "add_loanrestructure"),
    ("collections", "change_loanrestructure"),
    ("collections", "add_writeoff"),
    ("collections", "change_writeoff"),
    # Issue fréquente d'un dossier de recouvrement ; suivi possible par juridique / exploitation.
    ("guarantees", "initiate_dationrequest"),
    ("guarantees", "initiate_guaranteeformalizationrequest"),
)

_WRITE_COLLECTIONS_ASSIST = (
    ("collections", "add_repayment"),
    ("collections", "add_collectioncase"),
    ("collections", "change_collectioncase"),
    ("collections", "add_collectionaction"),
    ("collections", "add_paymentpromise"),
    ("collections", "change_paymentpromise"),
    ("collections", "add_litigationfile"),
    ("collections", "change_litigationfile"),
    ("collections", "add_litigationevent"),
    ("collections", "add_legalparty"),
    ("collections", "change_legalparty"),
    ("collections", "add_litigationseizure"),
    ("collections", "change_litigationseizure"),
    ("collections", "add_litigationcost"),
    ("collections", "change_litigationcost"),
    ("guarantees", "initiate_dationrequest"),
    ("guarantees", "initiate_guaranteeformalizationrequest"),
)

_READ_METIER = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CATALOG,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    *_VIEW_WORKFLOW,
    *_VIEW_COLLECTIONS,
    *_VIEW_CBS,
    *_VIEW_TRANSVERSE,
)

_CHARGE_AFFAIRE_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CATALOG,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    *_VIEW_WORKFLOW,
    *_VIEW_TRANSVERSE,
    *_WRITE_INSTRUCTION,
)

_ANALYSTE_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CATALOG,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    *_VIEW_WORKFLOW,
    *_VIEW_TRANSVERSE,
    *_WRITE_ANALYSIS,
)

# Chef d'agence : même instruction que le CA + vision recouvrement agence.
_CHEF_AGENCE_PERMS = (
    *_CHARGE_AFFAIRE_PERMS,
    *_VIEW_COLLECTIONS,
)

_RESP_CREDIT_PERMS = (
    *_READ_METIER,
    *_WRITE_ANALYSIS,
)

_RESP_EXPLOITATION_PERMS = _READ_METIER

_RESP_RETAILS_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CATALOG,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    *_VIEW_WORKFLOW,
    *_VIEW_COLLECTIONS,
    *_VIEW_TRANSVERSE,
    ("clients", "change_client"),
    *_WRITE_ANALYSIS,
)

_COMMITTEE_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CATALOG,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    *_VIEW_WORKFLOW,
    *_VIEW_TRANSVERSE,
    *_WRITE_ANALYSIS,
)

_DG_PERMS = _READ_METIER

_RESP_OPERATIONS_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CATALOG,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    *_VIEW_WORKFLOW,
    *_VIEW_CBS,
    *_VIEW_TRANSVERSE,
    *_WRITE_OPERATIONS,
)

_ASSISTANT_OPERATIONS_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CATALOG,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    *_VIEW_WORKFLOW,
    *_VIEW_CBS,
    *_VIEW_TRANSVERSE,
    *_WRITE_OPS_ASSISTANT,
)

_RESP_JURIDIQUE_PERMS = (
    # Vue transverse type exploitation + recouvrement, écriture juridique / contentieux.
    *_READ_METIER,
    *_WRITE_LEGAL,
    *_WRITE_LEGAL_CONTENTIEUX,
)

_ASSISTANT_JURIDIQUE_PERMS = (
    *_READ_METIER,
    *_WRITE_LEGAL_ASSIST,
    *_WRITE_LEGAL_CONTENTIEUX_ASSIST,
)

_RESP_RECOUVREMENT_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_COLLECTIONS,
    *_VIEW_GUARANTEES,
    *_VIEW_DOCS,
    *_VIEW_WORKFLOW,
    *_VIEW_TRANSVERSE,
    *_WRITE_COLLECTIONS_MGR,
)

_ASSISTANT_RECOUVREMENT_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_COLLECTIONS,
    *_VIEW_GUARANTEES,
    *_VIEW_DOCS,
    *_VIEW_WORKFLOW,
    *_VIEW_TRANSVERSE,
    *_WRITE_COLLECTIONS_ASSIST,
)

_RESP_CONTROLE_PERMS = _READ_METIER
_ASSISTANT_CONTROLE_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CONTRACTS,
    *_VIEW_COLLECTIONS,
    *_VIEW_WORKFLOW,
    ("tenants", "view_agency"),
    ("audit", "view_auditlog"),
)

_RESP_AUDIT_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CONTRACTS,
    *_VIEW_COLLECTIONS,
    *_VIEW_CBS,
    *_VIEW_WORKFLOW,
    ("tenants", "view_agency"),
    ("audit", "view_auditlog"),
    ("notifications", "view_notificationlog"),
)

_ASSISTANT_AUDIT_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CONTRACTS,
    ("audit", "view_auditlog"),
    ("tenants", "view_agency"),
)

# Consultation seule : lecture métier, aucune écriture / décision / admin.
_LECTEUR_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_GUARANTEES,
    *_VIEW_CATALOG,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    *_VIEW_WORKFLOW,
    *_VIEW_COLLECTIONS,
    ("tenants", "view_agency"),
)

# Finance / comptabilité : encaissements, lecture prêts & clients.
_WRITE_COMPTA = (
    ("collections", "add_repayment"),
    ("collections", "change_repayment"),
)

_WRITE_COMPTA_CHEF = (
    *_WRITE_COMPTA,
    ("collections", "delete_repayment"),
    ("collections", "view_collectioncase"),
    ("collections", "view_collectionaction"),
    ("collections", "view_paymentpromise"),
)

_COMPTABLE_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_COLLECTIONS,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    ("tenants", "view_agency"),
    *_WRITE_COMPTA,
)

_CHEF_COMPTABLE_PERMS = (
    *_VIEW_CLIENTS,
    *_VIEW_CREDIT,
    *_VIEW_COLLECTIONS,
    *_VIEW_GUARANTEES,
    *_VIEW_DOCS,
    *_VIEW_CONTRACTS,
    *_VIEW_CBS,
    *_VIEW_TRANSVERSE,
    *_WRITE_COMPTA_CHEF,
)

# RAF / DAF : vision transverse + pilotage encaissements / recouvrement financier.
_RESP_ADMIN_FINANCIER_PERMS = (
    *_READ_METIER,
    *_WRITE_COLLECTIONS_MGR,
    ("audit", "view_auditlog"),
)

# Packs appliqués aux rôles métier bootstrap (hors admin filiale).
DEFAULT_ROLE_PACKS = {
    CHARGE_AFFAIRE_ROLE_NAME: _CHARGE_AFFAIRE_PERMS,
    CHEF_AGENCE_ROLE_NAME: _CHEF_AGENCE_PERMS,
    RESP_EXPLOITATION_ROLE_NAME: _RESP_EXPLOITATION_PERMS,
    RESP_CREDIT_RISQUE_ROLE_NAME: _RESP_CREDIT_PERMS,
    ANALYSTE_CREDIT_RISQUE_ROLE_NAME: _ANALYSTE_PERMS,
    CREDIT_COMMITTEE_ROLE_NAME: _COMMITTEE_PERMS,
    RESP_RETAILS_ROLE_NAME: _RESP_RETAILS_PERMS,
    DIRECTEUR_GENERAL_ROLE_NAME: _DG_PERMS,
    RESP_JURIDIQUE_ROLE_NAME: _RESP_JURIDIQUE_PERMS,
    ASSISTANT_JURIDIQUE_ROLE_NAME: _ASSISTANT_JURIDIQUE_PERMS,
    RESP_OPERATIONS_ROLE_NAME: _RESP_OPERATIONS_PERMS,
    ASSISTANT_OPERATIONS_ROLE_NAME: _ASSISTANT_OPERATIONS_PERMS,
    RESP_CONTROLE_INTERNE_ROLE_NAME: _RESP_CONTROLE_PERMS,
    ASSISTANT_CONTROLE_INTERNE_ROLE_NAME: _ASSISTANT_CONTROLE_PERMS,
    ASSISTANT_AUDIT_ROLE_NAME: _ASSISTANT_AUDIT_PERMS,
    RESP_AUDIT_ROLE_NAME: _RESP_AUDIT_PERMS,
    ASSISTANT_RECOUVREMENT_ROLE_NAME: _ASSISTANT_RECOUVREMENT_PERMS,
    RESP_RECOUVREMENT_ROLE_NAME: _RESP_RECOUVREMENT_PERMS,
    RESP_ADMIN_FINANCIER_ROLE_NAME: _RESP_ADMIN_FINANCIER_PERMS,
    CHEF_COMPTABLE_ROLE_NAME: _CHEF_COMPTABLE_PERMS,
    COMPTABLE_ROLE_NAME: _COMPTABLE_PERMS,
    LECTEUR_ROLE_NAME: _LECTEUR_PERMS,
}


def create_tenant_role(tenant, name, permissions=None):
    """Crée un rôle filiale et le groupe Django technique associé."""
    from .models import TenantRole

    internal_name = f"__ff_{tenant.id}__{uuid.uuid4().hex[:12]}"
    group = Group.objects.create(name=internal_name)
    if permissions:
        group.permissions.set(permissions)
    return TenantRole.objects.create(tenant=tenant, name=name, group=group)


def tenant_groups_queryset(tenant_id):
    """Groupes Django rattachés aux rôles d'une filiale."""
    from .models import TenantRole

    group_ids = TenantRole.objects.filter(tenant_id=tenant_id).values_list(
        "group_id", flat=True
    )
    return Group.objects.filter(id__in=group_ids)


def validate_groups_for_tenant(tenant_id, groups):
    """Vérifie que chaque groupe appartient à la filiale."""
    from .models import TenantRole

    allowed = set(
        TenantRole.objects.filter(tenant_id=tenant_id).values_list(
            "group_id", flat=True
        )
    )
    for group in groups:
        if group.id not in allowed:
            tr = getattr(group, "tenant_role", None)
            label = tr.name if tr else group.name
            raise ValueError(
                f"Le rôle « {label} » n'appartient pas à cette filiale."
            )


# SoD dur : paires de rôles métier incompatibles sur le même utilisateur.
SOD_INCOMPATIBLE_ROLE_PAIRS = (
    frozenset({CHARGE_AFFAIRE_ROLE_NAME, CREDIT_COMMITTEE_ROLE_NAME}),
    frozenset({ANALYSTE_CREDIT_RISQUE_ROLE_NAME, CREDIT_COMMITTEE_ROLE_NAME}),
    frozenset({CHARGE_AFFAIRE_ROLE_NAME, DIRECTEUR_GENERAL_ROLE_NAME}),
    frozenset({ANALYSTE_CREDIT_RISQUE_ROLE_NAME, DIRECTEUR_GENERAL_ROLE_NAME}),
    frozenset({RESP_OPERATIONS_ROLE_NAME, RESP_AUDIT_ROLE_NAME}),
    frozenset({ASSISTANT_OPERATIONS_ROLE_NAME, RESP_CONTROLE_INTERNE_ROLE_NAME}),
    frozenset({ASSISTANT_RECOUVREMENT_ROLE_NAME, RESP_AUDIT_ROLE_NAME}),
    frozenset({RESP_RECOUVREMENT_ROLE_NAME, RESP_AUDIT_ROLE_NAME}),
)


def validate_sod_role_assignment(groups):
    """
    Refuse les combinaisons de rôles qui violent la séparation des tâches.
    """
    from .models import TenantRole

    names = set()
    for group in groups:
        tr = getattr(group, "tenant_role", None)
        if tr is None:
            tr = TenantRole.objects.filter(group_id=group.id).first()
        if tr:
            names.add(tr.name)
    for pair in SOD_INCOMPATIBLE_ROLE_PAIRS:
        if pair.issubset(names):
            a, b = sorted(pair)
            raise ValueError(
                f"Séparation des tâches : les rôles « {a} » et « {b} » "
                f"sont incompatibles sur le même utilisateur."
            )


def get_or_create_tenant_role(tenant, name):
    """Retourne le groupe Django d'un rôle filiale (création si absent)."""
    from .models import TenantRole

    existing = TenantRole.objects.filter(tenant=tenant, name=name).first()
    if existing:
        return existing.group, False
    role = create_tenant_role(tenant, name)
    return role.group, True


def _dedupe_permissions(perms):
    seen = set()
    unique = []
    for p in perms:
        if p.id not in seen:
            seen.add(p.id)
            unique.append(p)
    return unique


def permissions_from_spec(spec):
    """Résout une liste (app_label, codename) en objets Permission."""
    perms = []
    for app_label, codename in spec:
        try:
            perms.append(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        except Permission.DoesNotExist:
            continue
    return _dedupe_permissions(perms)


def filiale_admin_permissions():
    """Ensemble des permissions Django pour un administrateur filiale."""
    perms = list(
        Permission.objects.filter(
            content_type__app_label__in=FILIALE_ADMIN_APP_LABELS
        )
    )
    perms.extend(permissions_from_spec(FILIALE_ADMIN_EXTRA_PERMS))
    return _dedupe_permissions(perms)


def ensure_filiale_admin_role(tenant):
    """
    Garantit le rôle « Administrateur filiale » avec le pack de permissions.
    Retourne le groupe Django associé.
    """
    group, _ = get_or_create_tenant_role(tenant, FILIALE_ADMIN_ROLE_NAME)
    group.permissions.set(filiale_admin_permissions())
    return group


def ensure_role_pack(tenant, role_name, spec):
    """Crée le rôle filiale si besoin et synchronise son pack de permissions."""
    group, _ = get_or_create_tenant_role(tenant, role_name)
    group.permissions.set(permissions_from_spec(spec))
    return group


def retire_legacy_bootstrap_roles(tenant):
    """
    Retire les anciens rôles bootstrap s'ils n'ont aucun utilisateur affecté.
    Les rôles encore utilisés sont conservés (réaffectation manuelle possible).
    """
    from .models import TenantRole

    for name in LEGACY_BOOTSTRAP_ROLE_NAMES:
        role = TenantRole.objects.filter(tenant=tenant, name=name).select_related(
            "group"
        ).first()
        if not role:
            continue
        if role.group.user_set.exists():
            continue
        group = role.group
        role.delete()
        group.delete()


def ensure_default_role_packs(tenant):
    """
    Synchronise les packs RBAC des rôles bootstrap d'une filiale.

    - Administrateur filiale : pack complet
    - Rôles métier bootstrap (dont finance / compta / Lecteur) : packs adaptés
    - Anciens rôles (Analyste crédit, Responsable agence) : retirés si inutilisés
    """
    ensure_filiale_admin_role(tenant)
    for role_name, spec in DEFAULT_ROLE_PACKS.items():
        ensure_role_pack(tenant, role_name, spec)
    retire_legacy_bootstrap_roles(tenant)
    from apps.collections.services import (
        ensure_default_escalation_rules,
        ensure_litigation_document_categories,
    )

    ensure_default_escalation_rules(tenant)
    ensure_litigation_document_categories(tenant)


@transaction.atomic
def provision_filiale_admin(
    *,
    tenant,
    username,
    agency=None,
    password=None,
    email="",
    first_name="",
    last_name="",
    phone="",
    employee_id="",
    cbs_id="",
    agency_ids=None,
    send_credentials=True,
    must_change_password=True,
):
    """
    Crée (ou met à jour) un administrateur de filiale :
    - rattachement tenant (agence optionnelle — périmètre toute la filiale)
    - data_scope = TENANT
    - is_staff = True (accès menus Administration)
    - rôle Administrateur filiale (toutes permissions métier)
    - mot de passe temporaire généré et envoyé par e-mail (sauf override)
    """
    from .models import DataScope, User
    from .password_services import (
        assign_password,
        issue_temporary_password,
        send_credentials_email,
    )

    if agency is not None and agency.tenant_id != tenant.id:
        raise ValueError("L'agence doit appartenir à la filiale.")
    if send_credentials and not (email or "").strip():
        raise ValueError(
            "L'adresse e-mail est obligatoire pour envoyer le mot de passe."
        )

    admin_group = ensure_filiale_admin_role(tenant)
    agencies = list(agency_ids or [])
    if agency is not None and agency not in agencies:
        agencies = [agency, *agencies]
    for ag in agencies:
        if ag.tenant_id != tenant.id:
            raise ValueError(
                "Toutes les agences doivent appartenir à la filiale."
            )

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "tenant": tenant,
            "agency": agency,
            "data_scope": DataScope.TENANT,
            "is_group_level": False,
            "is_staff": True,
            "is_active": True,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "employee_id": employee_id,
            "cbs_id": cbs_id,
            "must_change_password": must_change_password,
        },
    )
    email_sent = False
    if created:
        if password:
            assign_password(
                user,
                password,
                must_change_password=must_change_password,
            )
            if send_credentials:
                email_sent = send_credentials_email(
                    user, password, reason="created"
                )
        else:
            _, email_sent = issue_temporary_password(
                user, reason="created", send_email=send_credentials
            )
            if not must_change_password:
                user.must_change_password = False
                user.save(update_fields=["must_change_password"])
    else:
        # Réaffectation / élévation d'un compte existant
        if user.is_group_level:
            raise ValueError(
                "Impossible d'affecter un utilisateur Groupe comme admin filiale."
            )
        user.email = email or user.email
        user.tenant = tenant
        user.agency = agency
        user.data_scope = DataScope.TENANT
        user.is_staff = True
        user.is_active = True
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if phone:
            user.phone = phone
        if employee_id:
            user.employee_id = employee_id
        if cbs_id:
            user.cbs_id = cbs_id
        user.save()
        if password is not None:
            assign_password(
                user,
                password,
                must_change_password=must_change_password,
            )
        elif send_credentials:
            _, email_sent = issue_temporary_password(
                user, reason="reset", send_email=True
            )

    user.agencies.set(agencies)
    user.groups.add(admin_group)
    user._email_sent = email_sent  # noqa: SLF001
    return user, created

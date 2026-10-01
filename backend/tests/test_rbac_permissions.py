"""
Tests du système RBAC et des permissions.
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.services import (
    ensure_role_pack,
    check_sod_compliance,
    CHARGE_AFFAIRE_ROLE_NAME,
    CREDIT_COMMITTEE_FILIALE_ROLE_NAME,
    ADMINISTRATEUR_CREDIT_ROLE_NAME,
    ANALYSTE_CREDIT_RISQUE_ROLE_NAME,
    DEFAULT_ROLE_PACKS,
    SOD_INCOMPATIBLE_ROLE_PAIRS,
)
from apps.tenants.models import Tenant

User = get_user_model()


@pytest.fixture
def tenant(db):
    """Créer une filiale de test."""
    return Tenant.objects.create(
        name="Test Filiale",
        code="TEST",
        currency="XOF",
    )


@pytest.fixture
def user(tenant):
    """Créer un utilisateur de base."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        tenant=tenant,
    )


@pytest.mark.django_db
class TestRolePackCreation:
    """Tests de création des packs de rôles."""
    
    def test_create_role_pack_with_permissions(self, tenant):
        """Un pack de rôles doit créer un groupe avec ses permissions."""
        role_name = CHARGE_AFFAIRE_ROLE_NAME
        role_spec = DEFAULT_ROLE_PACKS[role_name]
        
        ensure_role_pack(tenant, role_name, role_spec)
        
        # Vérifier que le groupe existe
        group = Group.objects.get(name=role_name)
        assert group is not None
        
        # Vérifier que des permissions ont été ajoutées
        perms_count = group.permissions.count()
        assert perms_count > 0
    
    def test_role_pack_idempotent(self, tenant):
        """La création d'un pack doit être idempotente."""
        role_name = CHARGE_AFFAIRE_ROLE_NAME
        role_spec = DEFAULT_ROLE_PACKS[role_name]
        
        # Créer une première fois
        ensure_role_pack(tenant, role_name, role_spec)
        group1 = Group.objects.get(name=role_name)
        perms1 = set(group1.permissions.all())
        
        # Recréer
        ensure_role_pack(tenant, role_name, role_spec)
        group2 = Group.objects.get(name=role_name)
        perms2 = set(group2.permissions.all())
        
        # Les groupes doivent être identiques
        assert group1.id == group2.id
        assert perms1 == perms2


@pytest.mark.django_db
class TestSeparationOfDuties:
    """Tests de la séparation des devoirs (SoD)."""
    
    def test_sod_check_passes_with_compatible_roles(self, tenant, user):
        """Des rôles compatibles doivent passer la vérification SoD."""
        # Créer des rôles compatibles
        role_charge = Group.objects.create(name=CHARGE_AFFAIRE_ROLE_NAME)
        role_analyste = Group.objects.create(name=ANALYSTE_CREDIT_RISQUE_ROLE_NAME)
        
        user.groups.set([role_charge, role_analyste])
        
        # Ne doit pas lever d'erreur
        check_sod_compliance(user)
    
    def test_sod_check_fails_with_incompatible_roles(self, tenant, user):
        """Des rôles incompatibles doivent échouer la vérification SoD."""
        # Charge d'affaire + Comité de crédit = incompatible
        role_charge = Group.objects.create(name=CHARGE_AFFAIRE_ROLE_NAME)
        role_comite = Group.objects.create(name=CREDIT_COMMITTEE_FILIALE_ROLE_NAME)
        
        user.groups.set([role_charge, role_comite])
        
        # Doit lever une erreur
        with pytest.raises(ValueError, match="conflit d'intérêts"):
            check_sod_compliance(user)
    
    def test_sod_admin_credit_incompatible_with_charge_affaire(self, tenant, user):
        """Admin crédit et chargé d'affaire sont incompatibles."""
        role_admin = Group.objects.create(name=ADMINISTRATEUR_CREDIT_ROLE_NAME)
        role_charge = Group.objects.create(name=CHARGE_AFFAIRE_ROLE_NAME)
        
        user.groups.set([role_admin, role_charge])
        
        with pytest.raises(ValueError):
            check_sod_compliance(user)
    
    def test_sod_all_incompatible_pairs_defined(self):
        """Vérifier que les paires incompatibles sont bien définies."""
        assert len(SOD_INCOMPATIBLE_ROLE_PAIRS) >= 5
        
        # Vérifier quelques paires critiques
        pairs_list = [frozenset(p) for p in SOD_INCOMPATIBLE_ROLE_PAIRS]
        
        assert frozenset({
            CHARGE_AFFAIRE_ROLE_NAME,
            CREDIT_COMMITTEE_FILIALE_ROLE_NAME
        }) in pairs_list


@pytest.mark.django_db
class TestUserPermissions:
    """Tests des permissions utilisateur."""
    
    def test_user_inherits_group_permissions(self, tenant, user):
        """Un utilisateur doit hériter des permissions de ses groupes."""
        # Créer un rôle avec permissions
        role_name = CHARGE_AFFAIRE_ROLE_NAME
        role_spec = DEFAULT_ROLE_PACKS[role_name]
        ensure_role_pack(tenant, role_name, role_spec)
        
        group = Group.objects.get(name=role_name)
        user.groups.add(group)
        
        # Vérifier que l'utilisateur a bien des permissions
        user_perms = user.get_all_permissions()
        assert len(user_perms) > 0
    
    def test_user_has_credit_view_permission(self, tenant, user):
        """Un chargé d'affaire doit pouvoir voir les crédits."""
        role_name = CHARGE_AFFAIRE_ROLE_NAME
        role_spec = DEFAULT_ROLE_PACKS[role_name]
        ensure_role_pack(tenant, role_name, role_spec)
        
        group = Group.objects.get(name=role_name)
        user.groups.add(group)
        
        assert user.has_perm("credits.view_creditapplication")
    
    def test_user_can_add_client(self, tenant, user):
        """Un chargé d'affaire doit pouvoir créer des clients."""
        role_name = CHARGE_AFFAIRE_ROLE_NAME
        role_spec = DEFAULT_ROLE_PACKS[role_name]
        ensure_role_pack(tenant, role_name, role_spec)
        
        group = Group.objects.get(name=role_name)
        user.groups.add(group)
        
        assert user.has_perm("clients.add_client")


@pytest.mark.django_db
class TestDataScope:
    """Tests du périmètre de données (OWN/AGENCY/TENANT)."""
    
    def test_user_default_data_scope_is_agency(self, tenant, user):
        """Le périmètre par défaut doit être AGENCY."""
        assert user.data_scope == "AGENCY"
    
    def test_user_can_have_own_scope(self, tenant):
        """Un utilisateur peut avoir un périmètre OWN."""
        user = User.objects.create_user(
            username="ownscope",
            email="own@example.com",
            password="test123",
            tenant=tenant,
            data_scope="OWN",
        )
        assert user.data_scope == "OWN"
    
    def test_user_can_have_tenant_scope(self, tenant):
        """Un utilisateur peut avoir un périmètre TENANT."""
        user = User.objects.create_user(
            username="tenantscope",
            email="tenant@example.com",
            password="test123",
            tenant=tenant,
            data_scope="TENANT",
        )
        assert user.data_scope == "TENANT"


@pytest.mark.django_db
class TestGroupLevelUsers:
    """Tests des utilisateurs niveau Groupe."""
    
    def test_group_level_user_has_no_tenant(self, db):
        """Un utilisateur Groupe ne doit pas avoir de filiale."""
        user = User.objects.create_user(
            username="groupuser",
            email="group@example.com",
            password="test123",
            is_group_level=True,
            tenant=None,
        )
        assert user.is_group_level is True
        assert user.tenant is None
    
    def test_superuser_is_group_level(self, db):
        """Un superuser doit être créé en is_group_level."""
        user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123",
        )
        assert user.is_group_level is True
        assert user.tenant is None


@pytest.mark.django_db
class TestMFASettings:
    """Tests des paramètres MFA."""
    
    def test_user_mfa_disabled_by_default(self, tenant, user):
        """Le MFA doit être désactivé par défaut."""
        assert user.mfa_enabled is False
        assert user.mfa_secret == ""
    
    def test_user_can_enable_mfa(self, tenant, user):
        """Un utilisateur peut activer le MFA."""
        user.mfa_enabled = True
        user.mfa_secret = "TESTSECRET123456"
        user.save()
        
        user.refresh_from_db()
        assert user.mfa_enabled is True
        assert user.mfa_secret == "TESTSECRET123456"

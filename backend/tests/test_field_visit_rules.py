"""
Tests des règles de visites terrain conditionnelles.
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model

from apps.credits.models import CreditApplication, FieldVisitRule
from apps.clients.models import Client
from apps.tenants.models import Tenant
from apps.catalog.models import CreditProduct

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
def product(tenant):
    """Créer un produit de crédit."""
    return CreditProduct.objects.create(
        tenant=tenant,
        name="Crédit Standard",
        code="STANDARD",
        client_type="ALL",
        is_active=True,
    )


@pytest.fixture
def client_individual_independent(tenant):
    """Client particulier indépendant."""
    return Client.objects.create(
        tenant=tenant,
        client_type="INDIVIDUAL",
        individual_profile="INDEPENDANT",
        first_name="Jean",
        last_name="Dupont",
    )


@pytest.fixture
def client_individual_salaried(tenant):
    """Client particulier salarié."""
    return Client.objects.create(
        tenant=tenant,
        client_type="INDIVIDUAL",
        individual_profile="SALARIE",
        first_name="Marie",
        last_name="Martin",
    )


@pytest.mark.django_db
class TestFieldVisitRuleMatching:
    """Tests de matching des règles de visites terrain."""
    
    def test_rule_matches_client_type(self, tenant, client_individual_independent, product):
        """Une règle sur le type de client doit matcher correctement."""
        rule = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Visite particuliers",
            client_type="INDIVIDUAL",
            required_role="CHARGE_COMPTE",
        )
        
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client_individual_independent,
            product=product,
            requested_amount=Decimal("100000"),
        )
        
        assert rule.matches(application) is True
    
    def test_rule_matches_individual_profile(self, tenant, client_individual_independent, product):
        """Une règle sur le profil particulier doit matcher."""
        rule = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Visite indépendants",
            client_type="INDIVIDUAL",
            individual_profile="INDEPENDANT",
            required_role="CHARGE_COMPTE",
        )
        
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client_individual_independent,
            product=product,
            requested_amount=Decimal("100000"),
        )
        
        assert rule.matches(application) is True
    
    def test_rule_does_not_match_wrong_profile(
        self, tenant, client_individual_salaried, product
    ):
        """Une règle avec mauvais profil ne doit pas matcher."""
        rule = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Visite indépendants",
            client_type="INDIVIDUAL",
            individual_profile="INDEPENDANT",
            required_role="CHARGE_COMPTE",
        )
        
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client_individual_salaried,
            product=product,
            requested_amount=Decimal("100000"),
        )
        
        assert rule.matches(application) is False
    
    def test_rule_matches_amount_range(self, tenant, client_individual_independent, product):
        """Une règle sur une tranche de montant doit matcher."""
        rule = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Visite 0-100K",
            amount_min=Decimal("0"),
            amount_max=Decimal("100000"),
            required_role="CHARGE_COMPTE",
        )
        
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client_individual_independent,
            product=product,
            requested_amount=Decimal("50000"),
        )
        
        assert rule.matches(application) is True
    
    def test_rule_does_not_match_amount_too_high(
        self, tenant, client_individual_independent, product
    ):
        """Une règle ne doit pas matcher si montant trop élevé."""
        rule = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Visite 0-100K",
            amount_min=Decimal("0"),
            amount_max=Decimal("100000"),
            required_role="CHARGE_COMPTE",
        )
        
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client_individual_independent,
            product=product,
            requested_amount=Decimal("150000"),
        )
        
        assert rule.matches(application) is False
    
    def test_rule_matches_complex_condition(
        self, tenant, client_individual_independent, product
    ):
        """Une règle avec plusieurs conditions doit toutes les vérifier."""
        rule = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Visite indépendants 50-200K",
            client_type="INDIVIDUAL",
            individual_profile="INDEPENDANT",
            amount_min=Decimal("50000"),
            amount_max=Decimal("200000"),
            required_role="CHARGE_COMPTE",
        )
        
        # Doit matcher
        application1 = CreditApplication.objects.create(
            tenant=tenant,
            client=client_individual_independent,
            product=product,
            requested_amount=Decimal("100000"),
        )
        assert rule.matches(application1) is True
        
        # Ne doit pas matcher (montant trop faible)
        application2 = CreditApplication.objects.create(
            tenant=tenant,
            client=client_individual_independent,
            product=product,
            requested_amount=Decimal("30000"),
        )
        assert rule.matches(application2) is False
    
    def test_inactive_rule_is_ignored(self, tenant, client_individual_independent, product):
        """Une règle inactive ne doit pas être appliquée."""
        rule = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Visite désactivée",
            client_type="INDIVIDUAL",
            required_role="CHARGE_COMPTE",
            is_active=False,
        )
        
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client_individual_independent,
            product=product,
            requested_amount=Decimal("100000"),
        )
        
        # La règle match mais est inactive
        assert rule.matches(application) is True
        assert rule.is_active is False


@pytest.mark.django_db
class TestFieldVisitRulePriority:
    """Tests de la priorité des règles."""
    
    def test_rules_ordered_by_priority(self, tenant):
        """Les règles doivent être triées par priorité décroissante."""
        rule1 = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Priorité basse",
            priority=1,
            required_role="CHARGE_COMPTE",
        )
        rule2 = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Priorité haute",
            priority=10,
            required_role="RESP_EXPLOITATION",
        )
        rule3 = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Priorité moyenne",
            priority=5,
            required_role="CHEF_AGENCE",
        )
        
        rules = list(FieldVisitRule.objects.filter(tenant=tenant))
        
        # Ordre attendu: priority DESC, puis id
        assert rules[0] == rule2  # priority=10
        assert rules[1] == rule3  # priority=5
        assert rules[2] == rule1  # priority=1


@pytest.mark.django_db
class TestFieldVisitRuleBlockingStage:
    """Tests des étapes de blocage."""
    
    def test_blocking_stages(self, tenant):
        """Vérifier les différentes étapes de blocage."""
        rule_submit = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Blocage à la soumission",
            blocking_stage=FieldVisitRule.BlockingStage.SUBMIT,
            required_role="CHARGE_COMPTE",
        )
        
        rule_opinion = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Blocage à l'avis",
            blocking_stage=FieldVisitRule.BlockingStage.OPINION,
            required_role="ANALYSTE_CREDIT",
        )
        
        rule_approval = FieldVisitRule.objects.create(
            tenant=tenant,
            name="Blocage à l'approbation",
            blocking_stage=FieldVisitRule.BlockingStage.APPROVAL,
            required_role="COMITE_CREDIT",
        )
        
        assert rule_submit.blocking_stage == "SUBMIT"
        assert rule_opinion.blocking_stage == "OPINION"
        assert rule_approval.blocking_stage == "APPROVAL"

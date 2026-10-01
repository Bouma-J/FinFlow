"""
Tests de sélection et application des circuits de workflow.
"""
import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.workflow.models import WorkflowDefinition, ApprovalStep
from apps.workflow.services import select_best_workflow, WorkflowError
from apps.credits.models import CreditApplication
from apps.clients.models import Client
from apps.tenants.models import Tenant, Agency
from apps.catalog.models import CreditProduct, ProductCategory

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
def agency(tenant):
    """Créer une agence."""
    return Agency.objects.create(
        tenant=tenant,
        name="Agence Test",
        code="AG001",
    )


@pytest.fixture
def category(tenant):
    """Créer une famille de produits."""
    return ProductCategory.objects.create(
        tenant=tenant,
        name="Crédit Immobilier",
        code="IMMOBILIER",
    )


@pytest.fixture
def product(tenant, category):
    """Créer un produit de crédit."""
    return CreditProduct.objects.create(
        tenant=tenant,
        category=category,
        name="Crédit Habitat",
        code="HABITAT",
        client_type="ALL",
        is_active=True,
    )


@pytest.fixture
def client(tenant):
    """Créer un client."""
    return Client.objects.create(
        tenant=tenant,
        client_type="INDIVIDUAL",
        first_name="Jean",
        last_name="Dupont",
    )


@pytest.fixture
def workflow_generic(tenant):
    """Circuit générique (pas de filtre)."""
    return WorkflowDefinition.objects.create(
        tenant=tenant,
        code="GENERIC",
        name="Circuit générique",
        version=1,
        is_active=True,
    )


@pytest.fixture
def workflow_high_amount(tenant):
    """Circuit pour montants élevés (> 1M)."""
    return WorkflowDefinition.objects.create(
        tenant=tenant,
        code="HIGH",
        name="Circuit montants élevés",
        version=1,
        is_active=True,
        min_amount=Decimal("1000000"),
    )


@pytest.fixture
def workflow_low_amount(tenant):
    """Circuit pour petits montants (< 500K)."""
    return WorkflowDefinition.objects.create(
        tenant=tenant,
        code="LOW",
        name="Circuit petits montants",
        version=1,
        is_active=True,
        max_amount=Decimal("500000"),
    )


@pytest.fixture
def workflow_product_specific(tenant, product):
    """Circuit spécifique à un produit."""
    workflow = WorkflowDefinition.objects.create(
        tenant=tenant,
        code="PRODUCT_SPECIFIC",
        name="Circuit produit spécifique",
        version=1,
        is_active=True,
        product=product,
    )
    return workflow


@pytest.mark.django_db
class TestWorkflowSelection:
    """Tests de sélection du meilleur circuit."""
    
    def test_select_generic_workflow_when_no_specific(
        self, tenant, workflow_generic, product, client
    ):
        """Doit sélectionner le circuit générique si pas de circuit spécifique."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("750000"),
        )
        
        selected = select_best_workflow(application)
        assert selected == workflow_generic
    
    def test_select_high_amount_workflow(
        self, tenant, workflow_generic, workflow_high_amount, product, client
    ):
        """Doit sélectionner le circuit pour montants élevés."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("2000000"),
        )
        
        selected = select_best_workflow(application)
        assert selected == workflow_high_amount
    
    def test_select_low_amount_workflow(
        self, tenant, workflow_generic, workflow_low_amount, product, client
    ):
        """Doit sélectionner le circuit pour petits montants."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("300000"),
        )
        
        selected = select_best_workflow(application)
        assert selected == workflow_low_amount
    
    def test_select_product_specific_workflow(
        self, tenant, workflow_generic, workflow_product_specific, product, client
    ):
        """Doit sélectionner le circuit spécifique au produit."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("750000"),
        )
        
        selected = select_best_workflow(application)
        assert selected == workflow_product_specific
    
    def test_no_workflow_available_raises_error(self, tenant, product, client):
        """Doit lever une erreur si aucun circuit disponible."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("750000"),
        )
        
        with pytest.raises(WorkflowError, match="Aucun circuit"):
            select_best_workflow(application)
    
    def test_inactive_workflow_is_ignored(
        self, tenant, product, client
    ):
        """Un circuit inactif ne doit pas être sélectionné."""
        WorkflowDefinition.objects.create(
            tenant=tenant,
            code="INACTIVE",
            name="Circuit inactif",
            version=1,
            is_active=False,
        )
        
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("750000"),
        )
        
        with pytest.raises(WorkflowError):
            select_best_workflow(application)


@pytest.mark.django_db
class TestWorkflowSpecificity:
    """Tests du scoring de spécificité."""
    
    def test_product_specific_more_specific_than_amount(
        self, tenant, workflow_high_amount, workflow_product_specific, product, client
    ):
        """Circuit produit spécifique est plus spécifique que montant seul."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("2000000"),
        )
        
        # Les deux circuits matchent, mais le produit spécifique gagne
        selected = select_best_workflow(application)
        assert selected == workflow_product_specific
    
    def test_specificity_score_calculation(self, tenant):
        """Vérifier le calcul du score de spécificité."""
        # Circuit générique : score = 0
        wf_generic = WorkflowDefinition.objects.create(
            tenant=tenant,
            code="GENERIC",
            name="Générique",
            version=1,
            is_active=True,
        )
        assert wf_generic.specificity_score() == 0
        
        # Circuit avec montant : score > 0
        wf_amount = WorkflowDefinition.objects.create(
            tenant=tenant,
            code="AMOUNT",
            name="Avec montant",
            version=1,
            is_active=True,
            min_amount=Decimal("1000000"),
        )
        assert wf_amount.specificity_score() > 0


@pytest.mark.django_db
class TestApprovalStepOrder:
    """Tests de l'ordre des étapes d'approbation."""
    
    def test_approval_steps_ordered_by_order_field(self, tenant):
        """Les étapes doivent être triées par order."""
        workflow = WorkflowDefinition.objects.create(
            tenant=tenant,
            code="TEST",
            name="Test",
            version=1,
            is_active=True,
        )
        
        group1 = Group.objects.create(name="Niveau 1")
        group2 = Group.objects.create(name="Niveau 2")
        group3 = Group.objects.create(name="Niveau 3")
        
        step1 = ApprovalStep.objects.create(
            workflow=workflow,
            name="Première étape",
            order=1,
            required_group=group1,
        )
        step2 = ApprovalStep.objects.create(
            workflow=workflow,
            name="Deuxième étape",
            order=2,
            required_group=group2,
        )
        step3 = ApprovalStep.objects.create(
            workflow=workflow,
            name="Troisième étape",
            order=3,
            required_group=group3,
        )
        
        steps = list(workflow.steps.all())
        assert steps[0] == step1
        assert steps[1] == step2
        assert steps[2] == step3


@pytest.mark.django_db
class TestApprovalStepKind:
    """Tests des types d'étapes (consultative vs décisionnelle)."""
    
    def test_consultative_vs_decisional_steps(self, tenant):
        """Vérifier les types d'étapes."""
        workflow = WorkflowDefinition.objects.create(
            tenant=tenant,
            code="TEST",
            name="Test",
            version=1,
            is_active=True,
        )
        
        group_opinion = Group.objects.create(name="Opinion")
        group_decision = Group.objects.create(name="Décision")
        
        step_opinion = ApprovalStep.objects.create(
            workflow=workflow,
            name="Avis technique",
            order=1,
            required_group=group_opinion,
            step_kind=ApprovalStep.StepKind.CONSULTATIVE,
        )
        
        step_decision = ApprovalStep.objects.create(
            workflow=workflow,
            name="Décision finale",
            order=2,
            required_group=group_decision,
            step_kind=ApprovalStep.StepKind.DECISIONAL,
        )
        
        assert step_opinion.step_kind == "CONSULTATIVE"
        assert step_decision.step_kind == "DECISIONAL"
        
        # Vérifier qu'on peut interroger le type
        assert step_opinion.is_consultative is True
        assert step_decision.is_decisional is True

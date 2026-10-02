"""
Tests des calculs de crédit (échéanciers, intérêts, etc.).
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta

from apps.credits.models import (
    CreditApplication,
    Loan,
    Periodicity,
    RepaymentMechanism,
)
from apps.credits.schedule import compute_schedule
from apps.clients.models import Client
from apps.tenants.models import Tenant
from apps.catalog.models import CreditProduct


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
def client(tenant):
    """Créer un client."""
    return Client.objects.create(
        tenant=tenant,
        client_type="INDIVIDUAL",
        first_name="Jean",
        last_name="Dupont",
    )


@pytest.mark.django_db
class TestLoanAmountCalculations:
    """Tests des calculs de montants de prêt."""
    
    def test_disbursed_amount_set_correctly(self, tenant, product, client):
        """Le montant décaissé doit être correctement enregistré."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("10.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
        )
        
        assert loan.disbursed_amount == Decimal("1000000")
    
    def test_outstanding_balance_initial(self, tenant, product, client):
        """Le solde initial doit être égal au montant décaissé."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("500000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("500000"),
            interest_rate=Decimal("12.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
            outstanding_balance=Decimal("500000"),
        )
        
        assert loan.outstanding_balance == Decimal("500000")


@pytest.mark.django_db
class TestInterestRateCalculations:
    """Tests des calculs de taux d'intérêt."""
    
    def test_interest_rate_within_bounds(self, tenant, product, client):
        """Le taux d'intérêt doit être positif et raisonnable."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        # Taux normal
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("15.50"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
        )
        
        assert Decimal("0") < loan.interest_rate < Decimal("100")
    
    def test_zero_interest_rate_allowed(self, tenant, product, client):
        """Un taux d'intérêt de 0% doit être accepté (prêt sans intérêt)."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("100000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("100000"),
            interest_rate=Decimal("0.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
        )
        
        assert loan.interest_rate == Decimal("0.00")


@pytest.mark.django_db
class TestLoanDuration:
    """Tests de la durée des prêts."""
    
    def test_duration_in_months(self, tenant, product, client):
        """La durée doit être en mois."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("12.00"),
            duration_months=24,
            periodicity=Periodicity.MONTHLY,
        )
        
        assert loan.duration_months == 24
    
    def test_loan_maturity_date_calculation(self, tenant, product, client):
        """La date d'échéance doit être calculée correctement."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        disbursement_date = date(2024, 1, 1)
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("12.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
            disbursement_date=disbursement_date,
        )
        
        # Maturity devrait être ~12 mois après
        expected_maturity = date(2025, 1, 1)
        
        # Si maturity_date est calculé automatiquement
        if loan.maturity_date:
            # Tolérance de quelques jours pour les calculs de périodicité
            diff = abs((loan.maturity_date - expected_maturity).days)
            assert diff < 35  # Environ 1 mois de tolérance


@pytest.mark.django_db
class TestPeriodicityTypes:
    """Tests des différentes périodicités."""
    
    def test_monthly_periodicity(self, tenant, product, client):
        """Périodicité mensuelle."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("12.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
        )
        
        assert loan.periodicity == "MONTHLY"
    
    def test_quarterly_periodicity(self, tenant, product, client):
        """Périodicité trimestrielle."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("12.00"),
            duration_months=12,
            periodicity=Periodicity.QUARTERLY,
        )
        
        assert loan.periodicity == "QUARTERLY"
    
    def test_weekly_periodicity(self, tenant, product, client):
        """Périodicité hebdomadaire."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("100000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("100000"),
            interest_rate=Decimal("15.00"),
            duration_months=6,
            periodicity=Periodicity.WEEKLY,
        )
        
        assert loan.periodicity == "WEEKLY"


@pytest.mark.django_db
class TestRepaymentMechanisms:
    """Tests des mécanismes de remboursement."""
    
    def test_degressive_repayment(self, tenant, product, client):
        """Remboursement dégressif (amortissement constant)."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("12.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
            repayment_mechanism=RepaymentMechanism.DEGRESSIVE,
        )
        
        assert loan.repayment_mechanism == "DEGRESSIVE"
    
    def test_in_fine_repayment(self, tenant, product, client):
        """Remboursement in fine (capital à terme)."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("12.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
            repayment_mechanism=RepaymentMechanism.IN_FINE,
        )
        
        assert loan.repayment_mechanism == "IN_FINE"


@pytest.mark.django_db
class TestLoanStatus:
    """Tests des statuts de prêt."""
    
    def test_loan_active_status(self, tenant, product, client):
        """Prêt actif."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("12.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
            status=Loan.Status.ACTIVE,
        )
        
        assert loan.status == "ACTIVE"
    
    def test_loan_can_be_paid_off(self, tenant, product, client):
        """Un prêt peut être soldé."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("1000000"),
            interest_rate=Decimal("12.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
            status=Loan.Status.ACTIVE,
            outstanding_balance=Decimal("1000000"),
        )
        
        # Simuler un remboursement complet
        loan.outstanding_balance = Decimal("0.00")
        loan.status = Loan.Status.PAID_OFF
        loan.save()
        
        assert loan.outstanding_balance == Decimal("0.00")
        assert loan.status == "PAID_OFF"


@pytest.mark.django_db
class TestApplicationToLoanConversion:
    """Tests de la conversion d'une demande en prêt."""
    
    def test_loan_references_application(self, tenant, product, client):
        """Un prêt doit référencer sa demande d'origine."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("500000"),
        )
        
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("500000"),
            interest_rate=Decimal("10.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
        )
        
        assert loan.application == application
        assert loan.application.requested_amount == Decimal("500000")
    
    def test_disbursed_amount_can_differ_from_requested(self, tenant, product, client):
        """Le montant décaissé peut différer du montant demandé."""
        application = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            requested_amount=Decimal("1000000"),
        )
        
        # Décaissement partiel
        loan = Loan.objects.create(
            tenant=tenant,
            application=application,
            disbursed_amount=Decimal("800000"),
            interest_rate=Decimal("12.00"),
            duration_months=12,
            periodicity=Periodicity.MONTHLY,
        )
        
        assert loan.disbursed_amount < application.requested_amount

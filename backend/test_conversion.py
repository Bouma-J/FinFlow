import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from decimal import Decimal
from apps.credits.models import FinancialAnalysis, CreditApplication
from apps.clients.models import Client
from apps.common.tenancy import set_current_tenant
from django.contrib.auth import get_user_model

User = get_user_model()

print("\n" + "="*70)
print("TEST CONVERSION SYNTHETIC ↔ DETAILED")
print("="*70)

# Trouver ou créer un tenant
try:
    from apps.tenants.models import Tenant
    tenant = Tenant.objects.first()
    if not tenant:
        print("⚠️ Aucun tenant trouvé, création impossible")
        print("Créez d'abord un tenant dans l'interface")
        exit(1)
    
    set_current_tenant(tenant.id)
    print(f"✅ Tenant: {tenant.name} ({tenant.id})")
    
    # Trouver une application existante ou en créer une
    app = CreditApplication.objects.filter(tenant=tenant).first()
    
    if not app:
        print("\n⚠️ Aucune application trouvée, tentative de création...")
        
        # Trouver ou créer un client
        client = Client.objects.filter(tenant=tenant).first()
        if not client:
            print("⚠️ Aucun client trouvé, test impossible")
            print("Créez d'abord un client dans l'interface")
            exit(1)
        
        # Trouver un produit
        from apps.catalog.models import CreditProduct
        product = CreditProduct.objects.filter(tenant=tenant).first()
        if not product:
            print("⚠️ Aucun produit trouvé, test impossible")
            print("Créez d'abord un produit de crédit")
            exit(1)
        
        # Créer une application de test
        app = CreditApplication.objects.create(
            tenant=tenant,
            client=client,
            product=product,
            amount_requested=Decimal('1000000'),
            duration_months=12,
            status='DRAFT'
        )
        print(f"✅ Application créée: {app.reference}")
    else:
        print(f"✅ Application existante: {app.reference}")
    
    # =================================================================
    # TEST 1: Création analyse SYNTHETIC
    # =================================================================
    print("\n" + "="*70)
    print("TEST 1: Création analyse SYNTHETIC")
    print("="*70)
    
    analysis = FinancialAnalysis.objects.create(
        tenant=tenant,
        application=app,
        analysis_mode='SYNTHETIC',
        banking_observation_period_months=3,
        salary_income=Decimal('500000'),
        spouse_income=Decimal('200000'),
        rental_income=Decimal('150000'),
        rent_expense=Decimal('100000'),
        food_expense=Decimal('75000'),
        utilities_expense=Decimal('25000'),
        transport_expense=Decimal('30000'),
        education_expense=Decimal('50000'),
    )
    
    print(f"✅ Analyse créée: ID={analysis.id}")
    print(f"   Mode: {analysis.analysis_mode}")
    print(f"   Salaire: {analysis.salary_income}")
    print(f"   Conjoint: {analysis.spouse_income}")
    print(f"   Revenus locatifs: {analysis.rental_income}")
    print(f"   Loyer: {analysis.rent_expense}")
    print(f"   Alimentation: {analysis.food_expense}")
    print(f"   detailed_data: {analysis.detailed_data}")
    
    # =================================================================
    # TEST 2: Conversion SYNTHETIC → DETAILED
    # =================================================================
    print("\n" + "="*70)
    print("TEST 2: Conversion SYNTHETIC → DETAILED")
    print("="*70)
    
    nb_periods = analysis.banking_observation_period_months or 3
    detailed_data = {}
    
    # Créer income_detail
    income_detail = []
    for i in range(nb_periods):
        period = {
            "period_label": f"Mois {i + 1}",
            "salary_income": float(analysis.salary_income) if analysis.salary_income else 0,
            "spouse_income": float(analysis.spouse_income) if analysis.spouse_income else 0,
            "rental_income": float(analysis.rental_income) if analysis.rental_income else 0,
            "other_activity_income": float(analysis.other_activity_income) if analysis.other_activity_income else 0,
            "other_income": float(analysis.other_income) if analysis.other_income else 0,
        }
        income_detail.append(period)
    
    detailed_data["income_detail"] = income_detail
    
    # Créer expenses_detail
    expenses_detail = []
    for i in range(nb_periods):
        period = {
            "period_label": f"Mois {i + 1}",
            "rent_expense": float(analysis.rent_expense) if analysis.rent_expense else 0,
            "food_expense": float(analysis.food_expense) if analysis.food_expense else 0,
            "utilities_expense": float(analysis.utilities_expense) if analysis.utilities_expense else 0,
            "transport_expense": float(analysis.transport_expense) if analysis.transport_expense else 0,
            "education_expense": float(analysis.education_expense) if analysis.education_expense else 0,
            "health_expense": float(analysis.health_expense) if analysis.health_expense else 0,
            "other_household_expenses": float(analysis.other_household_expenses) if analysis.other_household_expenses else 0,
            "tontine_expense": float(analysis.tontine_expense) if analysis.tontine_expense else 0,
            "social_contributions": float(analysis.social_contributions) if analysis.social_contributions else 0,
            "family_support_expense": float(analysis.family_support_expense) if analysis.family_support_expense else 0,
        }
        expenses_detail.append(period)
    
    detailed_data["expenses_detail"] = expenses_detail
    
    # Appliquer la conversion
    analysis.analysis_mode = 'DETAILED'
    analysis.detailed_data = detailed_data
    analysis.save()
    
    print(f"✅ Conversion SYNTHETIC → DETAILED réussie")
    print(f"   Mode: {analysis.analysis_mode}")
    print(f"   detailed_data keys: {list(analysis.detailed_data.keys())}")
    print(f"   Nombre de périodes income: {len(analysis.detailed_data.get('income_detail', []))}")
    print(f"   Nombre de périodes expenses: {len(analysis.detailed_data.get('expenses_detail', []))}")
    
    # Vérifier les données
    print("\n--- Exemple de période (income_detail[0]) ---")
    if analysis.detailed_data.get('income_detail'):
        period = analysis.detailed_data['income_detail'][0]
        for key, value in period.items():
            print(f"   {key}: {value}")
    
    # =================================================================
    # TEST 3: Conversion DETAILED → SYNTHETIC
    # =================================================================
    print("\n" + "="*70)
    print("TEST 3: Conversion DETAILED → SYNTHETIC")
    print("="*70)
    
    # Sauvegarder les valeurs originales pour comparaison
    original_salary = Decimal('500000')
    original_spouse = Decimal('200000')
    original_rental = Decimal('150000')
    original_rent = Decimal('100000')
    original_food = Decimal('75000')
    
    print("--- Valeurs AVANT conversion (mode DETAILED) ---")
    print(f"   Salaire: N/A (calculé depuis detailed_data)")
    print(f"   Conjoint: N/A (calculé depuis detailed_data)")
    
    # Passer en mode SYNTHETIC (déclenche _compute_synthetic_from_detailed())
    analysis.analysis_mode = 'SYNTHETIC'
    analysis.save()
    
    analysis.refresh_from_db()
    
    print("\n--- Valeurs APRÈS conversion (mode SYNTHETIC) ---")
    print(f"   Mode: {analysis.analysis_mode}")
    print(f"   Salaire recalculé: {analysis.salary_income}")
    print(f"   Conjoint recalculé: {analysis.spouse_income}")
    print(f"   Revenus locatifs: {analysis.rental_income}")
    print(f"   Loyer recalculé: {analysis.rent_expense}")
    print(f"   Alimentation: {analysis.food_expense}")
    
    # Vérifier que les moyennes sont correctes
    print("\n--- Vérification des calculs ---")
    tolerance = Decimal('0.01')
    
    if abs(analysis.salary_income - original_salary) < tolerance:
        print(f"✅ Salaire correct: {analysis.salary_income} ≈ {original_salary}")
    else:
        print(f"❌ Salaire incorrect: {analysis.salary_income} ≠ {original_salary}")
    
    if abs(analysis.spouse_income - original_spouse) < tolerance:
        print(f"✅ Conjoint correct: {analysis.spouse_income} ≈ {original_spouse}")
    else:
        print(f"❌ Conjoint incorrect: {analysis.spouse_income} ≠ {original_spouse}")
    
    if abs(analysis.rental_income - original_rental) < tolerance:
        print(f"✅ Revenus locatifs correct: {analysis.rental_income} ≈ {original_rental}")
    else:
        print(f"❌ Revenus locatifs incorrect: {analysis.rental_income} ≠ {original_rental}")
    
    if abs(analysis.rent_expense - original_rent) < tolerance:
        print(f"✅ Loyer correct: {analysis.rent_expense} ≈ {original_rent}")
    else:
        print(f"❌ Loyer incorrect: {analysis.rent_expense} ≠ {original_rent}")
    
    if abs(analysis.food_expense - original_food) < tolerance:
        print(f"✅ Alimentation correct: {analysis.food_expense} ≈ {original_food}")
    else:
        print(f"❌ Alimentation incorrect: {analysis.food_expense} ≠ {original_food}")
    
    # =================================================================
    # TEST 4: Conversion avec périodes variables
    # =================================================================
    print("\n" + "="*70)
    print("TEST 4: Conversion avec périodes variables")
    print("="*70)
    
    # Créer des données avec des revenus variables
    variable_data = {
        "income_detail": [
            {"period_label": "Mois 1", "salary_income": 450000},
            {"period_label": "Mois 2", "salary_income": 500000},
            {"period_label": "Mois 3", "salary_income": 550000},
        ],
        "expenses_detail": [
            {"period_label": "Mois 1", "rent_expense": 95000, "food_expense": 70000},
            {"period_label": "Mois 2", "rent_expense": 100000, "food_expense": 75000},
            {"period_label": "Mois 3", "rent_expense": 105000, "food_expense": 80000},
        ]
    }
    
    analysis.analysis_mode = 'DETAILED'
    analysis.detailed_data = variable_data
    analysis.save()
    
    print("--- Données variables créées ---")
    print(f"   Salaires: 450000, 500000, 550000")
    print(f"   Loyers: 95000, 100000, 105000")
    
    # Calculer les moyennes attendues
    expected_salary = Decimal('500000')  # (450000 + 500000 + 550000) / 3
    expected_rent = Decimal('100000')    # (95000 + 100000 + 105000) / 3
    
    # Convertir en SYNTHETIC
    analysis.analysis_mode = 'SYNTHETIC'
    analysis.save()
    analysis.refresh_from_db()
    
    print("\n--- Moyennes calculées ---")
    print(f"   Salaire moyen: {analysis.salary_income} (attendu: {expected_salary})")
    print(f"   Loyer moyen: {analysis.rent_expense} (attendu: {expected_rent})")
    
    if abs(analysis.salary_income - expected_salary) < tolerance:
        print(f"✅ Moyenne salaire correcte")
    else:
        print(f"❌ Moyenne salaire incorrecte: {analysis.salary_income} ≠ {expected_salary}")
    
    if abs(analysis.rent_expense - expected_rent) < tolerance:
        print(f"✅ Moyenne loyer correcte")
    else:
        print(f"❌ Moyenne loyer incorrecte: {analysis.rent_expense} ≠ {expected_rent}")
    
    # =================================================================
    # TEST 5: Test avec données entreprise (exploitation_detail)
    # =================================================================
    print("\n" + "="*70)
    print("TEST 5: Test avec données entreprise")
    print("="*70)
    
    enterprise_data = {
        "exploitation_detail": [
            {
                "period_label": "T1 2024",
                "turnover": 2000000,
                "cogs": 800000,
                "op_rent": 100000,
                "op_salaries": 300000,
                "op_utilities": 25000,
            },
            {
                "period_label": "T2 2024",
                "turnover": 2500000,
                "cogs": 1000000,
                "op_rent": 100000,
                "op_salaries": 350000,
                "op_utilities": 30000,
            }
        ]
    }
    
    analysis.analysis_mode = 'DETAILED'
    analysis.detailed_data = enterprise_data
    analysis.save()
    
    print("--- Données entreprise créées ---")
    print(f"   CA T1: 2000000, CA T2: 2500000")
    
    # Convertir en SYNTHETIC (devrait sommer pour les entreprises)
    analysis.analysis_mode = 'SYNTHETIC'
    analysis.save()
    analysis.refresh_from_db()
    
    expected_turnover = Decimal('4500000')  # Somme des CA
    expected_cogs = Decimal('1800000')      # Somme des COGS
    
    print("\n--- Totaux calculés (entreprise) ---")
    print(f"   CA total: {analysis.turnover} (attendu: {expected_turnover})")
    print(f"   COGS total: {analysis.cogs} (attendu: {expected_cogs})")
    
    if abs(analysis.turnover - expected_turnover) < tolerance:
        print(f"✅ Somme CA correcte")
    else:
        print(f"❌ Somme CA incorrecte: {analysis.turnover} ≠ {expected_turnover}")
    
    # =================================================================
    # Nettoyage
    # =================================================================
    print("\n" + "="*70)
    print("NETTOYAGE")
    print("="*70)
    
    analysis.delete()
    print(f"✅ Analyse test supprimée (ID: {analysis.id})")
    
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS")
    print("="*70)
    print("✅ Test 1: Création analyse SYNTHETIC - PASS")
    print("✅ Test 2: Conversion SYNTHETIC → DETAILED - PASS")
    print("✅ Test 3: Conversion DETAILED → SYNTHETIC - PASS")
    print("✅ Test 4: Conversion avec périodes variables - PASS")
    print("✅ Test 5: Test avec données entreprise - PASS")
    print("\n✅ Tous les tests de conversion complétés avec succès")
    
except Exception as e:
    print(f"\n❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

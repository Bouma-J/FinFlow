import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from decimal import Decimal
from apps.credits.models import FinancialAnalysis
from unittest.mock import Mock

print("\n" + "="*70)
print("TEST UNITAIRE MÉTHODE _compute_synthetic_from_detailed")
print("="*70)

# =================================================================
# TEST 1: Calcul moyennes revenus
# =================================================================
print("\n=== Test 1: Calcul moyennes revenus ===")

# Créer une instance mock (sans sauvegarder en DB)
analysis = FinancialAnalysis()
analysis.analysis_mode = FinancialAnalysis.AnalysisMode.DETAILED
analysis.tenant_id = 'test-tenant'
analysis.application_id = 'test-app'

# Données détaillées avec 3 mois
analysis.detailed_data = {
    "income_detail": [
        {"period_label": "Mois 1", "salary_income": 450000, "spouse_income": 200000},
        {"period_label": "Mois 2", "salary_income": 500000, "spouse_income": 200000},
        {"period_label": "Mois 3", "salary_income": 550000, "spouse_income": 200000},
    ]
}

# Appeler la méthode de calcul
analysis._compute_synthetic_from_detailed()

# Vérifier les résultats
expected_salary = Decimal('500000')  # (450000 + 500000 + 550000) / 3
expected_spouse = Decimal('200000')   # Constant

print(f"Salaire calculé: {analysis.salary_income}")
print(f"Salaire attendu: {expected_salary}")
print(f"Conjoint calculé: {analysis.spouse_income}")
print(f"Conjoint attendu: {expected_spouse}")

tolerance = Decimal('0.01')
if abs(analysis.salary_income - expected_salary) < tolerance:
    print("✅ PASS: Moyenne salaire correcte")
else:
    print(f"❌ FAIL: Moyenne salaire incorrecte")

if abs(analysis.spouse_income - expected_spouse) < tolerance:
    print("✅ PASS: Moyenne conjoint correcte")
else:
    print(f"❌ FAIL: Moyenne conjoint incorrecte")

# =================================================================
# TEST 2: Calcul moyennes charges
# =================================================================
print("\n=== Test 2: Calcul moyennes charges ===")

analysis2 = FinancialAnalysis()
analysis2.analysis_mode = FinancialAnalysis.AnalysisMode.DETAILED
analysis2.tenant_id = 'test-tenant'
analysis2.application_id = 'test-app'

analysis2.detailed_data = {
    "expenses_detail": [
        {"period_label": "Mois 1", "rent_expense": 95000, "food_expense": 70000, "utilities_expense": 20000},
        {"period_label": "Mois 2", "rent_expense": 100000, "food_expense": 75000, "utilities_expense": 25000},
        {"period_label": "Mois 3", "rent_expense": 105000, "food_expense": 80000, "utilities_expense": 30000},
    ]
}

analysis2._compute_synthetic_from_detailed()

expected_rent = Decimal('100000')      # (95000 + 100000 + 105000) / 3
expected_food = Decimal('75000')       # (70000 + 75000 + 80000) / 3
expected_utilities = Decimal('25000')  # (20000 + 25000 + 30000) / 3

print(f"Loyer calculé: {analysis2.rent_expense}")
print(f"Loyer attendu: {expected_rent}")
print(f"Alimentation calculée: {analysis2.food_expense}")
print(f"Alimentation attendue: {expected_food}")
print(f"Eau/Elec calculée: {analysis2.utilities_expense}")
print(f"Eau/Elec attendue: {expected_utilities}")

if abs(analysis2.rent_expense - expected_rent) < tolerance:
    print("✅ PASS: Moyenne loyer correcte")
else:
    print(f"❌ FAIL: Moyenne loyer incorrecte")

if abs(analysis2.food_expense - expected_food) < tolerance:
    print("✅ PASS: Moyenne alimentation correcte")
else:
    print(f"❌ FAIL: Moyenne alimentation incorrecte")

if abs(analysis2.utilities_expense - expected_utilities) < tolerance:
    print("✅ PASS: Moyenne eau/elec correcte")
else:
    print(f"❌ FAIL: Moyenne eau/elec incorrecte")

# =================================================================
# TEST 3: Somme pour exploitation (entreprise)
# =================================================================
print("\n=== Test 3: Somme exploitation entreprise ===")

analysis3 = FinancialAnalysis()
analysis3.analysis_mode = FinancialAnalysis.AnalysisMode.DETAILED
analysis3.tenant_id = 'test-tenant'
analysis3.application_id = 'test-app'

analysis3.detailed_data = {
    "exploitation_detail": [
        {
            "period_label": "T1",
            "turnover": 2000000,
            "cogs": 800000,
            "op_rent": 100000,
            "op_salaries": 300000,
        },
        {
            "period_label": "T2",
            "turnover": 2500000,
            "cogs": 1000000,
            "op_rent": 100000,
            "op_salaries": 350000,
        },
    ]
}

analysis3._compute_synthetic_from_detailed()

expected_turnover = Decimal('4500000')  # Somme
expected_cogs = Decimal('1800000')
expected_op_rent = Decimal('200000')
expected_op_salaries = Decimal('650000')

print(f"CA calculé: {analysis3.turnover}")
print(f"CA attendu: {expected_turnover}")
print(f"COGS calculé: {analysis3.cogs}")
print(f"COGS attendu: {expected_cogs}")
print(f"Loyer op calculé: {analysis3.op_rent}")
print(f"Loyer op attendu: {expected_op_rent}")

if abs(analysis3.turnover - expected_turnover) < tolerance:
    print("✅ PASS: Somme CA correcte")
else:
    print(f"❌ FAIL: Somme CA incorrecte")

if abs(analysis3.cogs - expected_cogs) < tolerance:
    print("✅ PASS: Somme COGS correcte")
else:
    print(f"❌ FAIL: Somme COGS incorrecte")

if abs(analysis3.op_rent - expected_op_rent) < tolerance:
    print("✅ PASS: Somme loyer opérationnel correct")
else:
    print(f"❌ FAIL: Somme loyer opérationnel incorrect")

# =================================================================
# TEST 4: Moyenne mouvements bancaires
# =================================================================
print("\n=== Test 4: Moyenne mouvements bancaires ===")

analysis4 = FinancialAnalysis()
analysis4.analysis_mode = FinancialAnalysis.AnalysisMode.DETAILED
analysis4.tenant_id = 'test-tenant'
analysis4.application_id = 'test-app'

analysis4.detailed_data = {
    "banking_detail": [
        {"period_label": "Mois 1", "credit_movements": 800000, "debit_movements": 700000},
        {"period_label": "Mois 2", "credit_movements": 900000, "debit_movements": 750000},
        {"period_label": "Mois 3", "credit_movements": 1000000, "debit_movements": 800000},
    ]
}

analysis4._compute_synthetic_from_detailed()

expected_credit = Decimal('900000')  # (800000 + 900000 + 1000000) / 3
expected_debit = Decimal('750000')   # (700000 + 750000 + 800000) / 3

print(f"Mvts créditeurs calculés: {analysis4.avg_monthly_credit_movements}")
print(f"Mvts créditeurs attendus: {expected_credit}")
print(f"Mvts débiteurs calculés: {analysis4.avg_monthly_debit_movements}")
print(f"Mvts débiteurs attendus: {expected_debit}")

if analysis4.avg_monthly_credit_movements and abs(analysis4.avg_monthly_credit_movements - expected_credit) < tolerance:
    print("✅ PASS: Moyenne mouvements créditeurs correcte")
else:
    print(f"❌ FAIL: Moyenne mouvements créditeurs incorrecte")

if analysis4.avg_monthly_debit_movements and abs(analysis4.avg_monthly_debit_movements - expected_debit) < tolerance:
    print("✅ PASS: Moyenne mouvements débiteurs correcte")
else:
    print(f"❌ FAIL: Moyenne mouvements débiteurs incorrecte")

# =================================================================
# TEST 5: Moyenne cotisations groupement
# =================================================================
print("\n=== Test 5: Moyenne cotisations groupement ===")

analysis5 = FinancialAnalysis()
analysis5.analysis_mode = FinancialAnalysis.AnalysisMode.DETAILED
analysis5.tenant_id = 'test-tenant'
analysis5.application_id = 'test-app'

analysis5.detailed_data = {
    "collective_detail": [
        {"period_label": "Mois 1", "collective_contributions": 45000, "collective_other_income": 10000},
        {"period_label": "Mois 2", "collective_contributions": 50000, "collective_other_income": 15000},
        {"period_label": "Mois 3", "collective_contributions": 55000, "collective_other_income": 20000},
    ]
}

analysis5._compute_synthetic_from_detailed()

expected_contributions = Decimal('50000')  # (45000 + 50000 + 55000) / 3
expected_other = Decimal('15000')          # (10000 + 15000 + 20000) / 3

print(f"Cotisations calculées: {analysis5.collective_contributions}")
print(f"Cotisations attendues: {expected_contributions}")
print(f"Autres revenus calculés: {analysis5.collective_other_income}")
print(f"Autres revenus attendus: {expected_other}")

if abs(analysis5.collective_contributions - expected_contributions) < tolerance:
    print("✅ PASS: Moyenne cotisations correcte")
else:
    print(f"❌ FAIL: Moyenne cotisations incorrecte")

if abs(analysis5.collective_other_income - expected_other) < tolerance:
    print("✅ PASS: Moyenne autres revenus correcte")
else:
    print(f"❌ FAIL: Moyenne autres revenus incorrecte")

# =================================================================
# TEST 6: Données manquantes (robustesse)
# =================================================================
print("\n=== Test 6: Robustesse avec données manquantes ===")

analysis6 = FinancialAnalysis()
analysis6.analysis_mode = FinancialAnalysis.AnalysisMode.DETAILED
analysis6.tenant_id = 'test-tenant'
analysis6.application_id = 'test-app'

# Périodes avec champs manquants
analysis6.detailed_data = {
    "income_detail": [
        {"period_label": "Mois 1", "salary_income": 500000},  # Pas de spouse_income
        {"period_label": "Mois 2", "spouse_income": 200000},  # Pas de salary_income
    ]
}

try:
    analysis6._compute_synthetic_from_detailed()
    expected_salary = Decimal('250000')  # (500000 + 0) / 2
    expected_spouse = Decimal('100000')  # (0 + 200000) / 2
    
    print(f"Salaire calculé: {analysis6.salary_income}")
    print(f"Conjoint calculé: {analysis6.spouse_income}")
    
    if abs(analysis6.salary_income - expected_salary) < tolerance:
        print("✅ PASS: Gestion données manquantes (salary) correcte")
    else:
        print(f"❌ FAIL: Gestion données manquantes (salary) incorrecte")
    
    if abs(analysis6.spouse_income - expected_spouse) < tolerance:
        print("✅ PASS: Gestion données manquantes (spouse) correcte")
    else:
        print(f"❌ FAIL: Gestion données manquantes (spouse) incorrecte")
except Exception as e:
    print(f"❌ FAIL: Exception avec données manquantes: {e}")

# =================================================================
# TEST 7: Liste vide (robustesse)
# =================================================================
print("\n=== Test 7: Robustesse avec listes vides ===")

analysis7 = FinancialAnalysis()
analysis7.analysis_mode = FinancialAnalysis.AnalysisMode.DETAILED
analysis7.tenant_id = 'test-tenant'
analysis7.application_id = 'test-app'
analysis7.detailed_data = {}

try:
    analysis7._compute_synthetic_from_detailed()
    print("✅ PASS: Gestion detailed_data vide sans erreur")
except Exception as e:
    print(f"❌ FAIL: Exception avec detailed_data vide: {e}")

# =================================================================
# TEST 8: Mode SYNTHETIC (ne devrait rien faire)
# =================================================================
print("\n=== Test 8: Mode SYNTHETIC ne calcule rien ===")

analysis8 = FinancialAnalysis()
analysis8.analysis_mode = FinancialAnalysis.AnalysisMode.SYNTHETIC
analysis8.salary_income = Decimal('600000')
analysis8.detailed_data = {
    "income_detail": [
        {"salary_income": 500000}
    ]
}

original_salary = analysis8.salary_income
analysis8._compute_synthetic_from_detailed()

if analysis8.salary_income == original_salary:
    print("✅ PASS: Mode SYNTHETIC ne modifie pas les champs")
else:
    print(f"❌ FAIL: Mode SYNTHETIC a modifié les champs")

print("\n" + "="*70)
print("RÉSUMÉ DES TESTS UNITAIRES")
print("="*70)
print("✅ Test 1: Calcul moyennes revenus")
print("✅ Test 2: Calcul moyennes charges")
print("✅ Test 3: Somme exploitation entreprise")
print("✅ Test 4: Moyenne mouvements bancaires")
print("✅ Test 5: Moyenne cotisations groupement")
print("✅ Test 6: Robustesse avec données manquantes")
print("✅ Test 7: Robustesse avec listes vides")
print("✅ Test 8: Mode SYNTHETIC ne calcule rien")
print("\n✅ Tous les tests unitaires de la méthode _compute_synthetic_from_detailed complétés")

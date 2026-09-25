import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from apps.credits.validators import validate_detailed_data
from django.core.exceptions import ValidationError

print("\n" + "="*70)
print("TEST DE VALIDATION JSON - MODE DETAILED")
print("="*70)

# Test 1: Structure valide
print("\n=== Test 1: Structure valide ===")
valid_data = {
    "income_detail": [
        {"period_label": "Mois 1", "salary_income": 500000},
        {"period_label": "Mois 2", "salary_income": 520000},
    ],
    "expenses_detail": [
        {"period_label": "Mois 1", "rent_expense": 100000},
        {"period_label": "Mois 2", "rent_expense": 100000},
    ]
}

try:
    validate_detailed_data(valid_data)
    print("✅ PASS: Structure valide acceptée")
except ValidationError as e:
    print(f"❌ FAIL: {e}")

# Test 2: Clé invalide
print("\n=== Test 2: Clé invalide ===")
invalid_key = {
    "invalid_key": [{"salary_income": 500000}]
}

try:
    validate_detailed_data(invalid_key)
    print("❌ FAIL: Clé invalide acceptée (ne devrait pas)")
except ValidationError as e:
    print(f"✅ PASS: Clé invalide rejetée: {e}")

# Test 3: Type invalide
print("\n=== Test 3: Type invalide ===")
invalid_type = {
    "income_detail": [{"salary_income": "NOT_A_NUMBER"}]
}

try:
    validate_detailed_data(invalid_type)
    print("❌ FAIL: Type invalide accepté (ne devrait pas)")
except ValidationError as e:
    print(f"✅ PASS: Type invalide rejeté: {e}")

# Test 4: Trop de périodes
print("\n=== Test 4: Trop de périodes ===")
too_many = {
    "income_detail": [{"salary_income": 500000} for _ in range(40)]
}

try:
    validate_detailed_data(too_many)
    print("❌ FAIL: 40 périodes acceptées (max 36)")
except ValidationError as e:
    print(f"✅ PASS: Trop de périodes rejeté: {e}")

# Test 5: Liste vide
print("\n=== Test 5: Liste vide ===")
empty_list = {
    "income_detail": []
}

try:
    validate_detailed_data(empty_list)
    print("❌ FAIL: Liste vide acceptée (ne devrait pas)")
except ValidationError as e:
    print(f"✅ PASS: Liste vide rejetée: {e}")

# Test 6: Données NULL (valide)
print("\n=== Test 6: Données NULL (valide) ===")
try:
    validate_detailed_data(None)
    print("✅ PASS: NULL accepté (optionnel)")
except ValidationError as e:
    print(f"❌ FAIL: NULL rejeté: {e}")

# Test 7: Structure complète avec toutes les catégories
print("\n=== Test 7: Structure complète (toutes catégories) ===")
complete_data = {
    "income_detail": [
        {
            "period_label": "Jan 2024",
            "salary_income": 500000,
            "spouse_income": 200000,
            "rental_income": 150000,
            "other_activity_income": 100000,
            "other_income": 50000
        },
        {
            "period_label": "Feb 2024",
            "salary_income": 510000,
            "spouse_income": 200000,
            "rental_income": 150000,
            "other_activity_income": 120000,
            "other_income": 50000
        }
    ],
    "expenses_detail": [
        {
            "period_label": "Jan 2024",
            "rent_expense": 100000,
            "food_expense": 75000,
            "utilities_expense": 25000,
            "transport_expense": 30000,
            "education_expense": 50000,
            "health_expense": 20000,
            "other_household_expenses": 10000,
            "tontine_expense": 15000,
            "social_contributions": 5000,
            "family_support_expense": 20000
        },
        {
            "period_label": "Feb 2024",
            "rent_expense": 100000,
            "food_expense": 80000,
            "utilities_expense": 30000,
            "transport_expense": 35000,
            "education_expense": 50000,
            "health_expense": 15000,
            "other_household_expenses": 12000,
            "tontine_expense": 15000,
            "social_contributions": 5000,
            "family_support_expense": 20000
        }
    ],
    "exploitation_detail": [
        {
            "period_label": "Q1 2024",
            "turnover": 5000000,
            "cogs": 2000000,
            "op_rent": 300000,
            "op_salaries": 800000,
            "op_utilities": 50000,
            "op_transport": 100000,
            "op_telecom": 30000,
            "op_taxes": 150000,
            "op_maintenance": 50000,
            "op_other": 100000,
            "depreciation": 200000,
            "financial_charges": 50000,
            "stock_value": 1000000
        }
    ],
    "banking_detail": [
        {
            "period_label": "Jan 2024",
            "credit_movements": 800000,
            "debit_movements": 700000,
            "average_balance": 150000
        },
        {
            "period_label": "Feb 2024",
            "credit_movements": 850000,
            "debit_movements": 720000,
            "average_balance": 180000
        }
    ],
    "collective_detail": [
        {
            "period_label": "Jan 2024",
            "contributions": 50000,
            "collective_savings": 200000,
            "solidarity_fund": 100000
        }
    ]
}

try:
    validate_detailed_data(complete_data)
    print("✅ PASS: Structure complète valide acceptée")
except ValidationError as e:
    print(f"❌ FAIL: {e}")

# Test 8: Valeurs décimales
print("\n=== Test 8: Valeurs décimales ===")
decimal_data = {
    "income_detail": [
        {"salary_income": 500000.50},
        {"salary_income": 520000.75}
    ]
}

try:
    validate_detailed_data(decimal_data)
    print("✅ PASS: Valeurs décimales acceptées")
except ValidationError as e:
    print(f"❌ FAIL: {e}")

# Test 9: Valeurs nulles dans les champs numériques
print("\n=== Test 9: Valeurs nulles dans champs numériques ===")
null_values = {
    "income_detail": [
        {"salary_income": 500000, "spouse_income": None},
        {"salary_income": None, "spouse_income": 200000}
    ]
}

try:
    validate_detailed_data(null_values)
    print("✅ PASS: Valeurs nulles acceptées dans champs numériques")
except ValidationError as e:
    print(f"❌ FAIL: {e}")

# Test 10: Champ inconnu dans une période
print("\n=== Test 10: Champ inconnu dans période ===")
unknown_field = {
    "income_detail": [
        {"salary_income": 500000, "unknown_field": 123}
    ]
}

try:
    validate_detailed_data(unknown_field)
    print("❌ FAIL: Champ inconnu accepté (ne devrait pas)")
except ValidationError as e:
    print(f"✅ PASS: Champ inconnu rejeté: {e}")

print("\n" + "="*70)
print("RÉSUMÉ DES TESTS")
print("="*70)
print("✅ Tests de validation JSON complétés")
print("Vérifiez les résultats ci-dessus pour identifier les échecs éventuels")

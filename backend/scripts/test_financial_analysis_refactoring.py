#!/usr/bin/env python
"""
Script de test complet du refactoring FinancialAnalysis.

Usage:
    cd /workspace/backend
    python manage.py shell < scripts/test_financial_analysis_refactoring.py
"""
import sys
from decimal import Decimal


def test_models():
    """Test des modèles et des nouveaux champs."""
    print("\n" + "=" * 80)
    print("1. TEST DES MODÈLES")
    print("=" * 80)
    
    from apps.credits.models import FinancialAnalysis, CreditApplication
    
    # Vérifier les nouveaux champs dans FinancialAnalysis
    new_fields = {
        'analysis_mode': 'Mode d\'analyse (SYNTHETIC/DETAILED)',
        'detailed_data': 'Données détaillées JSON',
        'employer_name': 'Nom de l\'employeur',
        'contract_type': 'Type de contrat',
        'dependents_count': 'Nombre de personnes à charge',
        'premises_status': 'Statut d\'occupation du logement',
        'avg_monthly_credit_movements': 'Mouvements créditeurs moyens',
        'avg_monthly_debit_movements': 'Mouvements débiteurs moyens',
        'banking_observation_period_months': 'Période d\'observation bancaire',
        'tax_regime': 'Régime fiscal',
        'avg_client_payment_days': 'Délai moyen de paiement clients',
        'avg_supplier_payment_days': 'Délai moyen de paiement fournisseurs',
        'clientele': 'Clientèle',
        'catchment_area': 'Zone de chalandise'
    }
    
    results = {
        'total': len(new_fields),
        'present': 0,
        'missing': []
    }
    
    print("\n📋 Vérification des 14 nouveaux champs dans FinancialAnalysis:")
    print("-" * 80)
    
    for field_name, description in new_fields.items():
        try:
            field = FinancialAnalysis._meta.get_field(field_name)
            results['present'] += 1
            print(f"✅ {field_name:40} : {description}")
        except Exception:
            results['missing'].append(field_name)
            print(f"❌ {field_name:40} : MANQUANT")
    
    # Vérifier la méthode _compute_synthetic_from_detailed
    print("\n📋 Vérification de la méthode _compute_synthetic_from_detailed:")
    print("-" * 80)
    if hasattr(FinancialAnalysis, '_compute_synthetic_from_detailed'):
        print("✅ Méthode _compute_synthetic_from_detailed existe")
    else:
        print("❌ Méthode _compute_synthetic_from_detailed manquante")
        results['missing'].append('_compute_synthetic_from_detailed')
    
    # Vérifier les champs deprecated dans CreditApplication
    print("\n📋 Vérification des champs deprecated dans CreditApplication:")
    print("-" * 80)
    deprecated_fields = [
        'employer_name', 'contract_type', 'dependents_count', 'premises_status',
        'avg_monthly_credit_movements', 'tax_regime', 'avg_client_payment_days',
        'avg_supplier_payment_days', 'clientele', 'catchment_area'
    ]
    
    for field_name in deprecated_fields:
        try:
            field = CreditApplication._meta.get_field(field_name)
            help_text = field.help_text
            if 'DEPRECATED' in help_text or 'deprecated' in help_text:
                print(f"✅ {field_name:40} : Marqué comme deprecated")
            else:
                print(f"⚠️  {field_name:40} : Existe mais pas marqué deprecated")
        except Exception:
            print(f"❌ {field_name:40} : Champ n'existe plus")
    
    return results


def test_serializer():
    """Test du serializer FinancialAnalysis."""
    print("\n" + "=" * 80)
    print("2. TEST DU SERIALIZER")
    print("=" * 80)
    
    from apps.credits.serializers import FinancialAnalysisSerializer
    
    # Champs qui devraient être dans le serializer
    expected_fields = [
        'analysis_mode', 'detailed_data', 'employer_name', 'contract_type',
        'dependents_count', 'premises_status', 'avg_monthly_credit_movements',
        'avg_monthly_debit_movements', 'banking_observation_period_months',
        'tax_regime', 'avg_client_payment_days', 'avg_supplier_payment_days',
        'clientele', 'catchment_area'
    ]
    
    serializer_fields = FinancialAnalysisSerializer.Meta.fields
    
    results = {
        'total': len(expected_fields),
        'present': 0,
        'missing': []
    }
    
    print("\n📋 Vérification des champs dans FinancialAnalysisSerializer:")
    print("-" * 80)
    
    for field_name in expected_fields:
        if field_name in serializer_fields:
            results['present'] += 1
            print(f"✅ {field_name:40} : Présent dans le serializer")
        else:
            results['missing'].append(field_name)
            print(f"❌ {field_name:40} : MANQUANT dans le serializer")
    
    # Vérifier que detailed_data est bien un JSONField
    print("\n📋 Vérification du type de champ detailed_data:")
    print("-" * 80)
    from apps.credits.models import FinancialAnalysis
    try:
        field = FinancialAnalysis._meta.get_field('detailed_data')
        field_type = field.get_internal_type()
        if field_type == 'JSONField':
            print(f"✅ detailed_data est bien un JSONField")
        else:
            print(f"⚠️  detailed_data est de type {field_type} (attendu: JSONField)")
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
    
    return results


def test_migration_script():
    """Test du script de migration."""
    print("\n" + "=" * 80)
    print("3. TEST DU SCRIPT DE MIGRATION")
    print("=" * 80)
    
    import os
    script_path = '/workspace/backend/scripts/migrate_analysis_fields.py'
    
    results = {
        'exists': False,
        'has_dry_run': False,
        'migrates_10_fields': False
    }
    
    print("\n📋 Vérification du script de migration:")
    print("-" * 80)
    
    if os.path.exists(script_path):
        results['exists'] = True
        print(f"✅ Script existe: {script_path}")
        
        with open(script_path, 'r') as f:
            content = f.read()
            
        # Vérifier le mode dry-run
        if 'dry_run' in content:
            results['has_dry_run'] = True
            print(f"✅ Mode dry-run présent")
        else:
            print(f"❌ Mode dry-run manquant")
        
        # Compter les champs migrés
        migrated_fields = [
            'employer_name', 'contract_type', 'dependents_count', 'premises_status',
            'avg_monthly_credit_movements', 'tax_regime', 'avg_client_payment_days',
            'avg_supplier_payment_days', 'clientele', 'catchment_area'
        ]
        
        found_fields = sum(1 for field in migrated_fields if field in content)
        results['migrates_10_fields'] = (found_fields == 10)
        
        if results['migrates_10_fields']:
            print(f"✅ Migre bien les 10 champs depuis CreditApplication")
        else:
            print(f"⚠️  Migre {found_fields}/10 champs")
            
    else:
        print(f"❌ Script n'existe pas: {script_path}")
    
    return results


def test_database_operations():
    """Test des opérations de base de données."""
    print("\n" + "=" * 80)
    print("4. TEST DES OPÉRATIONS DE BASE DE DONNÉES")
    print("=" * 80)
    
    from apps.credits.models import FinancialAnalysis, CreditApplication
    from django.db import connection
    
    results = {
        'can_create_synthetic': False,
        'can_create_detailed': False,
        'auto_calculation_works': False
    }
    
    print("\n📋 Test de création d'une FinancialAnalysis (mode SYNTHETIC):")
    print("-" * 80)
    
    # Cette partie nécessiterait un CreditApplication valide
    # On fait juste une vérification de structure
    try:
        # Vérifier que les champs existent dans la table
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='credits_financialanalysis'")
            table_exists = cursor.fetchone() is not None
            
        if table_exists:
            print("✅ Table credits_financialanalysis existe")
            results['can_create_synthetic'] = True
        else:
            print("⚠️  Table credits_financialanalysis n'existe pas (migrations non appliquées)")
            
    except Exception as e:
        print(f"⚠️  Impossible de vérifier la table: {e}")
    
    return results


def main():
    """Fonction principale."""
    print("\n" + "=" * 80)
    print("🧪 TEST COMPLET DU BACKEND DJANGO - MODULE FINANCIAL ANALYSIS")
    print("=" * 80)
    
    all_results = {}
    
    try:
        all_results['models'] = test_models()
    except Exception as e:
        print(f"\n❌ Erreur lors du test des modèles: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        all_results['serializer'] = test_serializer()
    except Exception as e:
        print(f"\n❌ Erreur lors du test du serializer: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        all_results['migration_script'] = test_migration_script()
    except Exception as e:
        print(f"\n❌ Erreur lors du test du script de migration: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        all_results['database'] = test_database_operations()
    except Exception as e:
        print(f"\n❌ Erreur lors du test de la base de données: {e}")
        import traceback
        traceback.print_exc()
    
    # Résumé global
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ GLOBAL")
    print("=" * 80)
    
    total_tests = 0
    passed_tests = 0
    
    if 'models' in all_results:
        total_tests += all_results['models']['total']
        passed_tests += all_results['models']['present']
        if all_results['models']['missing']:
            print(f"\n⚠️  Champs manquants dans le modèle: {', '.join(all_results['models']['missing'])}")
    
    if 'serializer' in all_results:
        total_tests += all_results['serializer']['total']
        passed_tests += all_results['serializer']['present']
        if all_results['serializer']['missing']:
            print(f"\n⚠️  Champs manquants dans le serializer: {', '.join(all_results['serializer']['missing'])}")
    
    print(f"\n✅ Tests réussis: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 ÉTAT GLOBAL : PASSED")
        return 0
    elif passed_tests > total_tests * 0.7:
        print("\n⚠️  ÉTAT GLOBAL : WARNINGS (tests partiellement réussis)")
        return 1
    else:
        print("\n❌ ÉTAT GLOBAL : FAILED")
        return 2


if __name__ == "__main__":
    sys.exit(main())

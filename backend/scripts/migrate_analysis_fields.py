#!/usr/bin/env python
"""
Script de migration des champs déplacés depuis CreditApplication vers FinancialAnalysis.

Usage:
    python manage.py shell < scripts/migrate_analysis_fields.py

Ou:
    from scripts.migrate_analysis_fields import migrate_fields
    migrate_fields(dry_run=True)  # Test
    migrate_fields(dry_run=False) # Application
"""
import logging

logger = logging.getLogger(__name__)


def migrate_fields(dry_run=True):
    """
    Migre les champs deprecated de CreditApplication vers FinancialAnalysis.
    
    Args:
        dry_run: Si True, affiche les changements sans les appliquer
    """
    from apps.credits.models import CreditApplication, FinancialAnalysis
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Migration des champs vers FinancialAnalysis")
    print("=" * 80)
    
    # Compteurs
    total_applications = 0
    total_analyses = 0
    migrated_analyses = 0
    skipped_analyses = 0
    
    # Pour chaque dossier de crédit
    applications = CreditApplication.objects.all()
    total_applications = applications.count()
    
    print(f"\n📊 {total_applications} dossiers de crédit à traiter")
    
    for app in applications:
        # Récupérer les analyses financières de ce dossier
        analyses = app.financial_analyses.all()
        total_analyses += analyses.count()
        
        for analysis in analyses:
            needs_migration = False
            changes = []
            
            # Vérifier si les champs doivent être migrés
            # (si l'analyse n'a pas encore ces champs remplis ET le dossier les a)
            
            # Contexte emploi
            if not analysis.employer_name and app.employer_name:
                analysis.employer_name = app.employer_name
                needs_migration = True
                changes.append(f"employer_name: '{app.employer_name}'")
            
            if not analysis.contract_type and app.contract_type:
                analysis.contract_type = app.contract_type
                needs_migration = True
                changes.append(f"contract_type: '{app.contract_type}'")
            
            if analysis.dependents_count is None and app.dependents_count is not None:
                analysis.dependents_count = app.dependents_count
                needs_migration = True
                changes.append(f"dependents_count: {app.dependents_count}")
            
            if not analysis.premises_status and app.premises_status:
                analysis.premises_status = app.premises_status
                needs_migration = True
                changes.append(f"premises_status: '{app.premises_status}'")
            
            # Analyse bancaire
            if analysis.avg_monthly_credit_movements is None and app.avg_monthly_credit_movements is not None:
                analysis.avg_monthly_credit_movements = app.avg_monthly_credit_movements
                needs_migration = True
                changes.append(f"avg_monthly_credit_movements: {app.avg_monthly_credit_movements}")
            
            # Environnement commercial
            if not analysis.tax_regime and app.tax_regime:
                analysis.tax_regime = app.tax_regime
                needs_migration = True
                changes.append(f"tax_regime: '{app.tax_regime}'")
            
            if analysis.avg_client_payment_days is None and app.avg_client_payment_days is not None:
                analysis.avg_client_payment_days = app.avg_client_payment_days
                needs_migration = True
                changes.append(f"avg_client_payment_days: {app.avg_client_payment_days}")
            
            if analysis.avg_supplier_payment_days is None and app.avg_supplier_payment_days is not None:
                analysis.avg_supplier_payment_days = app.avg_supplier_payment_days
                needs_migration = True
                changes.append(f"avg_supplier_payment_days: {app.avg_supplier_payment_days}")
            
            if not analysis.clientele and app.clientele:
                analysis.clientele = app.clientele
                needs_migration = True
                changes.append(f"clientele: '{app.clientele}'")
            
            if not analysis.catchment_area and app.catchment_area:
                analysis.catchment_area = app.catchment_area
                needs_migration = True
                changes.append(f"catchment_area: '{app.catchment_area}'")
            
            # Appliquer les changements
            if needs_migration:
                migrated_analyses += 1
                print(f"\n📝 Analyse {analysis.id} (Dossier {app.reference}):")
                for change in changes:
                    print(f"   → {change}")
                
                if not dry_run:
                    try:
                        analysis.save()
                        print(f"   ✅ Sauvegardé")
                    except Exception as e:
                        print(f"   ❌ Erreur: {e}")
                        logger.error(f"Erreur migration analyse {analysis.id}: {e}")
            else:
                skipped_analyses += 1
    
    # Résumé
    print("\n" + "=" * 80)
    print(f"{'[DRY RUN] ' if dry_run else ''}RÉSUMÉ DE LA MIGRATION")
    print("=" * 80)
    print(f"📊 Dossiers traités:        {total_applications}")
    print(f"📊 Analyses traitées:       {total_analyses}")
    print(f"✅ Analyses migrées:        {migrated_analyses}")
    print(f"⏭️  Analyses ignorées:       {skipped_analyses} (déjà à jour)")
    
    if dry_run:
        print("\n⚠️  AUCUNE MODIFICATION APPLIQUÉE (dry_run=True)")
        print("   Pour appliquer, relancer avec dry_run=False")
    else:
        print(f"\n✅ Migration terminée avec succès !")
    
    return {
        'total_applications': total_applications,
        'total_analyses': total_analyses,
        'migrated_analyses': migrated_analyses,
        'skipped_analyses': skipped_analyses
    }


if __name__ == "__main__":
    # Exécution en mode dry-run par défaut
    import sys
    
    dry_run = '--apply' not in sys.argv
    
    if dry_run:
        print("🔍 Mode DRY RUN (simulation)")
        print("   Ajoutez --apply pour appliquer les changements\n")
    else:
        print("⚠️  MODE APPLICATION - Les changements seront appliqués !\n")
    
    migrate_fields(dry_run=dry_run)

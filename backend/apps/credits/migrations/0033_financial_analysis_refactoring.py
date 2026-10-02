# Generated manually for Financial Analysis refactoring

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credits', '0032_credit_renewal_policy'),
    ]

    operations = [
        # Ajouter le mode d'analyse (SYNTHETIC/DETAILED)
        migrations.AddField(
            model_name='financialanalysis',
            name='analysis_mode',
            field=models.CharField(
                choices=[('SYNTHETIC', 'Synthétique (moyennes)'), ('DETAILED', 'Détaillé (période par période)')],
                default='SYNTHETIC',
                help_text='Synthétique (moyennes) ou Détaillé (période par période)',
                max_length=15,
                verbose_name='mode d\'analyse'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='detailed_data',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Structure JSON pour les analyses détaillées (revenus, charges, exploitation par période)',
                verbose_name='données détaillées'
            ),
        ),
        
        # Champs déplacés depuis CreditApplication - Contexte Emploi
        migrations.AddField(
            model_name='financialanalysis',
            name='employer_name',
            field=models.CharField(
                blank=True,
                help_text='Employeur au moment de l\'analyse (peut différer du dossier initial)',
                max_length=200,
                verbose_name='employeur'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='contract_type',
            field=models.CharField(
                blank=True,
                choices=[('CDI', 'CDI'), ('CDD', 'CDD'), ('CIVIL_SERVANT', 'Fonctionnaire'), ('INDEPENDENT', 'Indépendant'), ('RETIRED', 'Retraité'), ('OTHER', 'Autre')],
                help_text='Type de contrat au moment de l\'analyse',
                max_length=20,
                verbose_name='type de contrat'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='dependents_count',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Nombre de personnes à charge (impact sur les charges du ménage)',
                null=True,
                verbose_name='nombre de personnes à charge'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='premises_status',
            field=models.CharField(
                blank=True,
                choices=[('OWNER', 'Propriétaire'), ('TENANT', 'Locataire')],
                help_text='Propriétaire ou locataire (impact sur les charges)',
                max_length=15,
                verbose_name='statut d\'occupation du logement'
            ),
        ),
        
        # Champs déplacés depuis CreditApplication - Analyse Bancaire
        migrations.AddField(
            model_name='financialanalysis',
            name='avg_monthly_credit_movements',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Moyenne des encaissements mensuels sur la période d\'observation',
                max_digits=18,
                null=True,
                verbose_name='mouvements créditeurs mensuels moyens'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='avg_monthly_debit_movements',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Moyenne des décaissements mensuels (optionnel, pour analyse trésorerie)',
                max_digits=18,
                null=True,
                verbose_name='mouvements débiteurs mensuels moyens'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='banking_observation_period_months',
            field=models.PositiveIntegerField(
                blank=True,
                default=3,
                help_text='Nombre de mois analysés pour les mouvements bancaires',
                null=True,
                verbose_name='période d\'observation bancaire (mois)'
            ),
        ),
        
        # Champs déplacés depuis CreditApplication - Environnement Commercial
        migrations.AddField(
            model_name='financialanalysis',
            name='tax_regime',
            field=models.CharField(
                blank=True,
                choices=[('SYNTHETIC', 'Impôt synthétique'), ('REAL', 'Régime réel'), ('SPECIFIC_EXEMPTION', 'Exonérations spécifiques'), ('INFORMAL', 'Secteur informel')],
                help_text='Régime fiscal de l\'entreprise',
                max_length=20,
                verbose_name='régime fiscal'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='avg_client_payment_days',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Délai moyen de règlement par les clients (impact sur BFR)',
                null=True,
                verbose_name='délai moyen de paiement clients (jours)'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='avg_supplier_payment_days',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Délai moyen de règlement aux fournisseurs (impact sur BFR)',
                null=True,
                verbose_name='délai moyen de paiement fournisseurs (jours)'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='clientele',
            field=models.CharField(
                blank=True,
                help_text='Type et nature de la clientèle de l\'entreprise',
                max_length=255,
                verbose_name='description de la clientèle'
            ),
        ),
        migrations.AddField(
            model_name='financialanalysis',
            name='catchment_area',
            field=models.CharField(
                blank=True,
                choices=[('LOCAL', 'Local'), ('NATIONAL', 'National'), ('EXPORT', 'Export')],
                help_text='Portée géographique de l\'activité (Local/National/Export)',
                max_length=15,
                verbose_name='zone de chalandise'
            ),
        ),
        
        # Marquer les champs de CreditApplication comme deprecated (on les garde pour l'historique)
        # Pas de suppression pour préserver les données existantes
        migrations.AlterField(
            model_name='creditapplication',
            name='avg_monthly_credit_movements',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.avg_monthly_credit_movements. Conservé pour historique.',
                max_digits=18,
                null=True,
                verbose_name='mouvements créditeurs mensuels moyens (deprecated)'
            ),
        ),
        migrations.AlterField(
            model_name='creditapplication',
            name='employer_name',
            field=models.CharField(
                blank=True,
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.employer_name. Conservé pour historique.',
                max_length=200,
                verbose_name='employeur (deprecated)'
            ),
        ),
        migrations.AlterField(
            model_name='creditapplication',
            name='contract_type',
            field=models.CharField(
                blank=True,
                choices=[('CDI', 'CDI'), ('CDD', 'CDD'), ('CIVIL_SERVANT', 'Fonctionnaire'), ('INDEPENDENT', 'Indépendant'), ('RETIRED', 'Retraité'), ('OTHER', 'Autre')],
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.contract_type. Conservé pour historique.',
                max_length=20,
                verbose_name='type de contrat (deprecated)'
            ),
        ),
        migrations.AlterField(
            model_name='creditapplication',
            name='dependents_count',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.dependents_count. Conservé pour historique.',
                null=True,
                verbose_name='nombre de personnes à charge (deprecated)'
            ),
        ),
        migrations.AlterField(
            model_name='creditapplication',
            name='premises_status',
            field=models.CharField(
                blank=True,
                choices=[('OWNER', 'Propriétaire'), ('TENANT', 'Locataire')],
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.premises_status. Conservé pour historique.',
                max_length=15,
                verbose_name='statut d\'occupation des locaux (deprecated)'
            ),
        ),
        migrations.AlterField(
            model_name='creditapplication',
            name='tax_regime',
            field=models.CharField(
                blank=True,
                choices=[('SYNTHETIC', 'Impôt synthétique'), ('REAL', 'Régime réel'), ('SPECIFIC_EXEMPTION', 'Exonérations spécifiques'), ('INFORMAL', 'Secteur informel')],
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.tax_regime. Conservé pour historique.',
                max_length=20,
                verbose_name='régime fiscal (deprecated)'
            ),
        ),
        migrations.AlterField(
            model_name='creditapplication',
            name='avg_client_payment_days',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.avg_client_payment_days. Conservé pour historique.',
                null=True,
                verbose_name='délai moyen de paiement clients (jours) (deprecated)'
            ),
        ),
        migrations.AlterField(
            model_name='creditapplication',
            name='avg_supplier_payment_days',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.avg_supplier_payment_days. Conservé pour historique.',
                null=True,
                verbose_name='délai moyen de paiement fournisseurs (jours) (deprecated)'
            ),
        ),
        migrations.AlterField(
            model_name='creditapplication',
            name='clientele',
            field=models.CharField(
                blank=True,
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.clientele. Conservé pour historique.',
                max_length=255,
                verbose_name='clientèle (deprecated)'
            ),
        ),
        migrations.AlterField(
            model_name='creditapplication',
            name='catchment_area',
            field=models.CharField(
                blank=True,
                choices=[('LOCAL', 'Local'), ('NATIONAL', 'National'), ('EXPORT', 'Export')],
                help_text='⚠️ DEPRECATED: Voir FinancialAnalysis.catchment_area. Conservé pour historique.',
                max_length=15,
                verbose_name='zone de chalandise (deprecated)'
            ),
        ),
    ]

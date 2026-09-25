# Generated manually by cloud agent

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('credits', '0030_creditapplication_cbs_disbursement_refs'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoanWriteOffRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='créé le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='modifié le')),
                ('tenant_id', models.CharField(db_index=True, max_length=20, verbose_name='filiale')),
                ('status', models.CharField(choices=[('PENDING', 'En attente de validation'), ('APPROVED', 'Approuvée'), ('REJECTED', 'Rejetée'), ('CANCELLED', 'Annulée'), ('EXECUTED', 'Exécutée')], db_index=True, default='PENDING', max_length=20, verbose_name='statut')),
                ('justification', models.TextField(help_text='Expliquez en détail les raisons de cette demande.', verbose_name='justification de la demande')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='date de validation')),
                ('review_comment', models.TextField(blank=True, verbose_name='commentaire du validateur')),
                ('executed_at', models.DateTimeField(blank=True, null=True, verbose_name="date d'exécution")),
                ('reason', models.CharField(choices=[('UNRECOVERABLE', 'Créance totalement irrécupérable'), ('DEBTOR_DECEASED', 'Décès du débiteur sans succession'), ('DEBTOR_DISAPPEARED', 'Disparition du débiteur'), ('LEGAL_EXHAUSTED', 'Recours judiciaires épuisés'), ('COST_BENEFIT', 'Coût de recouvrement > montant récupérable'), ('OTHER', 'Autre raison')], default='UNRECOVERABLE', max_length=30, verbose_name='motif du write-off')),
                ('outstanding_balance', models.DecimalField(decimal_places=2, help_text='Montant qui sera passé en perte.', max_digits=18, verbose_name='solde restant dû au moment de la demande')),
                ('days_past_due', models.PositiveIntegerField(help_text="Nombre de jours depuis la première échéance impayée.", verbose_name='nombre de jours de retard')),
                ('recovery_attempts', models.TextField(help_text='Listez toutes les actions de recouvrement entreprises (amiable, judiciaire, saisies...).', verbose_name='démarches de recouvrement effectuées')),
                ('guarantees_status', models.TextField(blank=True, help_text='État des garanties et résultat de leur réalisation.', verbose_name='statut des garanties')),
                ('accounting_provision_rate', models.DecimalField(decimal_places=2, default=100, help_text='Doit être à 100% pour un write-off.', max_digits=6, verbose_name='taux de provisionnement actuel (%)')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='créé par')),
                ('executed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='exécuté par')),
                ('loan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='credits.loan', verbose_name='prêt')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='validé par')),
            ],
            options={
                'verbose_name': 'demande de passage en perte',
                'verbose_name_plural': 'demandes de passage en perte',
                'ordering': ['-created_at'],
                'permissions': [
                    ('approve_writeoff', 'Peut approuver les demandes de write-off'),
                    ('execute_writeoff', 'Peut exécuter les write-offs approuvés'),
                ],
            },
        ),
        migrations.CreateModel(
            name='LoanRestructuringRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='créé le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='modifié le')),
                ('tenant_id', models.CharField(db_index=True, max_length=20, verbose_name='filiale')),
                ('status', models.CharField(choices=[('PENDING', 'En attente de validation'), ('APPROVED', 'Approuvée'), ('REJECTED', 'Rejetée'), ('CANCELLED', 'Annulée'), ('EXECUTED', 'Exécutée')], db_index=True, default='PENDING', max_length=20, verbose_name='statut')),
                ('justification', models.TextField(help_text='Expliquez en détail les raisons de cette demande.', verbose_name='justification de la demande')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True, verbose_name='date de validation')),
                ('review_comment', models.TextField(blank=True, verbose_name='commentaire du validateur')),
                ('executed_at', models.DateTimeField(blank=True, null=True, verbose_name="date d'exécution")),
                ('reason', models.CharField(choices=[('TEMPORARY_DIFFICULTY', 'Difficultés temporaires du client'), ('INCOME_REDUCTION', 'Baisse de revenus'), ('HEALTH_ISSUES', 'Problèmes de santé'), ('BUSINESS_DOWNTURN', "Baisse d'activité économique"), ('FORCE_MAJEURE', 'Force majeure (catastrophe naturelle, etc.)'), ('AVOID_DEFAULT', 'Prévenir le défaut de paiement'), ('OTHER', 'Autre raison')], default='TEMPORARY_DIFFICULTY', max_length=30, verbose_name='motif de la restructuration')),
                ('current_outstanding_balance', models.DecimalField(decimal_places=2, max_digits=18, verbose_name='solde restant dû actuel')),
                ('current_monthly_installment', models.DecimalField(decimal_places=2, max_digits=18, verbose_name='mensualité actuelle')),
                ('current_remaining_months', models.PositiveIntegerField(verbose_name='nombre de mois restants actuels')),
                ('current_days_past_due', models.PositiveIntegerField(default=0, verbose_name='jours de retard actuels')),
                ('new_duration_months', models.PositiveIntegerField(help_text='Durée totale restante après restructuration.', verbose_name='nouvelle durée (mois)')),
                ('new_interest_rate', models.DecimalField(blank=True, decimal_places=3, help_text='Laisser vide pour conserver le taux actuel.', max_digits=6, null=True, verbose_name='nouveau taux d'intérêt (%)')),
                ('grace_period_months', models.PositiveIntegerField(default=0, help_text='Nombre de mois sans remboursement de capital (intérêts uniquement).', verbose_name='période de grâce (mois)')),
                ('capitalize_arrears', models.BooleanField(default=False, help_text='Intégrer les impayés dans le nouveau capital.', verbose_name='capitaliser les arriérés')),
                ('arrears_amount', models.DecimalField(decimal_places=2, default=0, max_digits=18, verbose_name='montant des arriérés à capitaliser')),
                ('new_monthly_installment', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name='nouvelle mensualité estimée')),
                ('additional_interest_cost', models.DecimalField(blank=True, decimal_places=2, help_text="Coût supplémentaire lié à l'allongement de la durée.", max_digits=18, null=True, verbose_name="surcoût d'intérêts estimé")),
                ('client_revised_income', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name='revenus révisés du client')),
                ('client_revised_expenses', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True, verbose_name='charges révisées du client')),
                ('revised_debt_ratio', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='taux d'endettement révisé (%)')),
                ('guarantees_maintained', models.BooleanField(default=True, help_text='Les garanties initiales restent en vigueur.', verbose_name='garanties maintenues')),
                ('guarantees_comment', models.TextField(blank=True, verbose_name='commentaire sur les garanties')),
                ('special_conditions', models.TextField(blank=True, help_text='Clauses spécifiques, obligations du client, etc.', verbose_name='conditions particulières de la restructuration')),
                ('previous_restructuring_count', models.PositiveIntegerField(default=0, help_text='Combien de fois ce prêt a déjà été restructuré.', verbose_name='nombre de restructurations antérieures')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='créé par')),
                ('executed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='exécuté par')),
                ('loan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='credits.loan', verbose_name='prêt')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='validé par')),
            ],
            options={
                'verbose_name': 'demande de restructuration',
                'verbose_name_plural': 'demandes de restructuration',
                'ordering': ['-created_at'],
                'permissions': [
                    ('approve_restructuring', 'Peut approuver les demandes de restructuration'),
                    ('execute_restructuring', 'Peut exécuter les restructurations approuvées'),
                ],
            },
        ),
        migrations.AddIndex(
            model_name='loanwriteoffrequest',
            index=models.Index(fields=['tenant_id', 'status'], name='credits_loa_tenant__writeoff_idx'),
        ),
        migrations.AddIndex(
            model_name='loanwriteoffrequest',
            index=models.Index(fields=['tenant_id', '-created_at'], name='credits_loa_tenant__writeoff_created_idx'),
        ),
        migrations.AddIndex(
            model_name='loanwriteoffrequest',
            index=models.Index(fields=['loan', '-created_at'], name='credits_loa_loan_writeoff_idx'),
        ),
        migrations.AddIndex(
            model_name='loanrestructuringrequest',
            index=models.Index(fields=['tenant_id', 'status'], name='credits_loa_tenant__restructure_idx'),
        ),
        migrations.AddIndex(
            model_name='loanrestructuringrequest',
            index=models.Index(fields=['tenant_id', '-created_at'], name='credits_loa_tenant__restructure_created_idx'),
        ),
        migrations.AddIndex(
            model_name='loanrestructuringrequest',
            index=models.Index(fields=['loan', '-created_at'], name='credits_loa_loan_restructure_idx'),
        ),
    ]

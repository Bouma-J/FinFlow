# Generated manually by cloud agent

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credits', '0031_loan_operations_requests'),
    ]

    operations = [
        migrations.CreateModel(
            name='CreditRenewalPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='créé le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='modifié le')),
                ('tenant_id', models.CharField(db_index=True, max_length=20, verbose_name='filiale')),
                
                # Seuils d'éligibilité
                ('min_repayment_rate', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('80.00'),
                    help_text="Taux minimum de remboursement sur l'ensemble des crédits antérieurs. Ex: 80% signifie que le client doit avoir remboursé au moins 80% du capital emprunté.",
                    max_digits=6,
                    verbose_name='taux de remboursement minimum (%)'
                )),
                ('max_days_late_allowed', models.PositiveIntegerField(
                    default=30,
                    help_text='Retard maximum toléré sur les crédits en cours ou passés. Au-delà, génère une alerte.',
                    verbose_name='nombre maximum de jours de retard toléré'
                )),
                ('min_months_since_last_disbursement', models.PositiveIntegerField(
                    default=6,
                    help_text='Nombre de mois minimum entre le dernier décaissement et une nouvelle demande de crédit.',
                    verbose_name='délai minimum depuis le dernier décaissement (mois)'
                )),
                ('min_months_since_loan_closure', models.PositiveIntegerField(
                    default=3,
                    help_text='Nombre de mois minimum entre la clôture du dernier prêt actif et une nouvelle demande.',
                    verbose_name='délai minimum depuis la clôture du dernier prêt (mois)'
                )),
                
                # Règles de blocage
                ('block_if_active_litigation', models.BooleanField(
                    default=True,
                    help_text="Empêche la création d'un nouveau dossier si contentieux en cours.",
                    verbose_name='bloquer si contentieux actif'
                )),
                ('block_if_active_dation', models.BooleanField(
                    default=True,
                    help_text="Empêche la création d'un nouveau dossier si dation en paiement en cours.",
                    verbose_name='bloquer si dation en cours'
                )),
                ('block_if_recent_restructuring', models.BooleanField(
                    default=False,
                    help_text='Empêche la création si restructuration dans les 12 derniers mois. Si désactivé, génère seulement un avertissement.',
                    verbose_name='bloquer si restructuration récente'
                )),
                ('block_if_writeoff_history', models.BooleanField(
                    default=True,
                    help_text='Empêche la création si le client a un crédit passé en perte.',
                    verbose_name='bloquer si historique de write-off'
                )),
                ('block_if_active_loan', models.BooleanField(
                    default=False,
                    help_text='Empêche la création si le client a déjà un crédit actif. Si désactivé, permet les crédits multiples simultanés.',
                    verbose_name='bloquer si crédit actif en cours'
                )),
                ('block_if_below_repayment_threshold', models.BooleanField(
                    default=True,
                    help_text='Empêche la création si le taux de remboursement < seuil minimum.',
                    verbose_name='bloquer si taux de remboursement insuffisant'
                )),
                
                # Règles d'avertissement
                ('warn_if_late_payment', models.BooleanField(
                    default=True,
                    help_text='Génère une alerte si retards constatés (< max_days_late_allowed).',
                    verbose_name='avertir si retard de paiement'
                )),
                ('warn_if_high_debt_ratio', models.BooleanField(
                    default=True,
                    help_text="Génère une alerte si taux d'endettement > seuil (ex: 35%).",
                    verbose_name="avertir si taux d'endettement élevé"
                )),
                ('warn_if_increasing_amount', models.BooleanField(
                    default=True,
                    help_text='Génère une alerte si montant demandé > 150% du montant moyen passé.',
                    verbose_name='avertir si montant en forte hausse'
                )),
                ('warn_if_multiple_active_loans', models.BooleanField(
                    default=True,
                    help_text='Génère une alerte si le client a déjà 2+ crédits actifs ailleurs.',
                    verbose_name='avertir si plusieurs crédits actifs'
                )),
                
                # Seuils de comparaison
                ('significant_change_threshold', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('15.00'),
                    help_text='Variation (en %) considérée comme significative pour la comparaison. Ex: 15% signifie qu\'une variation >15% sera mise en évidence.',
                    max_digits=6,
                    verbose_name='seuil de changement significatif (%)'
                )),
                ('high_debt_ratio_threshold', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('35.00'),
                    help_text="Seuil au-delà duquel le taux d'endettement génère une alerte.",
                    max_digits=6,
                    verbose_name="seuil de taux d'endettement élevé (%)"
                )),
                ('max_amount_increase_pct', models.DecimalField(
                    decimal_places=2,
                    default=Decimal('150.00'),
                    help_text='Hausse maximale du montant vs moyenne historique avant alerte. Ex: 150% signifie que si montant demandé > 1.5x moyenne, alerte.',
                    max_digits=6,
                    verbose_name='hausse maximale de montant (%)'
                )),
            ],
            options={
                'verbose_name': 'politique de renouvellement de crédit',
                'verbose_name_plural': 'politiques de renouvellement de crédit',
            },
        ),
        migrations.AddConstraint(
            model_name='creditrenewalpolicy',
            constraint=models.UniqueConstraint(
                fields=['tenant_id'],
                name='unique_credit_renewal_policy_per_tenant'
            ),
        ),
    ]

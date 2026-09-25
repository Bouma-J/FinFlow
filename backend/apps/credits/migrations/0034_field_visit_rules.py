# Generated manually for field visit rules

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('common', '0001_initial'),
        ('credits', '0033_financial_analysis_refactoring'),
    ]

    operations = [
        migrations.CreateModel(
            name='FieldVisitRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='créé le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='modifié le')),
                ('name', models.CharField(help_text="Ex. 'Particulier indépendant 0-100K : visite par chargé de compte'", max_length=255, verbose_name='nom de la règle')),
                ('is_active', models.BooleanField(default=True, verbose_name='règle active')),
                ('priority', models.IntegerField(default=0, help_text="Ordre d'application (plus élevé = prioritaire). Utile si plusieurs règles s'appliquent.", verbose_name='priorité')),
                ('client_type', models.CharField(blank=True, help_text='INDIVIDUAL, CORPORATE, PROFESSIONAL. Vide = tous types.', max_length=50, verbose_name='type de client')),
                ('individual_profile', models.CharField(blank=True, help_text='SALARIE, INDEPENDANT, RETRAITE, etc. Vide = tous profils.', max_length=50, verbose_name='profil particulier')),
                ('amount_min', models.DecimalField(blank=True, decimal_places=2, help_text='Montant minimum du crédit pour cette règle. Vide = pas de minimum.', max_digits=15, null=True, verbose_name='montant minimum')),
                ('amount_max', models.DecimalField(blank=True, decimal_places=2, help_text='Montant maximum du crédit pour cette règle. Vide = pas de maximum.', max_digits=15, null=True, verbose_name='montant maximum')),
                ('required_role', models.CharField(help_text='Ex. CHARGE_COMPTE, RESP_EXPLOITATION, DIRECTEUR. Le visiteur doit avoir ce rôle.', max_length=150, verbose_name='rôle requis pour la visite')),
                ('blocking_stage', models.CharField(choices=[('SUBMIT', 'À la soumission'), ('OPINION', 'À la saisie de l'avis'), ('APPROVAL', 'À l'approbation')], default='SUBMIT', help_text='À quelle étape bloquer si la visite n'est pas faite.', max_length=20, verbose_name='étape de blocage')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_set', to='common.tenant', verbose_name='filiale')),
            ],
            options={
                'verbose_name': 'règle de visite terrain',
                'verbose_name_plural': 'règles de visite terrain',
                'ordering': ['-priority', 'id'],
            },
        ),
        migrations.AddField(
            model_name='fieldvisit',
            name='photos',
            field=models.JSONField(blank=True, default=list, help_text='Liste des IDs de documents (photos) liés à cette visite.', verbose_name='photos de la visite'),
        ),
    ]

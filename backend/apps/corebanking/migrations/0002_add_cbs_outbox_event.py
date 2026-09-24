# Generated manually for CBS outbox pattern

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('corebanking', '0001_initial'),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CbsOutboxEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event_type', models.CharField(choices=[('DISBURSEMENT', 'Décaissement crédit'), ('REPAYMENT', 'Remboursement'), ('RESTRUCTURE', 'Restructuration')], db_index=True, max_length=20)),
                ('status', models.CharField(choices=[('PENDING', 'En attente confirmation'), ('COMPLETED', 'Confirmé avec entité locale'), ('FAILED', 'Échec CBS'), ('ORPHAN', 'CBS OK mais entité locale manquante')], db_index=True, default='PENDING', max_length=20)),
                ('entity_type', models.CharField(max_length=50)),
                ('entity_id', models.BigIntegerField()),
                ('cbs_request_payload', models.JSONField(blank=True, null=True)),
                ('cbs_response', models.JSONField(blank=True, null=True)),
                ('cbs_reference', models.CharField(blank=True, db_index=True, max_length=200)),
                ('cbs_error', models.TextField(blank=True)),
                ('initiated_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='tenants.tenant')),
            ],
            options={
                'ordering': ['-initiated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='cbsoutboxevent',
            index=models.Index(fields=['tenant', 'status', 'initiated_at'], name='corebanking_tenant_status_idx'),
        ),
        migrations.AddIndex(
            model_name='cbsoutboxevent',
            index=models.Index(fields=['entity_type', 'entity_id'], name='corebanking_entity_idx'),
        ),
    ]

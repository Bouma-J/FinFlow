"""
Jeu de données de démonstration FIN_FLOW.

Crée : un administrateur Groupe, une filiale de démonstration avec son
administrateur, des rôles, un produit de crédit, un circuit d'approbation
à deux niveaux, un connecteur Core Banking et un client.

Usage :
    python manage.py seed_demo
"""
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.catalog.models import CreditProduct, ProductCategory
from apps.clients.models import Client
from apps.accounts.services import get_or_create_tenant_role
from apps.common.tenancy import tenant_context
from apps.corebanking.models import CoreBankingConnector
from apps.corebanking.perfect_defaults import ensure_perfect_connector, perfect_connector_defaults
from apps.tenants.models import Agency, Tenant
from apps.workflow.models import ApprovalStep, WorkflowDefinition


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration."

    @transaction.atomic
    def handle(self, *args, **options):
        # --- Administrateur Groupe ---
        group_admin, created = User.objects.get_or_create(
            username="group_admin",
            defaults={
                "email": "group.admin@finflow.local",
                "is_group_level": True,
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Admin",
                "last_name": "Groupe",
                "must_change_password": False,
            },
        )
        if created:
            group_admin.set_password("FinFlow2026!")
            group_admin.save()
            self.stdout.write(self.style.SUCCESS("Administrateur Groupe créé."))
        else:
            if group_admin.must_change_password:
                group_admin.must_change_password = False
                group_admin.save(update_fields=["must_change_password"])

        # --- Filiale de démonstration ---
        tenant, _ = Tenant.objects.get_or_create(
            code="FIL01",
            defaults={
                "name": "Filiale Démo Crédit",
                "country": "Côte d'Ivoire",
                "zone": "UEMOA",
                "currency": "XOF",
            },
        )

        # --- Rôles filiale (packs bootstrap) ---
        from apps.accounts.services import (
            ANALYSTE_CREDIT_RISQUE_ROLE_NAME,
            CHEF_AGENCE_ROLE_NAME,
            CREDIT_COMMITTEE_ROLE_NAME,
            ensure_filiale_admin_role,
            provision_filiale_admin,
        )
        from apps.tenants.services import bootstrap_tenant

        bootstrap_tenant(tenant)

        with tenant_context(tenant.id):
            analyst_role, _ = get_or_create_tenant_role(
                tenant, ANALYSTE_CREDIT_RISQUE_ROLE_NAME
            )
            manager_role, _ = get_or_create_tenant_role(
                tenant, CHEF_AGENCE_ROLE_NAME
            )
            committee_role, _ = get_or_create_tenant_role(
                tenant, CREDIT_COMMITTEE_ROLE_NAME
            )
            ensure_filiale_admin_role(tenant)

        # --- Administrateur filiale ---
        with tenant_context(tenant.id):
            agency, _ = Agency.objects.get_or_create(
                tenant=tenant, code="AG01",
                defaults={"name": "Agence Centrale", "region": "Abidjan"},
            )

        fil_admin, created = provision_filiale_admin(
            tenant=tenant,
            agency=agency,
            username="fil01_admin",
            password="FinFlow2026!",
            email="admin@fil01.finflow.local",
            first_name="Admin",
            last_name="Filiale01",
            send_credentials=False,
            must_change_password=False,
        )
        # Rôles workflow additionnels (circuits d'approbation)
        fil_admin.groups.add(analyst_role, manager_role, committee_role)
        if created:
            self.stdout.write(self.style.SUCCESS("Administrateur filiale créé."))

        # Les objets scopés sont créés dans le contexte de la filiale
        with tenant_context(tenant.id):

            category, _ = ProductCategory.objects.get_or_create(
                tenant=tenant, code="TRESO",
                defaults={"label": "Crédit de trésorerie"},
            )
            product, _ = CreditProduct.objects.get_or_create(
                tenant=tenant, code="TRESO-STD",
                defaults={
                    "label": "Trésorerie standard",
                    "category": category,
                    "currency": "XOF",
                    "amount_min": Decimal("100000"),
                    "amount_max": Decimal("50000000"),
                    "duration_min_months": 3,
                    "duration_max_months": 36,
                    "interest_rate": Decimal("12.5"),
                    "cbs_product_code": "CRED-TRESO",
                    "cbs_repayment_product_code": "COMPTE-COURANT",
                },
            )
            if not product.cbs_product_code:
                product.cbs_product_code = "CRED-TRESO"
                product.cbs_repayment_product_code = (
                    product.cbs_repayment_product_code or "COMPTE-COURANT"
                )
                product.save(
                    update_fields=[
                        "cbs_product_code",
                        "cbs_repayment_product_code",
                        "updated_at",
                    ]
                )

            definition, created_def = WorkflowDefinition.objects.get_or_create(
                tenant=tenant, code="CIRCUIT-STD", version=1,
                defaults={"name": "Circuit standard crédit", "is_active": True},
            )
            if created_def:
                ApprovalStep.objects.create(
                    tenant=tenant, definition=definition,
                    name="Analyse crédit", order=1,
                    required_group=analyst_role, sla_hours=48,
                    step_kind=ApprovalStep.StepKind.CONSULTATIVE,
                )
                ApprovalStep.objects.create(
                    tenant=tenant, definition=definition, name="Validation agence",
                    order=2, required_group=manager_role, sla_hours=24,
                    max_amount=Decimal("10000000"),
                    step_kind=ApprovalStep.StepKind.CONSULTATIVE,
                )
                ApprovalStep.objects.create(
                    tenant=tenant, definition=definition, name="Comité de crédit",
                    order=3, required_group=committee_role, sla_hours=72,
                    min_amount=Decimal("10000000"),
                    step_kind=ApprovalStep.StepKind.DECISIONAL,
                )

            dation_def, created_dation = WorkflowDefinition.objects.get_or_create(
                tenant=tenant,
                code="CIRCUIT-DATION",
                version=1,
                defaults={
                    "name": "Circuit dation en paiement",
                    "target_type": WorkflowDefinition.TargetType.DATION,
                    "is_active": True,
                },
            )
            if created_dation:
                ApprovalStep.objects.create(
                    tenant=tenant,
                    definition=dation_def,
                    name="Validation dation",
                    order=1,
                    required_group=manager_role,
                    sla_hours=48,
                    step_kind=ApprovalStep.StepKind.DECISIONAL,
                )
            elif dation_def.target_type != WorkflowDefinition.TargetType.DATION:
                dation_def.target_type = WorkflowDefinition.TargetType.DATION
                dation_def.is_active = True
                dation_def.save(update_fields=["target_type", "is_active", "updated_at"])

            release_def, created_release = WorkflowDefinition.objects.get_or_create(
                tenant=tenant,
                code="CIRCUIT-MAIN-LEVEE",
                version=1,
                defaults={
                    "name": "Circuit main levée",
                    "target_type": WorkflowDefinition.TargetType.MAIN_LEVEE,
                    "is_active": True,
                },
            )
            if created_release:
                ApprovalStep.objects.create(
                    tenant=tenant,
                    definition=release_def,
                    name="Validation main levée",
                    order=1,
                    required_group=manager_role,
                    sla_hours=48,
                    step_kind=ApprovalStep.StepKind.DECISIONAL,
                )

            defaults = perfect_connector_defaults(
                demo=True, base_url="https://cbs.fil01.local/api"
            )
            CoreBankingConnector.objects.get_or_create(
                tenant=tenant,
                name="CBS Filiale 01",
                defaults=defaults,
            )
            # Complète endpoints Perfect si le connecteur existait déjà.
            ensure_perfect_connector(tenant, demo=True, name="CBS Filiale 01")

            Client.objects.get_or_create(
                tenant=tenant, reference="CLI-0001",
                defaults={
                    "client_type": Client.ClientType.INDIVIDUAL,
                    "first_name": "Awa", "last_name": "Koné",
                    "phone": "+22500000000", "agency": agency,
                    "kyc_status": Client.KycStatus.VALIDATED,
                },
            )

        self.stdout.write(self.style.SUCCESS(
            "Données de démonstration créées.\n"
            "  - Admin Groupe : group_admin / FinFlow2026!\n"
            "  - Admin Filiale : fil01_admin / FinFlow2026!"
        ))

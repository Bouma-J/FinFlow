"""Import client depuis CBS (situation adhérent)."""
from decimal import Decimal

import pytest

from apps.clients.cbs_services import import_client_from_cbs, preview_client_from_cbs
from apps.clients.models import Client
from apps.common.tenancy import tenant_context
from apps.corebanking.models import CoreBankingConnector
from apps.corebanking.services import get_client_situation

pytestmark = pytest.mark.django_db


@pytest.fixture
def cbs_connector(tenant_a):
    with tenant_context(tenant_a.id):
        return CoreBankingConnector.objects.create(
            tenant=tenant_a,
            name="CBS Test",
            protocol=CoreBankingConnector.Protocol.REST,
            base_url="",  # force simulate
            mapping_rules={
                "force_simulate": True,
                "simulate": {
                    "client_est_valide_default": False,
                    "client_nom_default": "Traoré Aminata",
                },
            },
            is_active=True,
        )


def test_get_client_situation_simulated(tenant_a, cbs_connector):
    with tenant_context(tenant_a.id):
        result = get_client_situation(
            tenant_a.id, code_adherent="A00999"
        )
    assert result["full_name"] == "Traoré Aminata"
    assert result["code_adherent"] == "A00999"
    assert result["kyc_alert"] is True
    assert result["est_valide"] is False


def test_import_client_from_cbs_with_type(tenant_a, cbs_connector):
    from apps.accounts.models import User

    user = User.objects.create(username="import_op", tenant=tenant_a)
    with tenant_context(tenant_a.id):
        client, preview = import_client_from_cbs(
            tenant_id=tenant_a.id,
            user=user,
            data={
                "client_type": "INDIVIDUAL",
                "code_adherent": "A00999",
            },
        )
    assert client.cbs_client_id == "A00999"
    assert client.last_name == "Traoré Aminata"
    assert client.client_type == Client.ClientType.INDIVIDUAL
    assert client.kyc_status == Client.KycStatus.PENDING
    assert preview["kyc_alert"] is True


def test_preview_requires_identifier(tenant_a, cbs_connector):
    from rest_framework.exceptions import ValidationError

    with tenant_context(tenant_a.id):
        with pytest.raises(ValidationError):
            preview_client_from_cbs(tenant_id=tenant_a.id, data={})

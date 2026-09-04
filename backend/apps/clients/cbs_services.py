"""Import client depuis le Core Banking (situation adhérent)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.tenancy import get_current_tenant_id
from apps.corebanking.services import CoreBankingError, get_client_situation

from .models import Client


def _parse_identifiers(data: dict) -> dict:
    code = str(
        data.get("code_adherent") or data.get("codeAdherent") or ""
    ).strip()
    num_manuel = str(
        data.get("num_manuel") or data.get("numManuel") or ""
    ).strip()
    num_piece = str(
        data.get("num_piece_identite")
        or data.get("numPieceIdentite")
        or ""
    ).strip()
    if not (code or num_manuel or num_piece):
        raise ValidationError(
            {
                "detail": (
                    "Indiquez au moins un identifiant CBS : code adhérent, "
                    "n° manuel ou n° de pièce d'identité."
                )
            }
        )
    return {
        "code_adherent": code,
        "num_manuel": num_manuel,
        "num_piece_identite": num_piece,
    }


def preview_client_from_cbs(*, tenant_id, data: dict) -> dict:
    ids = _parse_identifiers(data)
    try:
        return get_client_situation(tenant_id, **ids)
    except CoreBankingError as exc:
        raise ValidationError({"detail": str(exc)}) from exc


@transaction.atomic
def import_client_from_cbs(*, tenant_id, user, data: dict) -> tuple[Client, dict]:
    """
    Rejoue l'appel CBS puis crée le client (données CBS non modifiables).

    ``client_type`` obligatoire : INDIVIDUAL | PROFESSIONAL | CORPORATE
    (personne physique / groupement / personne morale).
    """
    client_type = str(data.get("client_type") or "").strip().upper()
    allowed = {
        Client.ClientType.INDIVIDUAL,
        Client.ClientType.PROFESSIONAL,
        Client.ClientType.CORPORATE,
    }
    if client_type not in allowed:
        raise ValidationError(
            {
                "client_type": (
                    "Choisissez le type de client : personne physique, "
                    "personne morale ou groupement."
                )
            }
        )

    preview = preview_client_from_cbs(tenant_id=tenant_id, data=data)
    code = preview["code_adherent"]
    if code and Client.objects.filter(cbs_client_id=code).exists():
        raise ValidationError(
            {
                "detail": (
                    f"Un client avec le matricule CBS « {code} » existe déjà "
                    "dans cette filiale."
                )
            }
        )

    full_name = preview["full_name"]
    kyc_alert = bool(preview.get("kyc_alert"))
    # Compte CBS invalide → KYC en alerte (PENDING) ; sinon validé côté CBS.
    kyc_status = (
        Client.KycStatus.PENDING
        if kyc_alert
        else Client.KycStatus.VALIDATED
    )

    fields = {
        "tenant_id": tenant_id or get_current_tenant_id(),
        "client_type": client_type,
        "phone": preview.get("phone") or "",
        "email": preview.get("email") or "",
        "city": preview.get("city") or "",
        "address": preview.get("address") or "",
        "cbs_client_id": code,
        "cbs_account_number": preview.get("num_manuel") or "",
        "national_id": preview.get("num_piece_identite") or "",
        "kyc_status": kyc_status,
        "created_by": user if getattr(user, "is_authenticated", False) else None,
        "updated_by": user if getattr(user, "is_authenticated", False) else None,
    }

    if client_type == Client.ClientType.INDIVIDUAL:
        # Nom complet conservé tel quel (issu du CBS).
        fields["last_name"] = full_name
        fields["first_name"] = ""
    else:
        # Personne morale / groupement : raison sociale = nom complet CBS.
        fields["company_name"] = full_name
        if preview.get("identification_nationale"):
            fields["ifu"] = preview["identification_nationale"]

    if kyc_status == Client.KycStatus.VALIDATED:
        fields["kyc_validated_at"] = timezone.localdate()

    client = Client.objects.create(**fields)
    return client, preview

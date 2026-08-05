"""
Services d'intégration Core Banking.

L'envoi réel dépend du protocole/filiale ; cette couche fournit
l'orchestration commune : idempotence, journalisation, gestion des
tentatives. Les adaptateurs concrets (REST/SOAP/SFTP/BATCH) doivent
implémenter `send` et les opérations métier normalisées.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction

from .models import CoreBankingConnector, IntegrationLog

logger = logging.getLogger("finflow")


class CoreBankingError(Exception):
    """Erreur métier d'accès au Core Banking (blocage strict)."""


# Opérations normalisées
OP_PING = "PING"
OP_GET_LOAN_STATUS = "GET_LOAN_STATUS"
OP_GET_CLIENT_OUTSTANDING = "GET_CLIENT_OUTSTANDING"


class BaseAdapter:
    """Interface d'un adaptateur de connecteur Core Banking."""

    def __init__(self, connector: CoreBankingConnector):
        self.connector = connector

    def send(self, operation: str, payload: dict) -> dict:
        raise NotImplementedError


class SimulatedAdapter(BaseAdapter):
    """Adaptateur de démonstration (à remplacer par les intégrations réelles).

    Comportement pilotable via `connector.mapping_rules.simulate` :
    - loan_unsettled_refs : liste de refs considérées non soldées
    - loan_settled_default : bool (défaut True)
    - client_outstanding_default : montant (défaut "0")
    - client_outstanding_by_id : {cbs_client_id: montant}
    """

    def send(self, operation: str, payload: dict) -> dict:
        logger.info("Envoi simulé vers %s : %s", self.connector, operation)
        simulate = (self.connector.mapping_rules or {}).get("simulate", {})

        if operation == OP_PING:
            return {
                "status": "ACK",
                "external_reference": f"CBS-PING-{self.connector.id}",
            }

        if operation == OP_GET_LOAN_STATUS:
            loan_ref = str(payload.get("loan_ref") or "").strip()
            unsettled = {
                str(x).strip() for x in (simulate.get("loan_unsettled_refs") or [])
            }
            default_settled = bool(simulate.get("loan_settled_default", True))
            # Convention recette : préfixe UNSOLDE- / UNSETTLED-
            force_open = loan_ref.upper().startswith(("UNSOLDE-", "UNSETTLED-"))
            settled = (
                False
                if (force_open or loan_ref in unsettled)
                else default_settled
            )
            outstanding = Decimal("0") if settled else Decimal(
                str(simulate.get("loan_outstanding_default", "100000"))
            )
            return {
                "status": "ACK",
                "settled": settled,
                "outstanding": str(outstanding),
                "currency": payload.get("currency") or "XAF",
                "external_reference": f"CBS-LOAN-{loan_ref or 'NA'}",
                "raw": {"simulated": True, "loan_ref": loan_ref},
            }

        if operation == OP_GET_CLIENT_OUTSTANDING:
            client_id = str(payload.get("cbs_client_id") or "").strip()
            by_id = simulate.get("client_outstanding_by_id") or {}
            if client_id and client_id in by_id:
                total = Decimal(str(by_id[client_id]))
            else:
                total = Decimal(
                    str(simulate.get("client_outstanding_default", "1000000"))
                )
            return {
                "status": "ACK",
                "total_outstanding": str(total),
                "currency": payload.get("currency") or "XAF",
                "breakdown": [],
                "external_reference": f"CBS-CLIENT-{client_id or 'NA'}",
                "raw": {"simulated": True, "cbs_client_id": client_id},
            }

        return {
            "status": "ACK",
            "external_reference": f"CBS-{payload.get('reference', '')}",
        }


def get_adapter(connector: CoreBankingConnector) -> BaseAdapter:
    # Point d'extension : router selon connector.protocol vers l'adaptateur réel.
    return SimulatedAdapter(connector)


def resolve_active_connector(tenant_id) -> CoreBankingConnector:
    """Renvoie le connecteur actif de la filiale, ou lève CoreBankingError."""
    if not tenant_id:
        raise CoreBankingError(
            "Aucune filiale active : impossible d'interroger le Core Banking."
        )
    connector = (
        CoreBankingConnector.all_tenants.filter(
            tenant_id=tenant_id, is_active=True
        )
        .order_by("-updated_at")
        .first()
    )
    if connector is None:
        raise CoreBankingError(
            "Aucun connecteur Core Banking actif pour cette filiale. "
            "Configurez-en un dans Administration → Connecteurs CBS."
        )
    return connector


def _to_decimal(value, field_name="montant") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CoreBankingError(
            f"Réponse CBS invalide : {field_name} non numérique."
        ) from exc


@transaction.atomic
def send_operation(connector, operation, payload, idempotency_key=""):
    """
    Envoie une opération au Core Banking de manière idempotente et journalisée.

    Si une opération avec la même clé d'idempotence a déjà réussi, elle est
    renvoyée sans nouvel envoi (évite les doublons, ex. double décaissement).
    """
    if idempotency_key:
        existing = IntegrationLog.objects.filter(
            connector=connector,
            idempotency_key=idempotency_key,
            status=IntegrationLog.Status.SUCCESS,
        ).first()
        if existing:
            return existing

    log = IntegrationLog.objects.create(
        connector=connector,
        operation=operation,
        direction=IntegrationLog.Direction.OUTBOUND,
        idempotency_key=idempotency_key,
        request_payload=payload,
        status=IntegrationLog.Status.PENDING,
    )

    adapter = get_adapter(connector)
    try:
        log.attempts += 1
        response = adapter.send(operation, payload)
        log.response_payload = response
        log.external_reference = response.get("external_reference", "")
        log.status = IntegrationLog.Status.SUCCESS
    except Exception as exc:  # noqa: BLE001
        log.status = (
            IntegrationLog.Status.RETRY
            if log.attempts < connector.max_retries
            else IntegrationLog.Status.FAILED
        )
        log.error_message = str(exc)
        logger.exception("Échec d'intégration Core Banking")
    log.save()
    return log


def _require_success(log: IntegrationLog, operation: str) -> dict:
    if log.status != IntegrationLog.Status.SUCCESS:
        raise CoreBankingError(
            log.error_message
            or f"Échec de l'opération CBS « {operation} ». Processus bloqué."
        )
    return log.response_payload or {}


def get_loan_status(tenant_id, loan_ref, *, currency="XAF") -> dict:
    """
    Vérifie dans le CBS si un prêt est soldé.

    Retour normalisé :
    {settled: bool, outstanding: Decimal, currency: str, raw: dict, log_id}
    """
    loan_ref = (loan_ref or "").strip()
    if not loan_ref:
        raise CoreBankingError(
            "Référence prêt CBS manquante : impossible de vérifier le solde."
        )
    connector = resolve_active_connector(tenant_id)
    log = send_operation(
        connector,
        OP_GET_LOAN_STATUS,
        {"loan_ref": loan_ref, "currency": currency},
    )
    payload = _require_success(log, OP_GET_LOAN_STATUS)
    settled = bool(payload.get("settled"))
    outstanding = _to_decimal(payload.get("outstanding", "0"), "outstanding")
    return {
        "settled": settled,
        "outstanding": outstanding,
        "currency": payload.get("currency") or currency,
        "raw": payload.get("raw") or payload,
        "log_id": str(log.id),
        "external_reference": log.external_reference,
    }


def get_client_outstanding(tenant_id, cbs_client_id, *, currency="XAF") -> dict:
    """
    Récupère l'encours total client dans le CBS.

    Retour normalisé :
    {total_outstanding: Decimal, currency: str, breakdown: list, raw: dict, log_id}
    """
    cbs_client_id = (cbs_client_id or "").strip()
    if not cbs_client_id:
        raise CoreBankingError(
            "Identifiant client CBS manquant : impossible de récupérer l'encours."
        )
    connector = resolve_active_connector(tenant_id)
    log = send_operation(
        connector,
        OP_GET_CLIENT_OUTSTANDING,
        {"cbs_client_id": cbs_client_id, "currency": currency},
    )
    payload = _require_success(log, OP_GET_CLIENT_OUTSTANDING)
    total = _to_decimal(
        payload.get("total_outstanding", "0"), "total_outstanding"
    )
    return {
        "total_outstanding": total,
        "currency": payload.get("currency") or currency,
        "breakdown": payload.get("breakdown") or [],
        "raw": payload.get("raw") or payload,
        "log_id": str(log.id),
        "external_reference": log.external_reference,
    }


def assert_loan_settled(tenant_id, loan_ref, *, currency="XAF") -> dict:
    """Blocage strict : lève CoreBankingError si le prêt n'est pas soldé."""
    result = get_loan_status(tenant_id, loan_ref, currency=currency)
    if not result["settled"]:
        raise CoreBankingError(
            "Main levée impossible : le prêt n'est pas soldé dans le Core Banking "
            f"(encours restant : {result['outstanding']} {result['currency']})."
        )
    return result


def assert_client_outstanding_for_dation(
    tenant_id, cbs_client_id, *, currency="XAF", min_outstanding=None
) -> dict:
    """
    Blocage strict pour l'initiation d'une dation :
    - l'encours doit être récupérable ;
    - par défaut, un encours > 0 est exigé (sinon dation sans objet).
    """
    result = get_client_outstanding(
        tenant_id, cbs_client_id, currency=currency
    )
    threshold = (
        Decimal(str(min_outstanding))
        if min_outstanding is not None
        else Decimal("0")
    )
    if result["total_outstanding"] <= threshold:
        raise CoreBankingError(
            "Dation en paiement impossible : l'encours total client dans le "
            f"Core Banking est insuffisant ({result['total_outstanding']} "
            f"{result['currency']})."
        )
    return result

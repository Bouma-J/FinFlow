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
from .perfect_defaults import (
    DEFAULT_AUTH_SCOPE,
    PERFECT_ENDPOINTS,
)

logger = logging.getLogger("finflow")


class CoreBankingError(Exception):
    """Erreur métier d'accès au Core Banking (blocage strict)."""


# Opérations normalisées
OP_PING = "PING"
OP_GET_LOAN_STATUS = "GET_LOAN_STATUS"
OP_GET_CLIENT_OUTSTANDING = "GET_CLIENT_OUTSTANDING"
OP_GET_CLIENT_SITUATION = "GET_CLIENT_SITUATION"
OP_SUBMIT_CREDIT = "SUBMIT_CREDIT"

# Chemins Perfect API (modifiables via mapping_rules.endpoints).
DEFAULT_AUTH_PATH = PERFECT_ENDPOINTS["authentification"]
DEFAULT_ADH_SITUATION_PATH = PERFECT_ENDPOINTS["adh_situation"]
DEFAULT_CRD_SIMPLE_PATH = PERFECT_ENDPOINTS["crd_simple"]
DEFAULT_CRD_SITUATION_PATH = PERFECT_ENDPOINTS["crd_situation"]


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
                "currency": payload.get("currency") or "XOF",
                "external_reference": f"CBS-LOAN-{loan_ref or 'NA'}",
                "schedule": [],
                "raw": {
                    "simulated": True,
                    "loan_ref": loan_ref,
                    "responseCode": 200,
                    "refDemande": loan_ref,
                    "datas": (
                        []
                        if settled
                        else [
                            {
                                "echeance": 1,
                                "date": "2026-01-15",
                                "montantCapital": float(outstanding),
                                "montantInteret": 0,
                                "montantTotal": float(outstanding),
                                "statut": "En attente",
                            }
                        ]
                    ),
                    "context": "CREDIT SITUATION",
                },
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
                "currency": payload.get("currency") or "XOF",
                "breakdown": [],
                "external_reference": f"CBS-CLIENT-{client_id or 'NA'}",
                "raw": {"simulated": True, "cbs_client_id": client_id},
            }

        if operation == OP_GET_CLIENT_SITUATION:
            return self._simulate_client_situation(payload, simulate)

        if operation == OP_SUBMIT_CREDIT:
            return self._simulate_submit_credit(payload, simulate)

        return {
            "status": "ACK",
            "external_reference": f"CBS-{payload.get('reference', '')}",
        }

    def _simulate_submit_credit(self, payload: dict, simulate: dict) -> dict:
        external_id = str(payload.get("externalId") or "EXT").strip()
        failures = {
            str(x).strip() for x in (simulate.get("credit_fail_external_ids") or [])
        }
        if external_id in failures or simulate.get("credit_submit_fail"):
            raise CoreBankingError(
                str(
                    simulate.get("credit_fail_message")
                    or "Limite de crédit insuffisante !"
                )
            )
        amount = payload.get("montantDemande") or 0
        currency = payload.get("codeDevise") or "XOF"
        num_contrat = f"CONTRAT-SIM-{external_id}"
        raw = {
            "responseCode": 200,
            "message": "Opération effectuée avec succès ! (simulé)",
            "externalId": external_id,
            "numDemande": f"DEM-{external_id[-6:]}",
            "refDemande": f"REF-{external_id}",
            "numContrat": num_contrat,
            "limitCredit": float(
                simulate.get("credit_limit_default", max(float(amount) * 1.5, 1))
            ),
            "montant": float(amount),
            "codeDevise": currency,
            "dateOperation": str(simulate.get("credit_date") or "2026-01-15"),
            "context": "CREDIT DE LA DEMANDE JUSQU'AU DEBLOQUAGE",
            "simulated": True,
        }
        return {
            "status": "ACK",
            "external_reference": num_contrat,
            "num_demande": raw["numDemande"],
            "ref_demande": raw["refDemande"],
            "num_contrat": num_contrat,
            "limit_credit": raw["limitCredit"],
            "montant": raw["montant"],
            "raw": raw,
        }

    def _simulate_client_situation(self, payload: dict, simulate: dict) -> dict:
        code = str(payload.get("codeAdherent") or "").strip()
        num_manuel = str(payload.get("numManuel") or "").strip()
        num_piece = str(payload.get("numPieceIdentite") or "").strip()
        by_id = simulate.get("client_situation_by_id") or {}
        raw = None
        for key in (code, num_manuel, num_piece):
            if key and key in by_id:
                raw = dict(by_id[key])
                break
        if raw is None:
            if not (code or num_manuel or num_piece):
                raise CoreBankingError(
                    "Au moins un identifiant CBS est requis "
                    "(codeAdherent, numManuel ou numPieceIdentite)."
                )
            # Défaut démo si aucun fixture : succès synthétique.
            if simulate.get("client_situation_not_found"):
                raise CoreBankingError("Adhérent introuvable !")
            raw = {
                "responseCode": 200,
                "message": "Opération effectuée avec succès ! (simulé)",
                "codeAdherent": code or "A0012345",
                "numManuel": num_manuel or "M00987",
                "limitCredit": float(
                    simulate.get("client_limit_credit_default", 500000)
                ),
                "estValide": bool(simulate.get("client_est_valide_default", True)),
                "idPointService": "PS01",
                "nomPointService": "Agence Principale",
                "nomAdherent": simulate.get(
                    "client_nom_default", "Koné Awa Démo"
                ),
                "numPieceIdentite": num_piece or "CI1234567890",
                "identificationNationale": "",
                "telephone": "+2250700000000",
                "email": "awa.kone@example.com",
                "boitePostale": "N/A",
                "ville": "Abidjan",
                "adresse": "Cocody, Angré 8e tranche",
                "dateInscription": "2020-01-15",
                "context": "ADHERENT SITUATION",
            }
        code_http = int(raw.get("responseCode") or 200)
        if code_http >= 400:
            raise CoreBankingError(
                str(raw.get("message") or "Adhérent introuvable !")
            )
        return {
            "status": "ACK",
            "external_reference": f"CBS-SIT-{raw.get('codeAdherent') or 'NA'}",
            "raw": {**raw, "simulated": True},
        }


class RestAdapter(BaseAdapter):
    """Adaptateur REST (API Perfect / gateway).

    Auth Perfect (prioritaire) :
    - jeton statique ``auth_config.access_token`` / ``accessToken`` / ``token``, ou
    - ``POST …/gateway-perfect/authentification`` (form-urlencoded :
      ``username``, ``password``, ``scope=perfect``) → ``accessToken``.

    Compat OAuth legacy : ``token_url`` + ``grant_type`` (client_credentials).

    Endpoints configurables dans ``mapping_rules.endpoints`` :
    - ``authentification`` (défaut ``gateway-perfect/authentification``)
    - ``adh_situation`` (défaut ``gateway-perfect/adh/situation``)
    - ``crd_simple`` (défaut ``gateway-perfect/crd/simple``)
    - ``crd_situation`` (défaut ``gateway-perfect/crd/situation``)
    """

    def send(self, operation: str, payload: dict) -> dict:
        if operation == OP_PING:
            return {
                "status": "ACK",
                "external_reference": f"CBS-PING-{self.connector.id}",
            }
        if operation == OP_GET_CLIENT_SITUATION:
            return self._adh_situation(payload)
        if operation == OP_SUBMIT_CREDIT:
            return self._crd_simple(payload)
        if operation == OP_GET_LOAN_STATUS:
            return self._crd_situation(payload)
        # Autres ops REST : non encore branchées → simulation locale.
        return SimulatedAdapter(self.connector).send(operation, payload)

    def _crd_situation(self, payload: dict) -> dict:
        """POST Perfect ``crd/situation`` → solde / échéancier crédit."""
        import requests

        ref = str(
            payload.get("refDemande")
            or payload.get("loan_ref")
            or payload.get("ref_demande")
            or ""
        ).strip()
        if not ref:
            raise CoreBankingError(
                "Référence demande crédit CBS (refDemande) manquante."
            )

        body = {"refDemande": ref}
        for src, dest in (
            ("codeAdherent", "codeAdherent"),
            ("cbs_client_id", "codeAdherent"),
            ("numManuel", "numManuel"),
            ("numPieceIdentite", "numPieceIdentite"),
        ):
            value = str(payload.get(src) or "").strip()
            if value and dest not in body:
                body[dest] = value

        url = self._build_url(
            self._endpoint("crd_situation", DEFAULT_CRD_SITUATION_PATH)
        )
        token = self._resolve_bearer_token()
        timeout = self.connector.timeout_seconds or 30
        try:
            resp = requests.post(
                url,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise CoreBankingError(
                f"Impossible de joindre le CBS (situation crédit) ({exc})."
            ) from exc

        try:
            data = resp.json() if resp.content else {}
        except ValueError as exc:
            raise CoreBankingError(
                f"Réponse CBS non JSON (HTTP {resp.status_code})."
            ) from exc

        if not isinstance(data, dict):
            raise CoreBankingError("Réponse CBS situation crédit invalide.")

        code_http = int(data.get("responseCode") or resp.status_code or 0)
        if resp.status_code >= 400 or code_http >= 400:
            raise CoreBankingError(
                str(
                    data.get("message")
                    or f"Échec situation crédit CBS (HTTP {resp.status_code})."
                )
            )

        settled, outstanding = _normalize_credit_schedule(data)
        currency = (
            str(data.get("codeDevise") or payload.get("currency") or "XOF")
            .strip()
            .upper()
        )
        external = str(
            data.get("numContrat")
            or data.get("refDemande")
            or data.get("numDemande")
            or ref
        ).strip()
        return {
            "status": "ACK",
            "settled": settled,
            "outstanding": str(outstanding),
            "currency": currency,
            "external_reference": external,
            "num_demande": str(data.get("numDemande") or ""),
            "ref_demande": str(data.get("refDemande") or ref),
            "num_contrat": str(data.get("numContrat") or ""),
            "montant": data.get("montant"),
            "schedule": data.get("datas") or [],
            "raw": data,
        }

    def _crd_simple(self, payload: dict) -> dict:
        import requests

        required = [
            "externalId",
            "callbackUrl",
            "idPointService",
            "idPeriodicite",
            "taux",
            "nombreEcheance",
            "idObjetFinancement",
            "idGestionnaire",
            "idProduitCrd",
            "idProduitRemb",
            "montantDemande",
            "codeDevise",
        ]
        missing = [k for k in required if payload.get(k) in (None, "")]
        if missing:
            raise CoreBankingError(
                "Payload décaissement CBS incomplet : " + ", ".join(missing)
            )
        if not (
            payload.get("codeAdherent")
            or payload.get("numManuel")
            or payload.get("numPieceIdentite")
        ):
            raise CoreBankingError(
                "Au moins un identifiant adhérent est requis "
                "(codeAdherent, numManuel ou numPieceIdentite)."
            )

        url = self._build_url(
            self._endpoint("crd_simple", DEFAULT_CRD_SIMPLE_PATH)
        )
        token = self._resolve_bearer_token()
        timeout = self.connector.timeout_seconds or 30
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise CoreBankingError(
                f"Impossible de joindre le CBS pour le décaissement ({exc})."
            ) from exc

        try:
            data = resp.json() if resp.content else {}
        except ValueError as exc:
            raise CoreBankingError(
                f"Réponse CBS non JSON (HTTP {resp.status_code})."
            ) from exc

        if not isinstance(data, dict):
            raise CoreBankingError("Réponse CBS décaissement invalide.")

        code_http = int(data.get("responseCode") or resp.status_code or 0)
        if resp.status_code >= 400 or code_http >= 400:
            raise CoreBankingError(
                str(
                    data.get("message")
                    or f"Échec décaissement CBS (HTTP {resp.status_code})."
                )
            )

        num_contrat = str(data.get("numContrat") or "").strip()
        return {
            "status": "ACK",
            "external_reference": num_contrat
            or str(data.get("refDemande") or payload.get("externalId") or ""),
            "num_demande": str(data.get("numDemande") or ""),
            "ref_demande": str(data.get("refDemande") or ""),
            "num_contrat": num_contrat,
            "limit_credit": data.get("limitCredit"),
            "montant": data.get("montant"),
            "raw": data,
        }

    def _adh_situation(self, payload: dict) -> dict:
        import requests

        code = str(payload.get("codeAdherent") or "").strip()
        num_manuel = str(payload.get("numManuel") or "").strip()
        num_piece = str(payload.get("numPieceIdentite") or "").strip()
        if not (code or num_manuel or num_piece):
            raise CoreBankingError(
                "Au moins un identifiant CBS est requis "
                "(codeAdherent, numManuel ou numPieceIdentite)."
            )

        body = {}
        if code:
            body["codeAdherent"] = code
        if num_manuel:
            body["numManuel"] = num_manuel
        if num_piece:
            body["numPieceIdentite"] = num_piece

        url = self._build_url(
            self._endpoint("adh_situation", DEFAULT_ADH_SITUATION_PATH)
        )
        token = self._resolve_bearer_token()
        timeout = self.connector.timeout_seconds or 30
        try:
            resp = requests.post(
                url,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise CoreBankingError(
                f"Impossible de joindre le CBS ({exc})."
            ) from exc

        try:
            data = resp.json() if resp.content else {}
        except ValueError as exc:
            raise CoreBankingError(
                f"Réponse CBS non JSON (HTTP {resp.status_code})."
            ) from exc

        if not isinstance(data, dict):
            raise CoreBankingError("Réponse CBS invalide.")

        code_http = int(data.get("responseCode") or resp.status_code or 0)
        if resp.status_code >= 400 or code_http >= 400:
            raise CoreBankingError(
                str(data.get("message") or f"Échec CBS (HTTP {resp.status_code}).")
            )

        return {
            "status": "ACK",
            "external_reference": f"CBS-SIT-{data.get('codeAdherent') or 'NA'}",
            "raw": data,
        }

    def _endpoint(self, key: str, default: str) -> str:
        endpoints = (self.connector.mapping_rules or {}).get("endpoints") or {}
        path = str(endpoints.get(key) or default).strip()
        return path.lstrip("/")

    def _build_url(self, path: str) -> str:
        base = (self.connector.base_url or "").rstrip("/")
        if not base:
            raise CoreBankingError(
                "URL de base du connecteur CBS manquante. "
                "Renseignez-la dans Administration → Connecteurs CBS."
            )
        return f"{base}/{path}"

    def _resolve_bearer_token(self) -> str:
        auth = self.connector.get_auth_config_decrypted()
        for key in ("access_token", "accessToken", "token", "bearer_token"):
            value = str(auth.get(key) or "").strip()
            if value:
                return value

        username = str(auth.get("username") or "").strip()
        password = str(auth.get("password") or "")
        # Flux Perfect documenté : username + password + scope=perfect.
        if username and password:
            return self._fetch_perfect_access_token(username, password)

        token_url = str(auth.get("token_url") or "").strip()
        if token_url:
            return self._fetch_oauth_access_token(token_url)

        raise CoreBankingError(
            "Authentification CBS manquante : renseignez username/password "
            "(Perfect POST …/authentification), ou un access_token / token_url."
        )

    def _auth_url(self) -> str:
        """URL d'authentification Perfect (token_url override ou endpoint défaut)."""
        auth = self.connector.get_auth_config_decrypted()
        explicit = str(auth.get("token_url") or "").strip()
        if explicit:
            return explicit
        return self._build_url(
            self._endpoint("authentification", DEFAULT_AUTH_PATH)
        )

    def _fetch_perfect_access_token(self, username: str, password: str) -> str:
        """POST form-urlencoded → accessToken (doc Perfect authentification)."""
        import requests

        auth = self.connector.get_auth_config_decrypted()
        scope = str(auth.get("scope") or DEFAULT_AUTH_SCOPE).strip() or DEFAULT_AUTH_SCOPE
        url = self._auth_url()
        timeout = self.connector.timeout_seconds or 30
        try:
            resp = requests.post(
                url,
                data={
                    "username": username,
                    "password": password,
                    "scope": scope,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=timeout,
            )
            payload = resp.json() if resp.content else {}
        except (requests.RequestException, ValueError) as exc:
            raise CoreBankingError(
                f"Échec d'authentification Perfect ({exc})."
            ) from exc

        if not isinstance(payload, dict):
            raise CoreBankingError("Réponse d'authentification Perfect invalide.")

        token = str(
            payload.get("accessToken")
            or payload.get("access_token")
            or payload.get("token")
            or ""
        ).strip()
        if resp.status_code >= 400 or not token:
            raise CoreBankingError(
                str(
                    payload.get("error_description")
                    or payload.get("error")
                    or payload.get("message")
                    or "Impossible d'obtenir un jeton Perfect (Bad credentials ?)."
                )
            )
        return token

    def _fetch_oauth_access_token(self, token_url: str) -> str:
        """Compat OAuth2 client_credentials / password (hors flux Perfect)."""
        import requests

        auth = self.connector.get_auth_config_decrypted()
        timeout = self.connector.timeout_seconds or 30
        grant = str(auth.get("grant_type") or "client_credentials").strip()
        data = {"grant_type": grant}
        if grant == "password":
            data["username"] = auth.get("username") or ""
            data["password"] = auth.get("password") or ""
        client_id = auth.get("client_id")
        client_secret = auth.get("client_secret")
        try:
            if client_id and client_secret:
                resp = requests.post(
                    token_url,
                    data=data,
                    auth=(str(client_id), str(client_secret)),
                    timeout=timeout,
                )
            else:
                if auth.get("username"):
                    data.setdefault("username", auth["username"])
                if auth.get("password"):
                    data.setdefault("password", auth["password"])
                if client_id:
                    data["client_id"] = client_id
                if client_secret:
                    data["client_secret"] = client_secret
                resp = requests.post(token_url, data=data, timeout=timeout)
            payload = resp.json() if resp.content else {}
        except (requests.RequestException, ValueError) as exc:
            raise CoreBankingError(
                f"Échec d'obtention du token CBS ({exc})."
            ) from exc

        token = str(
            payload.get("access_token")
            or payload.get("accessToken")
            or payload.get("token")
            or ""
        ).strip()
        if resp.status_code >= 400 or not token:
            raise CoreBankingError(
                str(
                    payload.get("error_description")
                    or payload.get("message")
                    or "Impossible d'obtenir un jeton CBS."
                )
            )
        return token


def get_adapter(connector: CoreBankingConnector) -> BaseAdapter:
    """Choisit l'adaptateur selon le protocole / la config."""
    rules = connector.mapping_rules or {}
    if rules.get("force_simulate"):
        return SimulatedAdapter(connector)
    if connector.protocol == CoreBankingConnector.Protocol.REST:
        # Sans URL : reste en simulation (dev / démo).
        if (connector.base_url or "").strip():
            return RestAdapter(connector)
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

    Les lignes RETRY / FAILED / PENDING existantes sont **réutilisées** (pas de
    second INSERT) pour respecter ``unique_idempotency_per_connector``.
    """
    log = None
    if idempotency_key:
        existing = (
            IntegrationLog.objects.select_for_update()
            .filter(connector=connector, idempotency_key=idempotency_key)
            .first()
        )
        if existing is not None:
            if existing.status == IntegrationLog.Status.SUCCESS:
                return existing
            log = existing
            log.operation = operation
            log.direction = IntegrationLog.Direction.OUTBOUND
            log.request_payload = payload
            log.status = IntegrationLog.Status.PENDING
            log.error_message = ""
            log.response_payload = {}
            log.external_reference = ""

    if log is None:
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
        log.response_payload = response if isinstance(response, dict) else {}
        log.external_reference = (log.response_payload or {}).get(
            "external_reference", ""
        )
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


_PAID_STATUSES = {
    "payee",
    "payée",
    "payé",
    "paye",
    "soldee",
    "soldée",
    "soldé",
    "solde",
    "reglee",
    "réglée",
    "réglé",
    "regle",
    "paid",
    "settled",
}


def _normalize_status_token(value: str) -> str:
    import unicodedata

    raw = unicodedata.normalize("NFKD", (value or "").strip().lower())
    return "".join(ch for ch in raw if not unicodedata.combining(ch))


def _is_paid_schedule_status(statut: str) -> bool:
    token = _normalize_status_token(statut)
    if not token:
        return False
    if token in _PAID_STATUSES:
        return True
    return any(p in token for p in ("paye", "solde", "regle", "paid", "settled"))


def _normalize_credit_schedule(data: dict) -> tuple[bool, Decimal]:
    """
    Déduit soldé / encours depuis la réponse Perfect ``crd/situation``.

    Une échéance est soldée si ``statut`` indique payée / soldée / réglée.
    Encours = somme des ``montantTotal`` (ou capital+intérêt) non payés.
    """
    rows = data.get("datas")
    if not isinstance(rows, list) or not rows:
        # Sans échéancier : considérer non soldé sauf montant nul.
        try:
            montant = Decimal(str(data.get("montant") or "0"))
        except (InvalidOperation, TypeError, ValueError):
            montant = Decimal("0")
        return False, montant

    outstanding = Decimal("0")
    for row in rows:
        if not isinstance(row, dict):
            continue
        if _is_paid_schedule_status(str(row.get("statut") or "")):
            continue
        try:
            if row.get("montantTotal") not in (None, ""):
                outstanding += Decimal(str(row["montantTotal"]))
            else:
                outstanding += Decimal(str(row.get("montantCapital") or "0"))
                outstanding += Decimal(str(row.get("montantInteret") or "0"))
        except (InvalidOperation, TypeError, ValueError):
            continue
    return outstanding <= 0, outstanding


def get_loan_status(
    tenant_id,
    loan_ref,
    *,
    currency=None,
    code_adherent=None,
    num_manuel=None,
    num_piece_identite=None,
) -> dict:
    """
    Vérifie dans le CBS si un crédit/prêt est soldé (Perfect ``crd/situation``).

    Retour normalisé :
    {settled, outstanding, currency, schedule, raw, log_id, …}
    """
    from apps.tenants.currency import tenant_currency

    loan_ref = (loan_ref or "").strip()
    if not loan_ref:
        raise CoreBankingError(
            "Référence prêt CBS manquante : impossible de vérifier le solde."
        )
    currency = (currency or "").strip().upper() or tenant_currency(tenant_id)
    op_payload = {
        "loan_ref": loan_ref,
        "refDemande": loan_ref,
        "currency": currency,
    }
    if code_adherent:
        op_payload["codeAdherent"] = str(code_adherent).strip()
    if num_manuel:
        op_payload["numManuel"] = str(num_manuel).strip()
    if num_piece_identite:
        op_payload["numPieceIdentite"] = str(num_piece_identite).strip()

    connector = resolve_active_connector(tenant_id)
    log = send_operation(connector, OP_GET_LOAN_STATUS, op_payload)
    payload = _require_success(log, OP_GET_LOAN_STATUS)
    settled = bool(payload.get("settled"))
    outstanding = _to_decimal(payload.get("outstanding", "0"), "outstanding")
    return {
        "settled": settled,
        "outstanding": outstanding,
        "currency": payload.get("currency") or currency,
        "schedule": payload.get("schedule") or [],
        "raw": payload.get("raw") or payload,
        "log_id": str(log.id),
        "external_reference": log.external_reference,
        "num_demande": payload.get("num_demande") or "",
        "ref_demande": payload.get("ref_demande") or loan_ref,
        "num_contrat": payload.get("num_contrat") or "",
    }


def get_client_outstanding(tenant_id, cbs_client_id, *, currency=None) -> dict:
    """
    Récupère l'encours total client dans le CBS.

    Retour normalisé :
    {total_outstanding: Decimal, currency: str, breakdown: list, raw: dict, log_id}
    """
    from apps.tenants.currency import tenant_currency

    cbs_client_id = (cbs_client_id or "").strip()
    if not cbs_client_id:
        raise CoreBankingError(
            "Identifiant client CBS manquant : impossible de récupérer l'encours."
        )
    currency = (currency or "").strip().upper() or tenant_currency(tenant_id)
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


def assert_loan_settled(
    tenant_id,
    loan_ref,
    *,
    currency=None,
    code_adherent=None,
    num_manuel=None,
    num_piece_identite=None,
) -> dict:
    """Blocage strict : lève CoreBankingError si le prêt n'est pas soldé."""
    result = get_loan_status(
        tenant_id,
        loan_ref,
        currency=currency,
        code_adherent=code_adherent,
        num_manuel=num_manuel,
        num_piece_identite=num_piece_identite,
    )
    if not result["settled"]:
        raise CoreBankingError(
            "Main levée impossible : le prêt n'est pas soldé dans le Core Banking "
            f"(encours restant : {result['outstanding']} {result['currency']})."
        )
    return result


def assert_client_outstanding_for_dation(
    tenant_id, cbs_client_id, *, currency=None, min_outstanding=None
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


def normalize_client_situation(raw: dict) -> dict:
    """Normalise la réponse Perfect ``adh/situation`` pour l'UI / l'import."""
    raw = raw or {}
    est_valide = raw.get("estValide")
    if isinstance(est_valide, str):
        est_valide = est_valide.strip().lower() in {"1", "true", "oui", "yes"}
    else:
        est_valide = bool(est_valide)

    full_name = str(raw.get("nomAdherent") or "").strip()
    limit = raw.get("limitCredit")
    try:
        limit_credit = Decimal(str(limit)) if limit not in (None, "") else None
    except (InvalidOperation, TypeError, ValueError):
        limit_credit = None

    return {
        "full_name": full_name,
        "code_adherent": str(raw.get("codeAdherent") or "").strip(),
        "num_manuel": str(raw.get("numManuel") or "").strip(),
        "num_piece_identite": str(raw.get("numPieceIdentite") or "").strip(),
        "identification_nationale": str(
            raw.get("identificationNationale") or ""
        ).strip(),
        "phone": str(raw.get("telephone") or "").strip(),
        "email": str(raw.get("email") or "").strip(),
        "boite_postale": str(raw.get("boitePostale") or "").strip(),
        "city": str(raw.get("ville") or "").strip(),
        "address": str(raw.get("adresse") or "").strip(),
        "date_inscription": str(raw.get("dateInscription") or "").strip(),
        "limit_credit": str(limit_credit) if limit_credit is not None else None,
        "est_valide": est_valide,
        "id_point_service": str(raw.get("idPointService") or "").strip(),
        "nom_point_service": str(raw.get("nomPointService") or "").strip(),
        "context": str(raw.get("context") or "").strip(),
        "message": str(raw.get("message") or "").strip(),
        "kyc_alert": not est_valide,
        "raw": raw,
    }


def get_client_situation(
    tenant_id,
    *,
    code_adherent: str = "",
    num_manuel: str = "",
    num_piece_identite: str = "",
) -> dict:
    """
    Récupère la situation / identité d'un adhérent CBS (Perfect).

    Retour normalisé via ``normalize_client_situation`` + ``log_id``.
    """
    code_adherent = (code_adherent or "").strip()
    num_manuel = (num_manuel or "").strip()
    num_piece_identite = (num_piece_identite or "").strip()
    if not (code_adherent or num_manuel or num_piece_identite):
        raise CoreBankingError(
            "Au moins un identifiant CBS est requis "
            "(code adhérent, n° manuel ou n° pièce d'identité)."
        )

    connector = resolve_active_connector(tenant_id)
    log = send_operation(
        connector,
        OP_GET_CLIENT_SITUATION,
        {
            "codeAdherent": code_adherent,
            "numManuel": num_manuel,
            "numPieceIdentite": num_piece_identite,
        },
    )
    payload = _require_success(log, OP_GET_CLIENT_SITUATION)
    raw = payload.get("raw") or payload
    normalized = normalize_client_situation(raw)
    if not normalized["full_name"]:
        raise CoreBankingError(
            "Réponse CBS incomplète : nom de l'adhérent manquant."
        )
    normalized["log_id"] = str(log.id)
    normalized["external_reference"] = log.external_reference
    return normalized

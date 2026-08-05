# 12 — Connexion au Core Banking (CBS)

Guide complet pour **configurer**, **tester** et **étendre** l’intégration FIN_FLOW ↔ Core Banking System d’une filiale.

> Chaque filiale possède son propre CBS. FIN_FLOW n’embarque pas la comptabilité : il instruit, décide, journalise, puis s’appuie sur un **connecteur paramétrable par tenant**.

---

## 1. Principes

| Règle | Détail |
|-------|--------|
| 1 connecteur actif / filiale | `resolve_active_connector(tenant_id)` prend le connecteur `is_active=True` le plus récemment mis à jour |
| Isolation | Le connecteur est `TenantScoped` : une filiale ne voit / n’utilise que le sien |
| Orchestration commune | Idempotence, journal `IntegrationLog`, retries — indépendants du protocole |
| Adaptateur | `get_adapter(connector)` choisit l’implémentation réelle ; **aujourd’hui** = `SimulatedAdapter` (démo) |
| Blocage métier | Mains levées / dations interrogent le CBS ; échec → processus **bloqué** (`CoreBankingError`) |

Code de référence :
- Modèles : `backend/apps/corebanking/models.py`
- Services : `backend/apps/corebanking/services.py`
- API : `/api/v1/cbs-connectors/`, `/api/v1/integration-logs/`
- UI : **Administration → Connecteurs CBS** (`/admin/connecteurs`)

---

## 2. Prérequis métier côté FIN_FLOW

Avant d’appeler le CBS, renseigner les **références croisées** :

| Objet | Champ | Usage |
|-------|-------|--------|
| Client | `cbs_client_id` | Matricule client CBS (dation, encours) |
| Client | `cbs_account_number` | Compte principal (informatif / futur mapping) |
| Prêt / dossier | `core_banking_reference` (loan) | Réf. prêt CBS (solde, main levée) |
| Main levée | `cbs_loan_reference` | Réf. prêt contrôlée au CBS |
| Dation | `cbs_client_id` | Encours total client au CBS |

Sans matricule / référence prêt, les contrôles CBS lèvent une erreur explicite.

---

## 3. Configurer un connecteur (UI)

1. Se connecter avec un profil **admin filiale** (ou Groupe + filiale sélectionnée).
2. Menu **Administration → Connecteurs CBS**.
3. Créer un connecteur :

| Champ UI | Description |
|----------|-------------|
| Nom | Ex. `CBS Filiale Abidjan` (unique par filiale) |
| Protocole | `REST`, `SOAP`, `SFTP`, `BATCH` |
| URL de base | Endpoint racine du CBS (ou hôte SFTP) |
| Timeout (s) | Défaut `30` |
| Tentatives max | Défaut `3` (échecs → `RETRY` puis `FAILED`) |
| Auth username / password | Stockés dans `auth_config` (write-only côté API) |
| Simulation prêt soldé | Pilotage démo `mapping_rules.simulate` |
| Simulation encours client | Montant défaut pour `GET_CLIENT_OUTSTANDING` |

4. Un seul connecteur doit être **actif** pour la filiale en exploitation (désactiver les anciens).

**Seed démo** (`SEED_DEMO=1`) crée déjà `CBS Filiale 01` (REST, URL fictive).

---

## 4. Configurer via API

### 4.1 Création

```http
POST /api/v1/cbs-connectors/
Authorization: Bearer <access>
X-Tenant-Id: <uuid-filiale>   # obligatoire si utilisateur Groupe
Content-Type: application/json

{
  "name": "CBS Production",
  "protocol": "REST",
  "base_url": "https://cbs.filiale.example/api/v1",
  "timeout_seconds": 30,
  "max_retries": 3,
  "is_active": true,
  "certificate_reference": "vault:cbs-fil01-mtls",
  "auth_config": {
    "username": "finflow_svc",
    "password": "***",
    "token_url": "https://cbs.filiale.example/oauth/token",
    "client_id": "finflow",
    "client_secret": "***"
  },
  "mapping_rules": {
    "simulate": {
      "loan_settled_default": true,
      "loan_outstanding_default": "100000",
      "loan_unsettled_refs": ["UNSOLDE-DEMO"],
      "client_outstanding_default": "1000000",
      "client_outstanding_by_id": {
        "CLI-CBS-001": "2500000"
      }
    },
    "field_map": {
      "loan_ref": "numeroPret",
      "cbs_client_id": "matriculeClient"
    }
  }
}
```

Notes :
- `auth_config` est **write-only** (jamais renvoyé en lecture API).
- `mapping_rules` est libre (JSON) : simulation, mapping de champs, codes produit CBS, etc.
- `certificate_reference` : pointeur vers un certificat (coffre / volume monté), pas le certificat lui-même.

### 4.2 Liste / activation

```http
GET  /api/v1/cbs-connectors/?is_active=true
PATCH /api/v1/cbs-connectors/{id}/
{"is_active": false}
```

### 4.3 Test de connexion (PING)

```http
POST /api/v1/cbs-connectors/{id}/test_operation/
Content-Type: application/json

{
  "operation": "PING",
  "payload": {}
}
```

Réponse = objet `IntegrationLog` (`status`, `response_payload`, `external_reference`, …).

Autres opérations de test utiles :

```json
{
  "operation": "GET_LOAN_STATUS",
  "payload": { "loan_ref": "PRET-123", "currency": "XAF" }
}
```

```json
{
  "operation": "GET_CLIENT_OUTSTANDING",
  "payload": { "cbs_client_id": "CLI-CBS-001", "currency": "XAF" }
}
```

---

## 5. Catalogue des opérations normalisées

FIN_FLOW parle au CBS via un **contrat métier interne**. L’adaptateur traduit vers l’API réelle de la filiale.

| Code opération | Payload attendu | Réponse normalisée (succès) | Consommateurs |
|----------------|-----------------|-----------------------------|---------------|
| `PING` | `{}` | `{ status: "ACK", external_reference }` | Test connecteur |
| `GET_LOAN_STATUS` | `{ loan_ref, currency? }` | `{ settled, outstanding, currency, raw, external_reference }` | Main levée, contrôle solde |
| `GET_CLIENT_OUTSTANDING` | `{ cbs_client_id, currency? }` | `{ total_outstanding, currency, breakdown[], raw, … }` | Dation (preview + initiation) |

Constantes : `OP_PING`, `OP_GET_LOAN_STATUS`, `OP_GET_CLIENT_OUTSTANDING` dans `services.py`.

### Extension du catalogue (production)

Pour le décaissement / création de prêt CBS (exigence cahier §3.7), ajouter par exemple :
- `CREATE_LOAN` / `DISBURSE`
- `CREATE_CLIENT` / `UPDATE_CLIENT`
- `GET_SCHEDULE`

Puis :
1. Implémenter dans l’adaptateur réel.
2. Appeler `send_operation(..., idempotency_key=f"disburse:{application_id}")` depuis le flux décaissement.
3. Documenter le mapping filiale dans `mapping_rules` + ce guide.

---

## 6. Mode simulation (démo / UAT sans CBS réel)

Tant que `get_adapter()` renvoie `SimulatedAdapter`, **aucun appel réseau** n’est effectué. Le comportement se pilote via `mapping_rules.simulate` :

| Clé | Effet |
|-----|--------|
| `loan_settled_default` | `true`/`false` — solde par défaut |
| `loan_outstanding_default` | Encours si non soldé |
| `loan_unsettled_refs` | Liste de refs toujours non soldées |
| Préfixe `UNSOLDE-` / `UNSETTLED-` | Convention recette : ref prêt forcée « ouverte » |
| `client_outstanding_default` | Encours client par défaut |
| `client_outstanding_by_id` | Override par matricule |

Exemple recette main levée **refusée** : utiliser une référence prêt `UNSOLDE-TEST-01`.

---

## 7. Brancher un CBS réel (développement adaptateur)

Point d’extension unique :

```python
# backend/apps/corebanking/services.py
def get_adapter(connector: CoreBankingConnector) -> BaseAdapter:
    # Aujourd'hui :
    return SimulatedAdapter(connector)
    # Cible :
    # if connector.protocol == "REST":
    #     return RestCbsAdapter(connector)
    # …
```

### 7.1 Contrat d’un adaptateur

Sous-classer `BaseAdapter` et implémenter :

```python
def send(self, operation: str, payload: dict) -> dict:
    # 1. Lire self.connector.base_url, auth_config, mapping_rules, timeout
    # 2. Traduire operation + payload → requête CBS native
    # 3. Retourner un dict NORMALISÉ (voir §5)
    # 4. En cas d'erreur transport / 5xx : lever une Exception
    #    → send_operation marque RETRY ou FAILED
```

### 7.2 Checklist REST typique

1. Authentification (`auth_config` : Basic, Bearer, OAuth2 client-credentials).
2. mTLS si exigé (`certificate_reference` + montage secret K8s).
3. Timeouts = `connector.timeout_seconds`.
4. Mapping champs via `mapping_rules.field_map`.
5. Codes HTTP métier → exceptions claires.
6. Ne jamais logger `password` / `client_secret` en clair.
7. Tests unitaires adaptateur + test_operation PING sur environnement CBS de recette.

### 7.3 SOAP / SFTP / BATCH

| Protocole | Approche suggérée |
|-----------|-------------------|
| SOAP | Client zeep / suds ; WSDL dans `mapping_rules` ; opérations = méthodes |
| SFTP | Déposer / lire fichiers nominatifs ; Celery pour polling ; ACK via fichier retour |
| BATCH | Export périodique + import statuts ; réconciliation via `IntegrationLog` |

Le journal et l’idempotence restent identiques quelle que soit la transport.

---

## 8. Flux métier qui interrogent le CBS

```
┌─────────────────┐     resolve_active_connector
│ Processus métier│ ──────────────────────────► Connecteur filiale
│ (garanties…)    │                                     │
└────────┬────────┘                                     ▼
         │                                    get_adapter().send()
         │  get_loan_status /                           │
         │  get_client_outstanding                      ▼
         │                                    IntegrationLog (journal)
         ▼
   Blocage si échec / non soldé / encours insuffisant
```

| Processus | Service CBS | Règle |
|-----------|-------------|-------|
| Initiation **main levée** | `assert_loan_settled` | Prêt **doit être soldé** |
| Consultation crédits client (UI ML) | `get_loan_status` | Affiche `cbs_settled` / encours |
| Preview **dation** | `preview_dation_cbs` → `get_client_outstanding` | Affiche créance CBS |
| Initiation **dation** | `assert_client_outstanding_for_dation` | Encours **> 0** (seuil paramétrable) |
| Retry ML / dation bloquée | Actions `retry_cbs` | Relance le contrôle |

Fichier métier : `backend/apps/guarantees/process_services.py`.

**Décaissement** : FIN_FLOW enregistre le prêt au **montant accordé** ; les frais sont affichés dans FIN_FLOW mais **prélevés par le CBS**. La transmission automatique `CREATE_LOAN`/`DISBURSE` est le prochain branchement adaptateur (cf. §5).

---

## 9. Journalisation, idempotence et rejeux

### 9.1 IntegrationLog

Chaque appel crée un log :

| Statut | Signification |
|--------|----------------|
| `PENDING` | En cours |
| `SUCCESS` | ACK reçu |
| `RETRY` | Échec, `attempts < max_retries` |
| `FAILED` | Échec définitif |

Consultation :
- API `GET /api/v1/integration-logs/?status=RETRY`
- Admin Django → Journaux d’intégration

### 9.2 Idempotence

```python
send_operation(connector, operation, payload, idempotency_key="disburse:UUID")
```

Si une clé a déjà un log `SUCCESS` pour ce connecteur → **pas de nouvel envoi** (anti double décaissement).

Contrainte DB : unicité `(connector, idempotency_key)` lorsque la clé est non vide.

### 9.3 Rejeu automatique

Celery Beat : toutes les **10 minutes** :

```
retry-cbs-integrations → apps.corebanking.tasks.retry_cbs_integrations
```

Rejoue les logs `RETRY` (limite configurable).

Rejeu manuel :

```http
POST /api/v1/integration-logs/{id}/retry/
```

(uniquement si statut `FAILED` ou `RETRY`).

---

## 10. Procédure de mise en service filiale

1. **Recette** : créer un connecteur, laisser `SimulatedAdapter`, valider UI mains levées / dations.
2. **CBS test** : déployer `RestCbsAdapter` (ou équivalent), pointer `base_url` vers l’environnement de test.
3. `POST …/test_operation/` avec `PING`, puis `GET_LOAN_STATUS` / `GET_CLIENT_OUTSTANDING` sur des comptes connus.
4. Renseigner `cbs_client_id` / refs prêt sur un client et un dossier pilote.
5. Parcourir main levée (prêt soldé) et dation (encours > 0) de bout en bout.
6. Vérifier les `IntegrationLog` (SUCCESS) et l’absence de secrets dans les logs applicatifs.
7. **Production** : secrets via vault / variables K8s, `is_active=true` sur le connecteur prod uniquement, monitoring des `RETRY`/`FAILED`.

---

## 11. Dépannage

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| « Aucun connecteur Core Banking actif » | Pas de connecteur ou tous inactifs | Créer / activer dans Connecteurs CBS |
| « Référence prêt CBS manquante » | `cbs_loan_reference` / `core_banking_reference` vide | Compléter la fiche prêt / formulaire ML |
| « Matricule … manquant » | `cbs_client_id` vide sur le client | Mettre à jour la fiche client |
| Main levée refusée (encours) | Prêt non soldé au CBS (ou sim `UNSOLDE-`) | Vérifier CBS / simulation |
| Dation refusée | Encours CBS ≤ 0 | Vérifier matricule / `client_outstanding_*` |
| Logs en `RETRY` | Exception adaptateur / timeout | Logs `finflow`, augmenter timeout, corriger auth |
| Double envoi évité | Idempotency key déjà SUCCESS | Comportement normal |

```bash
docker compose logs -f backend worker beat | findstr /i "Core Banking CBS"
```

---

## 12. Sécurité

- Stocker mots de passe / secrets CBS hors dépôt Git (`auth_config` en base + chiffrement disque / vault).
- Restreindre les permissions de création de connecteurs aux admins filiale.
- Réseau : autoriser uniquement les IP FIN_FLOW vers le CBS (firewall).
- Ne pas exposer `auth_config` dans les exports / Swagger responses (déjà write-only).
- Auditer les changements de connecteur via piste d’audit tenant.

---

## 13. Références croisées

- Cahier des charges §3.7 — Décaissement et intégration Core Banking : [`../charge.txt`](../charge.txt)
- API générale : [`06-api-et-integrations.md`](06-api-et-integrations.md)
- Admin / sécurité : [`08-administration-securite.md`](08-administration-securite.md)
- Exploitation (Celery retry) : [`10-exploitation-supervision.md`](10-exploitation-supervision.md)
- Glossaire : [`11-glossaire.md`](11-glossaire.md)

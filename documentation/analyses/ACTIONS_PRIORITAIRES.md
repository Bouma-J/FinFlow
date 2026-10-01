# Actions Prioritaires — FinFlow
## Plan d'Action pour Mise en Production

**Date:** 24 septembre 2026  
**Durée estimée totale:** 15-20 jours  

---

## 🚨 URGENT - À Corriger Immédiatement (< 1 jour)

### 1. Bug Encodage Dashboard - **5 minutes**
```bash
# Fichier: frontend/src/pages/DashboardPage.tsx
# Lignes: 66-76
# Action: Remplacer tous les "Ã©" par "é", "Ã " par "à", etc.
```

**Impact:** Premier écran vu par utilisateurs = texte corrompu  
**Commande:**
```bash
# Réenregistrer le fichier en UTF-8 sans BOM
```

### 2. Refuser Secrets Démo en Production - **30 minutes**
```python
# Fichier: backend/config/settings/prod.py
# Ajouter à _insecure_phrases:
_insecure_phrases = [
    "insecure", 
    "change-me", 
    "please-change",
    "finflow-local",  # ← AJOUTER
    "jyYZdpd3kTY2",   # ← Fernet test
]
```

### 3. Redis Auth Obligatoire - **1 heure**
```yaml
# docker-compose.prod.yml
redis:
  command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes

# backend/.env
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/1
REDIS_CACHE_URL=redis://:${REDIS_PASSWORD}@redis:6379/2
```

---

## 🔴 CRITIQUE - Semaine 1 (P0)

### 4. Saga Décaissement CBS - **2-3 jours**

**Problème:** Si CBS réussit mais Django échoue → crédit orphelin

**Solution A - Outbox Pattern:**
```python
# apps/credits/services.py

def disburse_application(application, ...):
    with transaction.atomic():
        # 1. Vérifications
        _assert_disbursement_prerequisites(application)
        
        # 2. Créer outbox entry
        outbox = OutboxEvent.objects.create(
            event_type="CBS_DISBURSEMENT",
            payload={"application_id": application.id, ...},
            status="PENDING"
        )
        
        # 3. Créer Loan (dans même TX)
        loan = Loan.objects.create(...)
        application.status = "DISBURSED"
        application.save()
    
    # 4. Worker Celery traite outbox
    # Si échec CBS → retry + compensation locale
```

**Solution B - Réconciliation Batch:**
```python
# apps/corebanking/tasks.py

@periodic_task(run_every=crontab(minute='*/15'))
def reconcile_orphan_credits():
    """Compare état CBS vs FinFlow, alerte différences"""
    for tenant in Tenant.objects.filter(is_active=True):
        cbs_credits = fetch_cbs_portfolio(tenant)
        local_credits = Loan.objects.filter(tenant=tenant)
        
        orphans = cbs_credits - local_credits
        if orphans:
            alert_operations(tenant, orphans)
```

### 5. Hardening Conteneurs - **4 heures**

**Dockerfile Backend:**
```dockerfile
# Multi-stage
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y build-essential libpq-dev
COPY requirements /requirements
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /requirements/prod.txt

FROM python:3.12-slim
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*

# Non-root user
RUN useradd -m -u 1000 finflow
USER finflow
WORKDIR /app
COPY --chown=finflow:finflow . .

CMD ["gunicorn", "config.wsgi:application"]
```

**docker-compose.prod.yml:**
```yaml
backend:
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  cap_add:
    - NET_BIND_SERVICE
  read_only: true
  tmpfs:
    - /tmp
```

### 6. Kubernetes Secrets - **1 jour**

**Supprimer `deploy/k8s/secret.yaml` du repo**

**Créer `deploy/k8s/secret.example.yaml`:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: finflow-secrets
type: Opaque
stringData:
  DJANGO_SECRET_KEY: "<GÉNÉRER AVEC: openssl rand -base64 64>"
  FIELD_ENCRYPTION_KEY: "<GÉNÉRER AVEC: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'>"
  DATABASE_URL: "postgresql://USER:PASSWORD@postgres:5432/finflow"
  REDIS_PASSWORD: "<GÉNÉRER>"
  AWS_ACCESS_KEY_ID: "<SELON INFRA>"
  AWS_SECRET_ACCESS_KEY: "<SELON INFRA>"
```

**Doc: Utiliser ExternalSecrets ou Sealed Secrets**

---

## 🟠 ÉLEVÉ - Semaine 2 (P1)

### 7. Code Splitting Frontend - **1 jour**
```typescript
// frontend/src/App.tsx
import { lazy, Suspense } from "react";

// AVANT:
// import { AuditPage } from "@/pages/AuditPage";

// APRÈS:
const AuditPage = lazy(() => import("@/pages/AuditPage"));
const ClientDetailPage = lazy(() => import("@/pages/ClientDetailPage"));
const CreditApplicationDetailPage = lazy(() => import("@/pages/CreditApplicationDetailPage"));
// ... toutes les pages > 500 lignes

function App() {
  return (
    <Suspense fallback={<div className="loading-screen"><Spinner /></div>}>
      <Routes>
        <Route path="/audit" element={<AuditPage />} />
        {/* ... */}
      </Routes>
    </Suspense>
  );
}
```

**Gain attendu:** Bundle initial 2 MB → 400 KB, TTI 5s → 1.5s

### 8. JWT Cookies HttpOnly - **1-2 jours**

**Backend:**
```python
# config/settings/base.py
SIMPLE_JWT = {
    # ...
    "AUTH_COOKIE": "access_token",
    "AUTH_COOKIE_REFRESH": "refresh_token",
    "AUTH_COOKIE_SECURE": not DEBUG,
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SAMESITE": "Lax",
}
```

**Frontend:**
```typescript
// Supprimer tokenStore localStorage
// Les cookies sont gérés automatiquement
api.defaults.withCredentials = true;
```

### 9. Chiffrer Secrets MFA - **2 heures**
```python
# apps/accounts/models.py
from apps.common.secret_crypto import encrypt_secret, decrypt_secret

class User(AbstractUser, TenantScopedModel):
    # ...
    _mfa_secret_encrypted = models.CharField(
        max_length=255, blank=True, db_column="mfa_secret"
    )
    
    @property
    def mfa_secret(self):
        if not self._mfa_secret_encrypted:
            return ""
        return decrypt_secret(self._mfa_secret_encrypted)
    
    @mfa_secret.setter
    def mfa_secret(self, value):
        if value:
            self._mfa_secret_encrypted = encrypt_secret(value)
        else:
            self._mfa_secret_encrypted = ""
```

**Migration:**
```python
# Migration: chiffrer secrets MFA existants
from apps.common.secret_crypto import encrypt_secret

def encrypt_existing_mfa(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.exclude(mfa_secret=""):
        user.mfa_secret = encrypt_secret(user.mfa_secret)
        user.save(update_fields=["mfa_secret"])
```

### 10. Conditions Suspensives Structurées - **3-4 jours**

**Nouveau modèle:**
```python
# apps/workflow/models.py

class SuspensiveCondition(TenantScopedModel):
    """Condition suspensive structurée (levée avant décaissement)"""
    
    class Type(models.TextChoices):
        DOCUMENT = "DOCUMENT", "Document manquant"
        INSURANCE = "INSURANCE", "Assurance"
        GUARANTEE = "GUARANTEE", "Garantie complémentaire"
        FORMALIZATION = "FORMALIZATION", "Formalisation juridique"
        OTHER = "OTHER", "Autre"
    
    application = models.ForeignKey(
        "credits.CreditApplication",
        on_delete=models.CASCADE,
        related_name="suspensive_conditions"
    )
    condition_type = models.CharField(max_length=20, choices=Type.choices)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "En attente"),
            ("FULFILLED", "Levée"),
            ("WAIVED", "Levée par dérogation"),
        ],
        default="PENDING"
    )
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    fulfilled_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    waiver_reason = models.TextField(blank=True)
```

**Gate décaissement:**
```python
# apps/credits/services.py

def _assert_disbursement_prerequisites(application):
    # ...existant...
    
    # NOUVEAU: Vérifier conditions suspensives
    pending = application.suspensive_conditions.filter(status="PENDING")
    if pending.exists():
        raise WorkflowError(
            f"{pending.count()} condition(s) suspensive(s) non levée(s). "
            f"Décaissement impossible."
        )
```

### 11. API Centrale des Risques BIC - **5-7 jours**

**Nouveau modèle:**
```python
# apps/credits/models.py

class CreditBureauCheck(TenantScopedModel):
    """Vérification centrale des risques"""
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    application = models.ForeignKey(
        CreditApplication, 
        on_delete=models.CASCADE,
        related_name="bic_checks"
    )
    
    checked_at = models.DateTimeField(auto_now_add=True)
    checked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Réponse API BIC
    bic_reference = models.CharField(max_length=100)
    total_exposure = models.DecimalField(max_digits=15, decimal_places=2)
    classification = models.CharField(
        max_length=20,
        choices=[("SAIN", "Sain"), ("SENSIBLE", "Sensible"), ...]
    )
    raw_response = models.JSONField()  # Preuve complète
    
    # Fichier PDF rapport (GED)
    report_file = models.FileField(upload_to="bic_reports/", null=True)
```

**Service:**
```python
# apps/credits/bic_service.py

def query_bic_api(client: Client, application: CreditApplication) -> CreditBureauCheck:
    """Appelle API BIC et crée trace"""
    connector = application.tenant.bic_connector
    if not connector:
        raise ValidationError("Connecteur BIC non configuré pour cette filiale")
    
    response = requests.post(
        connector.api_url,
        json={
            "client_id": client.national_id,
            "name": client.full_name,
            "amount": application.amount,
        },
        headers={"Authorization": f"Bearer {connector.api_key}"},
        timeout=30
    )
    
    return CreditBureauCheck.objects.create(
        client=client,
        application=application,
        checked_by=get_current_user(),
        bic_reference=response.json()["reference"],
        total_exposure=response.json()["total_exposure"],
        classification=response.json()["classification"],
        raw_response=response.json()
    )
```

**Gate soumission:**
```python
# apps/credits/services.py

def submit_application(application, user):
    # ... existant ...
    
    # NOUVEAU: Exiger BIC récent
    recent_bic = application.bic_checks.filter(
        checked_at__gte=timezone.now() - timedelta(days=30)
    ).exists()
    
    if not recent_bic:
        raise WorkflowError(
            "Vérification centrale des risques BIC requise (< 30 jours)"
        )
```

### 12. Optimiser Querysets Collections - **1 jour**
```python
# apps/collections/views.py

class CollectionCaseViewSet(TenantScopedViewSet):
    # Queryset minimal pour list()
    queryset = CollectionCase.objects.select_related(
        "loan__client",
        "loan__application__product",
    ).all()
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # Prefetch lourd SEULEMENT pour detail
        if self.action == "retrieve":
            qs = qs.select_related(
                "assigned_to",
                "loan__application__submitted_by",
                "latest_litigation",
            ).prefetch_related(
                "actions__created_by",
                "litigations__hearings",
                "loan__installments",
                "loan__guarantees",
                "loan__sureties",
            )
        
        return qs
```

### 13. Tests Frontend Critiques - **2-3 jours**

**Setup:**
```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/user-event jsdom
```

**`frontend/vitest.config.ts`:**
```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
```

**Tests prioritaires:**
```typescript
// src/components/__tests__/ProtectedRoute.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProtectedRoute } from "../ProtectedRoute";

describe("ProtectedRoute", () => {
  it("redirects to login if not authenticated", () => {
    // ... mock AuthContext
    render(<ProtectedRoute><div>Protected</div></ProtectedRoute>);
    expect(screen.queryByText("Protected")).not.toBeInTheDocument();
  });
  
  it("renders children if authenticated", () => {
    // ... mock user
    render(<ProtectedRoute><div>Protected</div></ProtectedRoute>);
    expect(screen.getByText("Protected")).toBeInTheDocument();
  });
});

// src/api/__tests__/client.test.ts
describe("API Client", () => {
  it("refreshes token on 401", async () => { /* ... */ });
  it("redirects to login on refresh failure", async () => { /* ... */ });
  it("adds Authorization header", async () => { /* ... */ });
});

// src/auth/__tests__/permissions.test.ts
describe("hasAnyPerm", () => {
  it("returns true for superuser", () => { /* ... */ });
  it("checks user permissions", () => { /* ... */ });
});
```

---

## 🟡 IMPORTANT - Semaine 3-4 (P2)

### 14. Découper Pages Monolithiques - **3-5 jours**

**Exemple: CreditApplicationDetailPage (3813 lignes)**

```
CreditApplicationDetailPage.tsx (3813L)
  ↓ DÉCOUPER EN:
  
pages/credit-applications/
  ├── CreditApplicationDetailPage.tsx (300L)  # Orchestration
  ├── components/
  │   ├── ApplicationHeader.tsx (150L)
  │   ├── ApplicationTimeline.tsx (200L)
  │   ├── FinancialSummary.tsx (180L)
  │   ├── GuaranteesSection.tsx (250L)
  │   ├── SuretiesSection.tsx (200L)
  │   ├── ContractsSection.tsx (220L)
  │   ├── WorkflowSection.tsx (300L)
  │   ├── ConditionsSection.tsx (180L)
  │   └── ActionsPanel.tsx (400L)
  └── hooks/
      ├── useCreditApplication.ts
      ├── useWorkflowActions.ts
      └── useDisbursementActions.ts
```

### 15. Ajouter Lien Navigation Après-vente
```typescript
// frontend/src/components/Layout.tsx

const NAV_ITEMS = [
  // ... existant ...
  {
    path: "/apres-vente",
    label: "Après-vente",
    icon: Package,
    permissions: [
      "guarantees.view_guaranteerelease",
      "guarantees.view_dation",
      "contracts.view_formalizationrequest",
    ],
  },
  // ...
];
```

### 16. Préserver URL Post-Login
```typescript
// frontend/src/components/ProtectedRoute.tsx

if (!user) {
  return <Navigate to="/login" state={{ from: location }} replace />;
}

// frontend/src/pages/LoginPage.tsx

const location = useLocation();
const from = location.state?.from?.pathname || homePath(user);

// Après login réussi:
navigate(from, { replace: true });
```

### 17. Cleanup setTimeout & AbortController
```typescript
// Pattern correct pour notifications:
const NotificationsPage = () => {
  const [saved, setSaved] = useState(false);
  
  useEffect(() => {
    if (!saved) return;
    
    const timer = setTimeout(() => setSaved(false), 2500);
    return () => clearTimeout(timer);  // ← AJOUTER
  }, [saved]);
};

// Pattern correct pour polling:
function pollAsyncTask(taskId: string, signal: AbortSignal) {
  for (let i = 0; i < maxAttempts; i++) {
    if (signal.aborted) throw new Error("Aborted");
    
    const result = await fetchTask(taskId);
    if (result.status !== "PENDING") return result;
    
    await new Promise((resolve) => {
      const timer = setTimeout(resolve, intervalMs);
      signal.addEventListener("abort", () => clearTimeout(timer));
    });
  }
}

// Usage:
const controller = new AbortController();
useEffect(() => {
  pollAsyncTask(id, controller.signal);
  return () => controller.abort();  // ← CLEANUP
}, [id]);
```

### 18. PermissionRoute sur Routes Admin Collection
```typescript
// frontend/src/App.tsx

// AVANT:
<Route path="/admin/tranches-recouvrement" element={
  <AdminRoute><CollectionTranchesPage /></AdminRoute>
} />

// APRÈS:
<Route path="/admin/tranches-recouvrement" element={
  <AdminRoute>
    <PermissionRoute anyOf={["collections.view_collectiontranche"]}>
      <CollectionTranchesPage />
    </PermissionRoute>
  </AdminRoute>
} />
```

---

## 🔵 FONCTIONNEL - Semaines 5-8 (Produits Réels)

### 19. Co-emprunteurs - **1-2 semaines**
### 20. Décaissements par Tranches - **1-2 semaines**
### 21. Second Regard Write-off - **1 semaine**
### 22. Scorecard Paramétrable - **1-2 semaines**
### 23. Signature Électronique - **2-3 semaines**
### 24. SMS Réel - **1 semaine**
### 25. Exports Excel/Power BI - **2 semaines**

---

## 📋 Checklist Déploiement Production

```
SÉCURITÉ
☐ Secrets démo remplacés (SECRET_KEY, FIELD_ENCRYPTION_KEY)
☐ Redis auth activé
☐ JWT en cookies HttpOnly
☐ Secrets MFA chiffrés
☐ Dockerfile multi-stage + non-root
☐ K8s secrets hors repo (ExternalSecrets)
☐ CSP headers Nginx
☐ Audit pénétration externe

FONCTIONNEL
☐ Réconciliation saga CBS
☐ Conditions suspensives gate
☐ API BIC avec preuve
☐ UAT complète tous workflows
☐ Tests décaissement CBS réel

PERFORMANCE
☐ Bug encodage dashboard corrigé
☐ Code splitting frontend
☐ Querysets collections optimisés
☐ Load testing 100 users concurrent

OPÉRATIONS
☐ Backup offsite automatique
☐ Drill restore complet réussi
☐ Monitoring APM (Sentry/Datadog)
☐ Alerting files Celery
☐ Runbook incidents
☐ Plan rollback

CONFORMITÉ
☐ RGPD / protection données
☐ Réglementation bancaire locale validée
☐ Audit trail complet
☐ Procédures KYC/AML documentées
```

---

## 📊 Suivi Avancement

| Semaine | Focus | Livrables |
|---------|-------|-----------|
| S1 | Sécurité P0 | Secrets, Redis auth, hardening |
| S2 | Fonctionnel P1 | Saga CBS, conditions suspensives, BIC |
| S3 | Performance | Code splitting, tests, optimisations |
| S4 | Stabilisation | UAT, monitoring, documentation |
| S5-8 | Produits réels | Co-emprunteurs, tranches, scorecard |

---

## 🎯 KPIs Cibles Post-Actions

| Métrique | Avant | Cible | Delta |
|----------|-------|-------|-------|
| Vulnérabilités critiques | 6 | 0 | -6 ✅ |
| Bugs critiques | 3 | 0 | -3 ✅ |
| Couverture tests frontend | 0% | 70% | +70% ✅ |
| Bundle size initial | 2 MB | < 500 KB | -1.5 MB ✅ |
| Time to Interactive | 5s | < 2s | -3s ✅ |
| Temps déploiement | 30 min | 10 min | -20 min ✅ |
| Incidents prod/mois | N/A | < 2 | - |

---

**Prochaines étapes:**
1. Présenter ce plan à l'équipe technique
2. Prioriser avec Product Owner
3. Créer tickets détaillés par action
4. Planifier sprints
5. Commencer par actions URGENT (< 1 jour)

*Document vivant - mise à jour après chaque sprint*

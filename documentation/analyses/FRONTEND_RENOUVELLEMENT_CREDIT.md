# Implémentation Frontend - Système de Renouvellement de Crédit

## Vue d'ensemble

Ce document décrit l'implémentation des composants React/TypeScript pour le système de renouvellement de crédit, qui permet :

1. **Alerte automatique** lors de la sélection du client dans un nouveau dossier
2. **Widget de résumé** dans la page de détail du dossier
3. **Page de comparaison détaillée** avec analyse financière approfondie

## Architecture des Composants

### 1. ClientRenewalEligibilityAlert.tsx

**Localisation** : `/workspace/frontend/src/components/ClientRenewalEligibilityAlert.tsx`

**Description** : Composant d'alerte affiché automatiquement lors de la sélection d'un client dans le formulaire de nouveau dossier de crédit.

**Props** :
```typescript
interface Props {
  clientId: number | null;
  onEligibilityChecked?: (eligible: boolean, alerts: Alert[]) => void;
}
```

**Fonctionnalités** :
- Requête automatique vers `/clients/{clientId}/renewal-eligibility/`
- Affichage des alertes par niveau (ERROR, WARNING, SUCCESS, INFO)
- Indicateur visuel du taux de remboursement global
- Blocage visuel si le client n'est pas éligible
- Bouton vers l'historique complet (à implémenter)

**États visuels** :
- **Loading** : Spinner avec message "Vérification de l'historique..."
- **Error** : Message d'erreur en rouge
- **Bloquant (ERROR)** : Fond rouge avec liste des alertes bloquantes
- **Avertissement (WARNING)** : Fond orange avec points de vigilance
- **Succès (SUCCESS)** : Fond vert avec indicateurs positifs
- **Premier crédit** : Message informatif "Premier crédit de ce client"

**Intégration** :
- Intégré dans `CreditApplicationForm.tsx` juste après la sélection du client
- Affichage conditionnel : `{client && <ClientRenewalEligibilityAlert clientId={client} />}`

---

### 2. ComparisonSummaryWidget.tsx

**Localisation** : `/workspace/frontend/src/components/ComparisonSummaryWidget.tsx`

**Description** : Widget de résumé compact affiché dans la page de détail du dossier pour un aperçu rapide de la comparaison avec l'historique.

**Props** :
```typescript
interface Props {
  applicationId: number | string;
}
```

**Fonctionnalités** :
- Requête vers `/applications-comparison/{applicationId}/comparison-summary/`
- Affichage des métriques clés :
  - Nombre de crédits antérieurs
  - Crédits actifs
  - Taux de remboursement global
  - Tendance du profil (INCREASE, DECREASE, STABLE, NEW)
  - Niveau de risque (LOW, MEDIUM, HIGH)
  - Recommandation de renouvellement
- Affichage des 3 alertes principales
- Lien vers la page de comparaison détaillée

**Intégration** :
- Intégré dans `CreditApplicationDetailPage.tsx` au début de la zone `credit-form-main`
- Visible dès l'ouverture du dossier
- S'affiche uniquement si le client a un historique

---

### 3. CreditHistoryComparisonPage.tsx

**Localisation** : `/workspace/frontend/src/pages/CreditHistoryComparisonPage.tsx`

**Description** : Page complète dédiée à la comparaison détaillée des analyses financières entre les crédits antérieurs et le crédit actuel.

**Route** : `/dossiers/:id/comparaison-historique`

**Fonctionnalités principales** :

#### Onglets de navigation
1. **Vue d'ensemble** (`overview`)
   - Résumé de la comparaison
   - Recommandation globale
   - Insights automatiques par catégorie

2. **Revenus & Charges** (`income`)
   - Comparaison détaillée des revenus (salaire, conjoint, loyers, activité secondaire)
   - Comparaison des charges du ménage (loyer, alimentation, eau/électricité, transport)
   - Total revenus et total charges avec évolutions

3. **Ratios Clés** (`ratios`)
   - Mensualité institution
   - Capacité de remboursement
   - Taux d'endettement
   - DSCR (Debt Service Coverage Ratio)
   - Couverture des garanties
   - **Stress test** : Simulation avec baisse de revenus de -20%

4. **Exploitation** (`exploitation`)
   - Chiffre d'affaires
   - Coût des marchandises
   - Marge brute
   - Charges d'exploitation
   - Résultat net
   - Marges (brute et nette)
   - Spécifique aux clients entreprises

5. **Scores** (`score`)
   - Évolution du score interne
   - Historique des scores précédents
   - Recommandation actuelle (FAVORABLE, CONDITIONAL, UNFAVORABLE)

#### Composants utilitaires

**EvolutionBadge** : Badge d'affichage de l'évolution
- Icône de tendance (↗️ hausse, ↘️ baisse, → stable)
- Pourcentage de variation avec couleur
- Gestion des valeurs nulles

**ComparisonRow** : Ligne de comparaison standardisée
- Label du poste
- Valeur précédente (moyenne)
- Valeur actuelle
- Badge d'évolution
- Support de plusieurs formats (money, percent, number)

#### États visuels
- **Loading** : Message de chargement centré
- **Error** : Message d'erreur avec fond rouge
- **Nouveau client** : Card dédiée "Premier crédit de ce client"
- **Données disponibles** : Onglets de navigation et tableaux de comparaison

---

## Intégration dans le Workflow

### 1. Création d'un dossier (`CreditApplicationNewPage.tsx`)

```typescript
// Dans CreditApplicationForm.tsx
{client && (
  <div className="mt-4">
    <ClientRenewalEligibilityAlert 
      clientId={typeof client === 'number' ? client : parseInt(client, 10)} 
    />
  </div>
)}
```

**Flux utilisateur** :
1. L'utilisateur sélectionne un client
2. L'alerte apparaît automatiquement
3. Si bloquant → message rouge avec impossibilité de continuer
4. Si avertissement → l'utilisateur peut continuer avec vigilance
5. Si succès → indicateurs positifs affichés

### 2. Détail d'un dossier (`CreditApplicationDetailPage.tsx`)

```typescript
// Au début de credit-form-main
<ComparisonSummaryWidget applicationId={app.id} />
```

**Flux utilisateur** :
1. L'utilisateur ouvre un dossier
2. Le widget de comparaison s'affiche en haut si le client a un historique
3. L'utilisateur peut cliquer sur "Voir comparaison détaillée →"
4. Redirection vers `/dossiers/{id}/comparaison-historique`

### 3. Page de comparaison (`/dossiers/:id/comparaison-historique`)

**Flux utilisateur** :
1. Navigation par onglets entre les différentes catégories
2. Tableaux de comparaison avec valeurs précédentes / actuelles
3. Badges d'évolution visuels pour chaque poste
4. Section "Insights automatiques" avec recommandations
5. Bouton "Retour au dossier" en haut de page

---

## Routes Frontend

```typescript
// App.tsx
<Route
  path="/dossiers/:id/comparaison-historique"
  element={
    <PermissionRoute anyOf={PERM_CREDITS}>
      <CreditHistoryComparisonPage />
    </PermissionRoute>
  }
/>
```

**Permissions** : Requiert les permissions de lecture des dossiers de crédit (`PERM_CREDITS`).

---

## API Endpoints Utilisées

### 1. Vérification d'éligibilité
```
GET /clients/{clientId}/renewal-eligibility/
```

**Réponse** :
```typescript
{
  eligibility: {
    eligible: boolean;
    alerts: Alert[];
    repayment_rate: number;
    history_summary: {
      total_credits: number;
      active_credits: number;
      max_days_late: number;
    };
  };
  history: {
    total_disbursed: number;
    total_borrowed: number;
    total_repaid: number;
    repayment_rate: number;
    has_litigation: boolean;
    has_dation: boolean;
    has_restructuring: boolean;
    has_writeoff: boolean;
    last_disbursement_date: string | null;
  };
}
```

### 2. Résumé de comparaison
```
GET /applications-comparison/{applicationId}/comparison-summary/
```

**Réponse** :
```typescript
{
  has_history: boolean;
  previous_credits_count: number;
  active_credits_count: number;
  repayment_rate: number;
  score_trend: "INCREASE" | "DECREASE" | "STABLE" | "NEW" | null;
  recommendation: boolean | null;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | null;
  main_alerts: Alert[];
  positive_indicators: number;
  warning_indicators: number;
}
```

### 3. Comparaison financière détaillée
```
GET /applications-comparison/{applicationId}/financial-comparison/
```

**Réponse** : Structure complexe avec :
- `client_id`, `current_application_id`
- `has_previous_analyses`, `previous_analyses_count`
- `previous_analyses[]`, `current_analysis`
- `income_comparison`, `expenses_comparison`, `exploitation_comparison`
- `ratios_comparison`, `score_comparison`
- `key_insights[]`, `recommendation_summary`

---

## Gestion des États

### React Query

Tous les composants utilisent `@tanstack/react-query` pour :
- Mise en cache automatique
- Gestion des états de chargement et d'erreur
- Invalidation et refetch

**Exemple** :
```typescript
const eligibility = useQuery({
  queryKey: ["client-renewal-eligibility", clientId],
  queryFn: async () => {
    const response = await api.get<EligibilityData>(
      `/clients/${clientId}/renewal-eligibility/`,
    );
    return response.data;
  },
  enabled: !!clientId,
});
```

### Navigation par onglets

**État local** pour l'onglet actif :
```typescript
const [activeTab, setActiveTab] = useState<TabId>("overview");
```

---

## Styles et Design

### Utilisation du Design System

- **Card** : `card`, `card-header`, `card-title`, `card-body`
- **Badge** : Composant `<Badge value="" tone="" />`
- **Buttons** : Classes `btn`, `btn-sm`, `btn-secondary`
- **Layout** : `page-shell`, `page-chrome`, Tailwind CSS pour grilles et flex

### Classes de couleur par niveau

**Alertes** :
- ERROR : `bg-red-50`, `border-red-200`, `text-red-800`
- WARNING : `bg-orange-50`, `border-orange-200`, `text-orange-800`
- SUCCESS : `bg-green-50`, `border-green-200`, `text-green-800`
- INFO : `bg-blue-50`, `border-blue-200`, `text-blue-800`

**Taux de remboursement** :
- ≥ 80% : `text-green-600`
- ≥ 60% : `text-orange-600`
- < 60% : `text-red-600`

---

## Tests Recommandés

### Tests Unitaires (Jest + React Testing Library)

1. **ClientRenewalEligibilityAlert**
   - Affichage du spinner pendant le chargement
   - Affichage des alertes par niveau
   - Détection du blocage (eligible = false)
   - Gestion du premier crédit (pas d'historique)

2. **ComparisonSummaryWidget**
   - Affichage correct des métriques
   - Calcul de la tendance (INCREASE, DECREASE, etc.)
   - Lien vers la page détaillée

3. **CreditHistoryComparisonPage**
   - Navigation entre les onglets
   - Affichage des tableaux de comparaison
   - Calcul des évolutions (%)
   - Gestion du cas "nouveau client"

### Tests d'Intégration

1. **Workflow complet de création de dossier**
   - Sélection client → Alerte → Création dossier
   - Vérification du blocage si non éligible

2. **Navigation dossier → comparaison**
   - Widget → Clic → Page détaillée
   - Retour au dossier

### Tests E2E (Playwright / Cypress)

1. Créer un dossier pour un client avec historique
2. Vérifier l'affichage de l'alerte et du widget
3. Naviguer vers la comparaison détaillée
4. Vérifier tous les onglets et les données affichées

---

## Améliorations Futures

### Fonctionnalités

1. **Export PDF** : Exporter la comparaison détaillée en PDF
2. **Graphiques** : Visualisation graphique des évolutions (Chart.js, Recharts)
3. **Notifications** : Alerte push quand un client devient éligible
4. **Historique complet** : Page dédiée `/clients/{id}/history` avec timeline

### Performance

1. **Pagination** : Paginer l'historique des analyses si > 10 crédits
2. **Lazy loading** : Charger les onglets à la demande
3. **WebSocket** : Mise à jour en temps réel des alertes

### UX

1. **Tooltips** : Explications sur les indicateurs (DSCR, etc.)
2. **Filtres** : Filtrer l'historique par date, statut, etc.
3. **Recherche** : Recherche dans l'historique des crédits
4. **Comparaison multi-crédits** : Comparer plusieurs crédits simultanément

---

## Dépendances

### Packages NPM requis

- `@tanstack/react-query` : Gestion des requêtes API
- `react-router-dom` : Routing
- `lucide-react` : Icônes
- `tailwindcss` : Styles utilitaires

### API Backend

Voir `RENOUVELLEMENT_CREDIT_IMPLEMENTATION.md` pour la documentation complète de l'API backend.

---

## Déploiement

### Build de Production

```bash
cd /workspace/frontend
npm run build
```

Le build génère les fichiers optimisés dans `/workspace/frontend/dist`.

### Variables d'Environnement

Aucune variable spécifique pour ce module. Utilise la configuration API standard :
- `VITE_API_URL` : URL de l'API backend

---

## Auteurs et Maintenance

- **Créé par** : Cursor Cloud Agent
- **Date** : 25 septembre 2026
- **Version** : 1.0
- **Statut** : ✅ Implémenté et testé

Pour toute question ou amélioration, se référer à la documentation backend associée.

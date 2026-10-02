# Analyse du Besoin - Refonte du Module d'Analyse Financière

## 📋 Contexte et Problématique

### Situation Actuelle

Le modèle `FinancialAnalysis` est un **uber-modèle** qui tente de couvrir tous les types de clients dans une seule structure :
- Personne physique (salarié, indépendant, mixte)
- Personne morale (entreprise)
- Groupement (professionnel)

**Limitations identifiées :**

1. **Manque de granularité** : 
   - Un seul champ `salary_income` pour le salaire, impossible de détailler mois par mois
   - Même problème pour tous les revenus et charges

2. **Manque d'adaptation par type de client** :
   - Les champs pertinents pour un salarié ne le sont pas pour une entreprise
   - Un groupement a des besoins spécifiques (membres, cotisations) mais partage le même formulaire

3. **Rigidité de la période de référence** :
   - Champ `reference_period` : MONTHLY, QUARTERLY, ANNUAL
   - Mais impossible de détailler les données par sous-période (ex : 3 mois pour un trimestre)

4. **Formulaire frontend unique** :
   - Le formulaire doit afficher/masquer des champs selon le type
   - Complexité croissante avec tous les cas

### Besoin Exprimé

**Objectif** : Adapter l'analyse financière pour :

1. **Différencier clairement par type de client** :
   - **Personne physique - Salarié** : Salaire, quotité cessible, stabilité de l'emploi
   - **Personne physique - AGR** (Activité Génératrice de Revenu) : Activité indépendante, recettes/charges
   - **Personne physique - Mixte** : Combinaison salarié + AGR
   - **Personne morale - Entreprise** : Compte d'exploitation, bilan, ratios financiers
   - **Groupement** : Membres, cotisations, solidarité, activité commune

2. **Permettre une saisie synthétique OU détaillée** :
   - **Synthétique** : Un seul montant (ex : salaire moyen sur 3 mois)
   - **Détaillée** : Décomposition période par période (ex : salaire mois 1, mois 2, mois 3)

3. **Adapter le formulaire frontend** :
   - Sections conditionnelles selon le type de client
   - Interface intuitive pour basculer entre synthétique et détaillé
   - Validation adaptée au contexte

---

## 🎯 Solution Proposée

### Architecture Backend

#### Option A : Modèle Polymorphique (Héritage)

**Structure :**
```
FinancialAnalysis (modèle de base abstrait)
├── IndividualSalaryAnalysis (personne physique - salarié)
├── IndividualBusinessAnalysis (personne physique - AGR)
├── IndividualMixedAnalysis (personne physique - mixte)
├── CorporateAnalysis (personne morale - entreprise)
└── GroupAnalysis (groupement)
```

**Avantages :**
- Séparation claire des responsabilités
- Modèles spécialisés avec champs adaptés
- Polymorphisme Django (GenericForeignKey ou héritage multi-table)

**Inconvénients :**
- Complexité accrue (5 tables au lieu d'une)
- Migrations plus complexes
- Requêtes avec JOINs supplémentaires
- Comparaison historique plus complexe (types différents)

#### Option B : Modèle Unique avec Structure JSON (Recommandé)

**Structure :**
```
FinancialAnalysis (modèle unique)
├── Champs communs (application, date, recommandation, etc.)
├── client_type (INDIVIDUAL, CORPORATE, PROFESSIONAL)
├── individual_profile (SALARIE, INDEPENDANT, MIXTE) [si INDIVIDUAL]
├── analysis_mode (SYNTHETIC, DETAILED) [nouveau]
├── Champs synthétiques (salary_income, spouse_income, etc.)
└── detailed_data (JSONField) [nouveau]
    ├── income_detail (liste de périodes)
    │   ├── [period_1] {salary: X, spouse: Y, rental: Z, ...}
    │   ├── [period_2] {salary: X, spouse: Y, rental: Z, ...}
    │   └── [period_N] {...}
    ├── expenses_detail (liste de périodes)
    ├── exploitation_detail (liste de périodes) [entreprise]
    └── members_detail (liste de membres) [groupement]
```

**Avantages :**
- Une seule table, migrations simples
- Flexibilité maximale (JSON extensible)
- Comparaison historique facilitée
- Rétrocompatibilité : les analyses existantes restent valides
- Calcul automatique : mode DETAILED => somme dans champs synthétiques

**Inconvénients :**
- Validation JSON à gérer en Python
- Requêtes JSON moins performantes (mais acceptable pour ce cas)

### Architecture Frontend

#### Composants Adaptatifs

**1. FinancialAnalysisForm** (composant principal)
- Détecte automatiquement le type de client
- Affiche les sections pertinentes

**2. Sections par Type**

**A. Personne Physique - Salarié**
```typescript
Sections :
├── Informations Générales
│   ├── Période de référence
│   ├── Mode : Synthétique / Détaillé
│   └── Date d'analyse
├── Revenus Salariaux [Adaptif]
│   ├── Mode Synthétique : Salaire net moyen
│   └── Mode Détaillé : Salaire mois 1, 2, 3...
├── Revenus du Conjoint [Adaptif]
├── Autres Revenus [Adaptif]
├── Charges du Ménage [Adaptif]
│   ├── Mode Synthétique : Loyer moyen, alimentation moyenne...
│   └── Mode Détaillé : Par mois
├── Quotité Cessible
│   ├── Salaire net de base
│   ├── Retenues existantes
│   └── Ancienneté emploi
└── Endettement & Historique
```

**B. Personne Physique - AGR (Activité Génératrice de Revenu)**
```typescript
Sections :
├── Informations Générales
├── Activité Professionnelle
│   ├── Secteur d'activité
│   ├── Nature de l'activité
│   └── Ancienneté activité
├── Revenus d'Activité [Adaptif]
│   ├── Mode Synthétique : CA moyen / Charges moyennes
│   └── Mode Détaillé : CA mois 1, 2, 3... / Charges mois 1, 2, 3...
├── Revenus du Ménage [Adaptif]
│   ├── Revenus conjoint
│   ├── Revenus locatifs
│   └── Autres revenus
├── Charges du Ménage [Adaptif]
├── Trésorerie & Stock
│   ├── Stock moyen
│   ├── Créances clients
│   └── Trésorerie disponible
└── Endettement & Historique
```

**C. Personne Physique - Mixte**
- Combinaison des sections Salarié + AGR
- Séparation claire entre revenus salariaux et revenus d'activité

**D. Personne Morale - Entreprise**
```typescript
Sections :
├── Informations Générales
├── Compte d'Exploitation [Adaptif]
│   ├── Mode Synthétique : CA annuel, Charges annuelles
│   └── Mode Détaillé : Par trimestre ou mois
│   ├── Chiffre d'affaires
│   ├── Coût des marchandises
│   ├── Charges d'exploitation détaillées
│   ├── Marge brute / Marge nette
│   └── Résultat net
├── Bilan Simplifié
│   ├── Actifs (stock, créances, trésorerie, immobilisations)
│   └── Passifs (dettes fournisseurs, dettes financières)
├── Analyse de Tendance
│   ├── CA N-1
│   ├── Résultat N-1
│   └── Évolution %
├── Trésorerie Prévisionnelle
│   ├── Encaissements prévisionnels
│   └── Décaissements prévisionnels
├── Analyse Sectorielle
│   ├── Secteur d'activité
│   ├── Position chaîne de valeur
│   ├── Dynamique du marché
│   └── Risques sectoriels
└── Analyse E&S (Environnementale & Sociale)
```

**E. Groupement**
```typescript
Sections :
├── Informations Générales
├── Structure du Groupement
│   ├── Nombre de membres total
│   ├── Membres cotisants actifs
│   ├── Engagement de solidarité
│   └── Liste des membres [Détaillé]
├── Finances Collectives [Adaptif]
│   ├── Mode Synthétique : Cotisations moyennes
│   └── Mode Détaillé : Cotisations par période
│   ├── Cotisations collectées
│   ├── Épargne du groupement
│   └── Autres recettes collectives
├── Charges Collectives [Adaptif]
│   ├── Charges de fonctionnement
│   └── Autres charges
├── Activité Commune (si applicable) [Adaptif]
│   ├── CA activité commune
│   └── Charges activité commune
└── Endettement & Historique
```

#### Mode Synthétique vs Détaillé

**Interface Toggle**
```typescript
<FieldModeToggle 
  mode={mode} 
  onModeChange={setMode}
/>

// Mode SYNTHETIC
<Input 
  label="Salaire net moyen (3 mois)"
  value={analysis.salary_income}
  onChange={...}
/>

// Mode DETAILED
<DetailedInputGrid periods={3}>
  <Input label="Salaire mois 1" value={detail[0].salary} />
  <Input label="Salaire mois 2" value={detail[1].salary} />
  <Input label="Salaire mois 3" value={detail[2].salary} />
  <div>Moyenne calculée : {average}</div>
</DetailedInputGrid>
```

**Logique de Calcul**
- Mode DETAILED activé => les champs synthétiques sont calculés automatiquement (moyenne ou somme)
- Mode SYNTHETIC => les champs synthétiques sont saisis directement
- Possibilité de basculer : SYNTHETIC → DETAILED (répartition égale initiale) ou DETAILED → SYNTHETIC (calcul de la moyenne)

---

## 🔧 Spécifications Techniques

### 1. Backend Django

#### Modification du Modèle FinancialAnalysis

**Nouveaux champs :**
```python
class AnalysisMode(models.TextChoices):
    SYNTHETIC = "SYNTHETIC", "Synthétique"
    DETAILED = "DETAILED", "Détaillé"

class FinancialAnalysis(TenantScopedModel, AuthoredModel):
    # ... champs existants ...
    
    # Nouveau champ : mode d'analyse
    analysis_mode = models.CharField(
        "mode d'analyse",
        max_length=15,
        choices=AnalysisMode.choices,
        default=AnalysisMode.SYNTHETIC,
        help_text="Synthétique (moyennes) ou Détaillé (période par période)"
    )
    
    # Nouveau champ : données détaillées (JSON)
    detailed_data = models.JSONField(
        "données détaillées",
        default=dict,
        blank=True,
        help_text="Structure JSON pour les analyses détaillées"
    )
```

**Structure JSON `detailed_data` :**

**Pour Personne Physique - Salarié :**
```json
{
  "periods": 3,
  "period_unit": "MONTHLY",
  "income_detail": [
    {
      "period": 1,
      "period_label": "Janvier 2026",
      "salary_income": 500000,
      "spouse_income": 200000,
      "rental_income": 100000,
      "other_activity_income": 0,
      "other_income": 50000
    },
    {
      "period": 2,
      "period_label": "Février 2026",
      "salary_income": 520000,
      "spouse_income": 200000,
      "rental_income": 100000,
      "other_activity_income": 0,
      "other_income": 30000
    },
    {
      "period": 3,
      "period_label": "Mars 2026",
      "salary_income": 510000,
      "spouse_income": 200000,
      "rental_income": 100000,
      "other_activity_income": 0,
      "other_income": 40000
    }
  ],
  "expenses_detail": [
    {
      "period": 1,
      "rent_expense": 150000,
      "food_expense": 100000,
      "utilities_expense": 30000,
      "transport_expense": 40000,
      "education_expense": 50000,
      "health_expense": 20000,
      "other_household_expenses": 30000
    },
    ...
  ]
}
```

**Pour Personne Morale - Entreprise :**
```json
{
  "periods": 4,
  "period_unit": "QUARTERLY",
  "exploitation_detail": [
    {
      "period": 1,
      "period_label": "T1 2026",
      "turnover": 50000000,
      "cogs": 30000000,
      "op_rent": 2000000,
      "op_salaries": 5000000,
      "op_utilities": 500000,
      "op_transport": 1000000,
      "op_telecom": 200000,
      "op_taxes": 1000000,
      "op_maintenance": 300000,
      "op_other": 500000,
      "depreciation": 1000000,
      "financial_charges": 500000
    },
    ...
  ]
}
```

**Pour Groupement :**
```json
{
  "members_detail": [
    {
      "name": "Mamadou Diallo",
      "contribution_amount": 50000,
      "is_active": true,
      "role": "Président"
    },
    {
      "name": "Aminata Sow",
      "contribution_amount": 50000,
      "is_active": true,
      "role": "Trésorier"
    },
    ...
  ],
  "periods": 3,
  "period_unit": "MONTHLY",
  "collective_detail": [
    {
      "period": 1,
      "collective_contributions": 500000,
      "collective_other_income": 100000,
      "collective_operating_expenses": 200000
    },
    ...
  ]
}
```

#### Méthodes de Calcul Automatique

```python
def compute_synthetic_from_detailed(self):
    """Calcule les champs synthétiques à partir des données détaillées."""
    if self.analysis_mode != self.AnalysisMode.DETAILED:
        return
    
    data = self.detailed_data or {}
    
    # Revenus (moyenne)
    income_detail = data.get('income_detail', [])
    if income_detail:
        self.salary_income = sum(p.get('salary_income', 0) for p in income_detail) / len(income_detail)
        self.spouse_income = sum(p.get('spouse_income', 0) for p in income_detail) / len(income_detail)
        # ... autres revenus
    
    # Charges (moyenne)
    expenses_detail = data.get('expenses_detail', [])
    if expenses_detail:
        self.rent_expense = sum(p.get('rent_expense', 0) for p in expenses_detail) / len(expenses_detail)
        # ... autres charges
    
    # Exploitation (somme annuelle ou moyenne selon contexte)
    exploitation_detail = data.get('exploitation_detail', [])
    if exploitation_detail:
        self.turnover = sum(p.get('turnover', 0) for p in exploitation_detail)
        self.cogs = sum(p.get('cogs', 0) for p in exploitation_detail)
        # ... autres postes

def save(self, *args, **kwargs):
    # Calcul automatique des champs synthétiques si mode DETAILED
    if self.analysis_mode == self.AnalysisMode.DETAILED:
        self.compute_synthetic_from_detailed()
    
    # Puis calcul des ratios (existant)
    self._compute_ratios()
    
    super().save(*args, **kwargs)
```

#### Validation de la Structure JSON

```python
from django.core.exceptions import ValidationError

def validate_detailed_data_structure(self):
    """Valide la structure JSON selon le type de client."""
    if self.analysis_mode != self.AnalysisMode.DETAILED:
        return
    
    data = self.detailed_data or {}
    
    if self.client_type == 'INDIVIDUAL':
        # Valider income_detail et expenses_detail
        if 'income_detail' not in data or not isinstance(data['income_detail'], list):
            raise ValidationError("income_detail doit être une liste")
        
        for period in data['income_detail']:
            required_fields = ['period', 'salary_income', 'spouse_income']
            for field in required_fields:
                if field not in period:
                    raise ValidationError(f"Champ {field} manquant dans income_detail")
    
    elif self.client_type == 'CORPORATE':
        # Valider exploitation_detail
        if 'exploitation_detail' not in data:
            raise ValidationError("exploitation_detail requis pour les entreprises")
        
        for period in data['exploitation_detail']:
            required_fields = ['period', 'turnover', 'cogs']
            for field in required_fields:
                if field not in period:
                    raise ValidationError(f"Champ {field} manquant dans exploitation_detail")
    
    elif self.client_type == 'PROFESSIONAL':
        # Valider members_detail et collective_detail
        if 'members_detail' not in data:
            raise ValidationError("members_detail requis pour les groupements")
```

#### Serializer DRF

```python
class FinancialAnalysisSerializer(serializers.ModelSerializer):
    # Champs calculés
    total_income = serializers.DecimalField(...)
    total_charges = serializers.DecimalField(...)
    
    # Validation du mode
    def validate(self, data):
        analysis_mode = data.get('analysis_mode')
        detailed_data = data.get('detailed_data', {})
        
        if analysis_mode == 'DETAILED' and not detailed_data:
            raise serializers.ValidationError(
                "detailed_data requis en mode DETAILED"
            )
        
        return data
    
    class Meta:
        model = FinancialAnalysis
        fields = '__all__'
```

### 2. Frontend React/TypeScript

#### Types TypeScript

```typescript
// Types pour les périodes détaillées
interface IncomePeriod {
  period: number;
  period_label: string;
  salary_income: number;
  spouse_income: number;
  rental_income: number;
  other_activity_income: number;
  other_income: number;
}

interface ExpensesPeriod {
  period: number;
  period_label: string;
  rent_expense: number;
  food_expense: number;
  utilities_expense: number;
  transport_expense: number;
  education_expense: number;
  health_expense: number;
  other_household_expenses: number;
}

interface ExploitationPeriod {
  period: number;
  period_label: string;
  turnover: number;
  cogs: number;
  op_rent: number;
  op_salaries: number;
  // ... autres champs
}

interface MemberDetail {
  name: string;
  contribution_amount: number;
  is_active: boolean;
  role?: string;
}

interface DetailedData {
  periods?: number;
  period_unit?: 'MONTHLY' | 'QUARTERLY' | 'ANNUAL';
  income_detail?: IncomePeriod[];
  expenses_detail?: ExpensesPeriod[];
  exploitation_detail?: ExploitationPeriod[];
  members_detail?: MemberDetail[];
  collective_detail?: any[];
}

// Interface principale
interface FinancialAnalysis {
  id: string;
  application: string;
  client_type: 'INDIVIDUAL' | 'CORPORATE' | 'PROFESSIONAL';
  individual_profile?: 'SALARIE' | 'INDEPENDANT' | 'MIXTE';
  analysis_mode: 'SYNTHETIC' | 'DETAILED';
  reference_period: 'MONTHLY' | 'QUARTERLY' | 'ANNUAL';
  
  // Champs synthétiques
  salary_income: number;
  spouse_income: number;
  // ... tous les autres champs
  
  // Données détaillées
  detailed_data: DetailedData;
  
  // Champs calculés
  total_income: number;
  total_charges: number;
  repayment_capacity: number;
  debt_ratio: number;
  // ...
}
```

#### Composant Toggle Mode

```typescript
interface FieldModeToggleProps {
  mode: 'SYNTHETIC' | 'DETAILED';
  onModeChange: (mode: 'SYNTHETIC' | 'DETAILED') => void;
  disabled?: boolean;
}

export function FieldModeToggle({ mode, onModeChange, disabled }: FieldModeToggleProps) {
  return (
    <div className="field-mode-toggle">
      <label className="toggle-label">Mode de saisie</label>
      <div className="toggle-buttons">
        <button
          className={`toggle-btn ${mode === 'SYNTHETIC' ? 'active' : ''}`}
          onClick={() => onModeChange('SYNTHETIC')}
          disabled={disabled}
        >
          📊 Synthétique (Moyennes)
        </button>
        <button
          className={`toggle-btn ${mode === 'DETAILED' ? 'active' : ''}`}
          onClick={() => onModeChange('DETAILED')}
          disabled={disabled}
        >
          📋 Détaillé (Période par période)
        </button>
      </div>
      <p className="toggle-hint">
        {mode === 'SYNTHETIC'
          ? "Saisir des montants moyens ou totaux"
          : "Détailler les montants pour chaque période"}
      </p>
    </div>
  );
}
```

#### Composant Grille Détaillée

```typescript
interface DetailedInputGridProps {
  periods: number;
  periodUnit: 'MONTHLY' | 'QUARTERLY' | 'ANNUAL';
  periodLabels: string[];
  fields: Array<{
    key: string;
    label: string;
    format?: 'money' | 'number' | 'percent';
  }>;
  values: Record<string, number>[];
  onChange: (periodIndex: number, fieldKey: string, value: number) => void;
  showAverage?: boolean;
}

export function DetailedInputGrid({
  periods,
  periodUnit,
  periodLabels,
  fields,
  values,
  onChange,
  showAverage = true
}: DetailedInputGridProps) {
  const calculateAverage = (fieldKey: string) => {
    const sum = values.reduce((acc, period) => acc + (period[fieldKey] || 0), 0);
    return sum / periods;
  };

  return (
    <div className="detailed-input-grid">
      <table className="detailed-table">
        <thead>
          <tr>
            <th>Poste</th>
            {periodLabels.map((label, idx) => (
              <th key={idx}>{label}</th>
            ))}
            {showAverage && <th>Moyenne</th>}
          </tr>
        </thead>
        <tbody>
          {fields.map((field) => (
            <tr key={field.key}>
              <td className="field-label">{field.label}</td>
              {values.map((period, periodIdx) => (
                <td key={periodIdx}>
                  <input
                    type="number"
                    value={period[field.key] || 0}
                    onChange={(e) => onChange(periodIdx, field.key, parseFloat(e.target.value) || 0)}
                    className="detailed-input"
                  />
                </td>
              ))}
              {showAverage && (
                <td className="average-cell">
                  {formatMoney(calculateAverage(field.key), 'XOF')}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

#### Formulaire Adaptatif Principal

```typescript
export function FinancialAnalysisForm({ applicationId, clientType, individualProfile }: Props) {
  const [mode, setMode] = useState<'SYNTHETIC' | 'DETAILED'>('SYNTHETIC');
  const [analysis, setAnalysis] = useState<FinancialAnalysis>({...});
  
  // Changer de mode avec confirmation si données existantes
  const handleModeChange = (newMode: 'SYNTHETIC' | 'DETAILED') => {
    if (hasExistingData && mode !== newMode) {
      if (confirm('Changer de mode recalculera les données. Continuer ?')) {
        setMode(newMode);
        // Logique de conversion
        if (newMode === 'DETAILED') {
          convertSyntheticToDetailed();
        } else {
          convertDetailedToSynthetic();
        }
      }
    } else {
      setMode(newMode);
    }
  };
  
  return (
    <form>
      <FieldModeToggle mode={mode} onModeChange={handleModeChange} />
      
      {/* Sections conditionnelles selon le type de client */}
      {clientType === 'INDIVIDUAL' && individualProfile === 'SALARIE' && (
        <IndividualSalarySection
          mode={mode}
          analysis={analysis}
          onChange={setAnalysis}
        />
      )}
      
      {clientType === 'INDIVIDUAL' && individualProfile === 'INDEPENDANT' && (
        <IndividualBusinessSection
          mode={mode}
          analysis={analysis}
          onChange={setAnalysis}
        />
      )}
      
      {clientType === 'CORPORATE' && (
        <CorporateSection
          mode={mode}
          analysis={analysis}
          onChange={setAnalysis}
        />
      )}
      
      {clientType === 'PROFESSIONAL' && (
        <GroupSection
          mode={mode}
          analysis={analysis}
          onChange={setAnalysis}
        />
      )}
      
      {/* Sections communes */}
      <CommonSections analysis={analysis} onChange={setAnalysis} />
      
      <button type="submit">Enregistrer l'analyse</button>
    </form>
  );
}
```

---

## 📊 Impacts et Bénéfices

### Bénéfices Métier

1. **Précision accrue** :
   - Mode détaillé permet de capturer les variations mensuelles (saisonnalité, primes, etc.)
   - Meilleure évaluation de la capacité de remboursement

2. **Flexibilité** :
   - Choix entre saisie rapide (synthétique) et analyse approfondie (détaillée)
   - Adaptation au niveau de maturité du client

3. **Comparabilité** :
   - Les champs synthétiques restent calculés en mode détaillé
   - Comparaison historique facilitée

4. **Conformité** :
   - Meilleure traçabilité des revenus et charges
   - Documentation plus solide pour les audits

### Impacts Techniques

**Backend :**
- Ajout de 2 champs au modèle (`analysis_mode`, `detailed_data`)
- Migration Django (backward compatible)
- Logique de calcul automatique
- Validation JSON

**Frontend :**
- Nouveau composant `FieldModeToggle`
- Nouveau composant `DetailedInputGrid`
- Refactoring du formulaire existant (sections conditionnelles)
- Nouveaux types TypeScript

**Compatibilité :**
- ✅ Les analyses existantes restent valides (mode SYNTHETIC par défaut)
- ✅ Pas de perte de données
- ✅ Pas de changement sur les endpoints API (ajout de champs)

---

## 🚦 Plan d'Implémentation

### Phase 1 : Backend (Migration + Modèle)
1. Ajouter les champs `analysis_mode` et `detailed_data`
2. Créer la migration
3. Ajouter les méthodes de calcul automatique
4. Ajouter la validation JSON
5. Mettre à jour les serializers

### Phase 2 : Backend (Services)
1. Service de conversion SYNTHETIC ↔ DETAILED
2. Service de génération des labels de période
3. Tests unitaires

### Phase 3 : Frontend (Composants de Base)
1. Créer `FieldModeToggle`
2. Créer `DetailedInputGrid`
3. Créer `DetailedInputRow` (version simplifiée pour une ligne)

### Phase 4 : Frontend (Sections Spécialisées)
1. Refactorer `IndividualSalarySection`
2. Refactorer `IndividualBusinessSection`
3. Refactorer `CorporateSection`
4. Refactorer `GroupSection`

### Phase 5 : Tests & Documentation
1. Tests E2E (création analyse SYNTHETIC)
2. Tests E2E (création analyse DETAILED)
3. Tests E2E (conversion SYNTHETIC → DETAILED)
4. Documentation utilisateur
5. Formation équipes

---

## ❓ Questions à Valider

1. **Nombre de périodes maximum** :
   - Mensuel : 3, 6, 12 mois ?
   - Trimestriel : 2, 4 trimestres ?
   - Annuel : 1, 2, 3 ans ?

2. **Conversion automatique** :
   - Faut-il permettre la conversion SYNTHETIC → DETAILED ?
   - Si oui, avec quelle logique (répartition égale) ?

3. **Champs obligatoires en mode détaillé** :
   - Tous les champs doivent-ils être remplis pour chaque période ?
   - Ou permettre des périodes partielles ?

4. **Calcul de la moyenne** :
   - Moyenne arithmétique simple ?
   - Ou pondérée (ex : pondérer les 3 derniers mois plus fortement) ?

5. **Interface mobile** :
   - Le mode détaillé avec grille est-il adapté au mobile ?
   - Faut-il une version accordéon pour mobile ?

6. **Historique de modification** :
   - Faut-il tracer les changements de mode (SYNTHETIC ↔ DETAILED) ?
   - Versionning des analyses ?

---

## 📋 Résumé Exécutif

### Recommandation

**Adopter l'Option B : Modèle Unique avec Structure JSON**

**Raisons :**
1. Rétrocompatibilité totale
2. Flexibilité maximale (JSON extensible)
3. Migrations simples
4. Comparaison historique facilitée
5. Une seule table à maintenir

**Effort estimé :**
- Backend : ~3-4 jours
- Frontend : ~5-6 jours
- Tests : ~2 jours
- Documentation : ~1 jour

**Total : ~11-13 jours de développement**

### Prochaine Étape

**Validation de l'analyse par le Product Owner / Utilisateur Métier :**
- Confirmer la structure proposée
- Répondre aux questions ouvertes
- Valider les maquettes frontend (à créer)
- Prioriser les types de clients (commencer par le plus fréquent)

Une fois validé, nous procéderons à l'implémentation méthodique phase par phase.

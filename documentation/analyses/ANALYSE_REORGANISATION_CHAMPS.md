# Analyse : Réorganisation des Champs entre CreditApplication et FinancialAnalysis

## 🎯 Objectif

Identifier les champs actuellement dans `CreditApplication` qui devraient être déplacés vers `FinancialAnalysis` pour une meilleure cohérence et éviter les doublons.

## 📊 État des Lieux

### Champs Actuels dans CreditApplication

#### 1. **Relation Bancaire** (lignes 340-352)
```python
client_account_number = models.CharField(...)  # ✅ GARDER
relationship_start_date = models.DateField(...) # ✅ GARDER
avg_monthly_credit_movements = models.DecimalField(...) # ⚠️ À DÉPLACER
```

**Analyse** :
- `client_account_number` : Information **statique** du client → **GARDER** dans CreditApplication (ou Client)
- `relationship_start_date` : Information **statique** du client → **GARDER** dans CreditApplication (ou Client)
- `avg_monthly_credit_movements` : **Donnée d'analyse bancaire** → **DÉPLACER** vers FinancialAnalysis

**Justification** :
Les mouvements créditeurs sont une **donnée d'analyse** qui peut varier dans le temps et qui sert à calculer la capacité de remboursement. Cette donnée devrait être dans l'analyse financière avec une période de référence (ex : 3 derniers mois, 6 derniers mois).

---

#### 2. **Demandeur & Emploi** (lignes 327-338)
```python
employer_name = models.CharField(...)           # ⚠️ À DÉPLACER (ou dupliquer)
contract_type = models.CharField(...)           # ⚠️ À DÉPLACER (ou dupliquer)
salary_domiciliation = models.BooleanField(...) # ✅ GARDER
dependents_count = models.PositiveIntegerField(...) # ⚠️ À DÉPLACER
```

**Analyse** :
- `employer_name` : **Peut changer** entre deux analyses → **DÉPLACER** ou **DUPLIQUER**
- `contract_type` : **Peut changer** (CDD → CDI) → **DÉPLACER** ou **DUPLIQUER**
- `salary_domiciliation` : Information **contractuelle** du dossier → **GARDER**
- `dependents_count` : **Peut changer** et impacte l'analyse des charges → **DÉPLACER**

**Justification** :
L'employeur, le type de contrat et le nombre de personnes à charge sont des **données contextuelles de l'analyse** qui peuvent évoluer. Elles devraient être capturées au moment de l'analyse financière.

**Proposition** :
- **Option A (Recommandée)** : Garder dans CreditApplication ET ajouter dans FinancialAnalysis
  - CreditApplication : Info "au moment du dossier"
  - FinancialAnalysis : Info "au moment de l'analyse" (peut être différente)
  
- **Option B** : Déplacer uniquement vers FinancialAnalysis
  - Plus clean mais perte d'info historique du dossier

---

#### 3. **Assurance** (lignes 356-365)
```python
has_credit_insurance = models.BooleanField(...) # ✅ GARDER
insurance_company = models.CharField(...)       # ✅ GARDER
insurance_premium = models.DecimalField(...)    # ✅ GARDER
```

**Analyse** :
- Tous ces champs sont des **conditions du crédit** → **GARDER** dans CreditApplication

**Justification** :
L'assurance est une **condition contractuelle** du dossier de crédit, pas une donnée d'analyse financière.

---

#### 4. **Activité du Client** (lignes 296-309)
```python
activity_start_date = models.DateField(...)              # ⚠️ COMPLEXE
exact_address = models.CharField(...)                    # ⚠️ À DÉPLACER (Client)
clientele = models.CharField(...)                        # ⚠️ À DÉPLACER
tax_regime = models.CharField(...)                       # ⚠️ À DÉPLACER
avg_client_payment_days = models.PositiveIntegerField(...) # ⚠️ À DÉPLACER
avg_supplier_payment_days = models.PositiveIntegerField(...) # ⚠️ À DÉPLACER
```

**Analyse** :
- `activity_start_date` : **Complexe** - peut être dans Client OU CreditApplication
- `exact_address` : Information **client** → **DÉPLACER vers Client**
- `clientele` : **Donnée d'analyse sectorielle** → **DÉPLACER** (déjà prévu dans FinancialAnalysis via analyse sectorielle)
- `tax_regime` : **Donnée d'analyse fiscale** → **DÉPLACER**
- `avg_client_payment_days` : **Donnée d'analyse trésorerie** → **DÉPLACER**
- `avg_supplier_payment_days` : **Donnée d'analyse trésorerie** → **DÉPLACER**

**Justification** :
Ces informations sont des **données d'analyse opérationnelle** qui peuvent varier dans le temps. Elles devraient être dans FinancialAnalysis.

**Note importante** :
Le modèle `FinancialAnalysis` ne contient PAS actuellement :
- `tax_regime` (à ajouter)
- `avg_client_payment_days` (à ajouter)
- `avg_supplier_payment_days` (à ajouter)

---

#### 5. **Environnement Commercial** (lignes 314-316)
```python
catchment_area = models.CharField(...) # ⚠️ À DÉPLACER (déjà prévu)
```

**Analyse** :
- Cette information est une **donnée d'analyse de marché** → **DÉPLACER**

**Note** :
Le champ n'existe PAS actuellement dans FinancialAnalysis. Il devrait être ajouté dans la section "Analyse sectorielle".

---

#### 6. **Patrimoine** (lignes 321-324)
```python
premises_status = models.CharField(...) # ⚠️ À DÉPLACER (ou dupliquer)
```

**Analyse** :
- Statut d'occupation des locaux (propriétaire/locataire) → **DÉPLACER** ou **DUPLIQUER**

**Justification** :
Cette information impacte l'analyse des charges (loyer ou non) et peut changer dans le temps.

**Proposition** :
- Garder dans CreditApplication comme info "au moment du dossier"
- Ajouter dans FinancialAnalysis pour l'analyse des charges

---

### Champs Déjà dans FinancialAnalysis (pour référence)

#### ✅ Bien placés :
- `employment_seniority_months` : Ancienneté emploi
- `credit_bureau_checked` : Centrale des risques consultée
- `has_payment_incidents` : Incidents de paiement
- `max_days_late` : Retard maximum constaté
- `existing_debt_institution` : Institution du crédit en cours
- `existing_debt_monthly` : Mensualités crédits en cours
- `prior_loans_count` : Nombre de crédits antérieurs
- `prior_repayment_rate` : Taux de remboursement historique

#### ❌ Manquants (à ajouter) :
- `avg_monthly_credit_movements` : Mouvements créditeurs moyens
- `employer_name` : Employeur (au moment de l'analyse)
- `contract_type` : Type de contrat (au moment de l'analyse)
- `dependents_count` : Personnes à charge
- `tax_regime` : Régime fiscal
- `avg_client_payment_days` : Délai paiement clients
- `avg_supplier_payment_days` : Délai paiement fournisseurs
- `catchment_area` : Zone de chalandise
- `premises_status` : Statut occupation locaux

---

## 🎨 Proposition de Réorganisation

### Phase 1 : Ajouter les Champs Manquants dans FinancialAnalysis

#### A. Section "Personne Physique - Contexte Emploi" (nouveau)
```python
# Contexte emploi (au moment de l'analyse)
employer_name_analysis = models.CharField(
    "employeur (au moment de l'analyse)", max_length=200, blank=True
)
contract_type_analysis = models.CharField(
    "type de contrat (au moment de l'analyse)", 
    max_length=20, choices=ContractType.choices, blank=True
)
dependents_count = models.PositiveIntegerField(
    "personnes à charge", null=True, blank=True
)
premises_status = models.CharField(
    "statut d'occupation du logement", 
    max_length=15, choices=PremisesStatus.choices, blank=True
)
```

**Justification** :
- Permet de capturer le contexte au moment de l'analyse
- Peut différer des infos du dossier initial
- Nécessaire pour l'analyse des charges du ménage

#### B. Section "Relation Bancaire - Mouvements" (ajout)
```python
# Mouvements bancaires (période d'observation)
avg_monthly_credit_movements = models.DecimalField(
    "mouvements créditeurs mensuels moyens", 
    max_digits=18, decimal_places=2, null=True, blank=True
)
avg_monthly_debit_movements = models.DecimalField(
    "mouvements débiteurs mensuels moyens", 
    max_digits=18, decimal_places=2, null=True, blank=True,
    help_text="Optionnel : permet d'analyser la trésorerie"
)
banking_observation_period_months = models.PositiveIntegerField(
    "période d'observation bancaire (mois)", 
    null=True, blank=True, default=3,
    help_text="Nombre de mois analysés pour les mouvements bancaires"
)
```

**Justification** :
- Donnée d'analyse bancaire temporelle
- Permet d'évaluer la stabilité des flux de trésorerie

#### C. Section "Entreprise - Environnement Commercial" (ajout)
```python
# Environnement commercial (déjà partiellement couvert par analyse sectorielle)
tax_regime = models.CharField(
    "régime fiscal", max_length=20, choices=TaxRegime.choices, blank=True
)
avg_client_payment_days = models.PositiveIntegerField(
    "délai moyen de paiement clients (jours)", null=True, blank=True
)
avg_supplier_payment_days = models.PositiveIntegerField(
    "délai moyen de paiement fournisseurs (jours)", null=True, blank=True
)
catchment_area = models.CharField(
    "zone de chalandise", max_length=15, choices=CatchmentArea.choices, blank=True
)
```

**Justification** :
- Données d'analyse opérationnelle et commerciale
- Impact direct sur la trésorerie (BFR, cycle d'exploitation)
- Complète l'analyse sectorielle existante

---

### Phase 2 : Déplacer `exact_address` vers Client

```python
# Dans apps/clients/models.py
class Client(TenantScopedModel, AuthoredModel):
    # ... champs existants ...
    
    # Adresse (ajout)
    exact_address = models.CharField(
        "adresse exacte de l'activité/du domicile", 
        max_length=255, blank=True
    )
```

**Justification** :
- L'adresse est une information **client**, pas une information **dossier**
- Devrait être unique par client, pas dupliquée dans chaque dossier

**Migration** :
1. Ajouter le champ dans Client
2. Migrer les données existantes de CreditApplication vers Client (script)
3. Marquer le champ comme deprecated dans CreditApplication
4. Supprimer après quelques releases

---

### Phase 3 : Déprécier les Champs Dupliqués dans CreditApplication

**Option A (Recommandée) : Conserver et Documenter**
```python
# Dans CreditApplication
employer_name = models.CharField(
    "employeur (au moment du dossier)", 
    max_length=200, blank=True,
    help_text="⚠️ Info historique au moment du dossier. Voir aussi FinancialAnalysis.employer_name_analysis"
)
```

**Option B (Plus Agressive) : Supprimer après Migration**
1. Créer un script de migration de données
2. Marquer les champs comme deprecated
3. Supprimer dans une version ultérieure

**Recommandation** : **Option A** pour préserver l'historique

---

## 📋 Résumé des Actions Recommandées

### ✅ Actions Prioritaires (P0)

1. **Ajouter dans FinancialAnalysis** :
   - [ ] `avg_monthly_credit_movements` (mouvements bancaires)
   - [ ] `banking_observation_period_months` (période d'observation)
   - [ ] `employer_name_analysis` (employeur au moment analyse)
   - [ ] `contract_type_analysis` (type contrat au moment analyse)
   - [ ] `dependents_count` (personnes à charge)
   - [ ] `premises_status` (statut occupation logement)
   - [ ] `tax_regime` (régime fiscal)
   - [ ] `avg_client_payment_days` (délai clients)
   - [ ] `avg_supplier_payment_days` (délai fournisseurs)
   - [ ] `catchment_area` (zone de chalandise)

2. **Mettre à jour le formulaire frontend** :
   - [ ] Déplacer les champs vers les sections d'analyse financière
   - [ ] Adapter selon le type de client (INDIVIDUAL, CORPORATE, PROFESSIONAL)
   - [ ] Intégrer avec le mode SYNTHETIC/DETAILED

3. **Documentation** :
   - [ ] Documenter les champs dupliqués (CreditApplication vs FinancialAnalysis)
   - [ ] Expliquer quand utiliser l'un ou l'autre

### 🔜 Actions Secondaires (P1)

4. **Migration de `exact_address`** :
   - [ ] Ajouter le champ dans Client
   - [ ] Script de migration de données
   - [ ] Déprécier dans CreditApplication

5. **Nettoyage** :
   - [ ] Identifier les autres doublons potentiels
   - [ ] Créer un guide de "Quel champ dans quel modèle ?"

---

## 🎯 Impact sur l'Implémentation de l'Analyse Financière Adaptative

### Intégration avec le Plan Initial

La réorganisation des champs s'intègre **parfaitement** avec le plan d'analyse financière adaptative :

**Mode SYNTHETIC** :
```python
# Exemple pour un salarié
analysis.employer_name_analysis = "Entreprise ABC"
analysis.contract_type_analysis = "CDI"
analysis.dependents_count = 3
analysis.premises_status = "TENANT"
analysis.avg_monthly_credit_movements = 500000  # Moyenne sur 3 mois
```

**Mode DETAILED** :
```json
{
  "periods": 3,
  "period_unit": "MONTHLY",
  "banking_detail": [
    {"period": 1, "credit_movements": 480000},
    {"period": 2, "credit_movements": 520000},
    {"period": 3, "credit_movements": 500000}
  ]
}
→ avg_monthly_credit_movements calculé = 500000
```

### Formulaire Frontend Adaptatif

**Section "Profil du Demandeur"** → **Déplacée vers Analyse Financière**

Avant (dans CreditApplicationForm) :
```typescript
<FormSection id="sec-applicant" title="Profil du demandeur">
  <Text label="Employeur" value={text.employer_name} />
  <Select label="Type de contrat" value={text.contract_type} />
  <Text label="Personnes à charge" value={text.dependents_count} />
</FormSection>
```

Après (dans FinancialAnalysisForm) :
```typescript
<FormSection id="sec-employment" title="Contexte Emploi">
  <Text label="Employeur" value={analysis.employer_name_analysis} />
  <Select label="Type de contrat" value={analysis.contract_type_analysis} />
  <Text label="Personnes à charge" value={analysis.dependents_count} />
  <Select label="Statut logement" value={analysis.premises_status} />
</FormSection>
```

---

## ⚠️ Points d'Attention

### 1. Rétrocompatibilité
- Les dossiers existants ont des valeurs dans CreditApplication
- Il faut maintenir ces champs pour l'historique
- Solution : Garder les champs + ajouter dans FinancialAnalysis

### 2. Formulaire Utilisateur
- Actuellement : Tout dans le formulaire de création de dossier
- Futur : Certains champs dans le formulaire d'analyse financière
- Impact UX : Les analystes doivent comprendre la séparation

### 3. Comparaison Historique
- Le système de comparaison doit gérer les deux sources
- Priorité : FinancialAnalysis > CreditApplication (si disponible)

### 4. Migration de Données
- Script nécessaire pour pré-remplir FinancialAnalysis avec les données CreditApplication
- Pour les analyses existantes qui n'ont pas ces champs

---

## 💡 Recommandation Finale

### Approche Progressive (Recommandée)

**Phase 1 (Actuel)** : Ajouter les champs manquants dans FinancialAnalysis
- ✅ Rétrocompatible
- ✅ Pas de rupture
- ✅ Permet coexistence

**Phase 2 (Court terme)** : Adapter le formulaire frontend
- Déplacer les sections vers l'analyse financière
- Conserver les champs dans le dossier comme "valeurs par défaut"
- Le formulaire d'analyse pré-remplit avec les valeurs du dossier

**Phase 3 (Moyen terme)** : Documentation et formation
- Expliquer la séparation dossier / analyse
- Former les équipes

**Phase 4 (Long terme)** : Nettoyage optionnel
- Évaluer si les champs CreditApplication sont encore utilisés
- Déprécier si redondants

---

## ✅ Décision à Prendre

**Question pour validation** :

1. **Approuvez-vous l'ajout de ces 10 champs dans FinancialAnalysis ?**
   - avg_monthly_credit_movements
   - employer_name_analysis
   - contract_type_analysis
   - dependents_count
   - premises_status
   - tax_regime
   - avg_client_payment_days
   - avg_supplier_payment_days
   - catchment_area
   - banking_observation_period_months

2. **Approuvez-vous la conservation des champs dans CreditApplication pour l'historique ?**
   - Option A : Conserver et documenter (recommandé)
   - Option B : Supprimer après migration

3. **Priorisation de la migration de `exact_address` vers Client ?**
   - P0 : Maintenant (en même temps que la refonte)
   - P1 : Plus tard (après la refonte)

**Je recommande** :
- ✅ Oui pour Q1 (ajouter les 10 champs)
- ✅ Option A pour Q2 (conserver et documenter)
- ✅ P1 pour Q3 (exact_address peut attendre)

---

## 📦 Livrables de cette Analyse

1. **Ce document** : Analyse complète des champs à réorganiser
2. **Prêt pour implémentation** : Spécifications précises des modifications
3. **Plan de migration** : Étapes progressives sans rupture

**Prochaine étape** : Validation de l'analyse → Implémentation de la refonte avec les champs réorganisés

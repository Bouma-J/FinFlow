# Analyse des Rôles et Droits - FinFlow

**Date** : 25 septembre 2026  
**Objectif** : Revue de cohérence des rôles existants + création Administrateur de crédit

---

## 📊 Rôles Existants - Analyse de Cohérence

### ✅ Rôles Instruction (COHÉRENTS)

#### 1. Chargé d'affaire
**Responsabilité** : Instruction complète des dossiers  
**Permissions** :
- ✅ CRUD clients
- ✅ CRUD dossiers crédit
- ✅ CRUD analyses financières
- ✅ CRUD visites terrain
- ✅ CRUD garanties & cautions
- ✅ CRUD documents
- ✅ Introduction main levée
- ✅ Opérations recouvrement

**Cohérence** : ✅ Profil complet pour instruire et gérer un dossier

#### 2. Analyste crédit et risque
**Responsabilité** : Analyse financière uniquement  
**Permissions** :
- ✅ Lecture clients, crédit, garanties, workflow
- ✅ CRUD analyses financières
- ✅ CRUD visites terrain
- ✅ CRUD documents

**Cohérence** : ✅ Profil restreint à l'analyse, pas d'instruction

#### 3. Chef d'agence
**Responsabilité** : Supervision + instruction  
**Permissions** :
- ✅ Toutes permissions Chargé d'affaire
- ✅ Décisions restructure/write-off

**Cohérence** : ✅ Extension logique du chargé d'affaire

#### 4. Responsable crédit et risque
**Responsabilité** : Supervision risque  
**Permissions** :
- ✅ Lecture métier complète
- ✅ CRUD analyses financières
- ✅ Décisions restructure

**Cohérence** : ✅ Profil adapté à la supervision risque

---

### ✅ Rôles Décision (COHÉRENTS)

#### 5. Comité de crédit (filiale/groupe)
**Responsabilité** : Décision crédit  
**Permissions** :
- ✅ Lecture clients, crédit, garanties, workflow
- ✅ CRUD analyses financières
- ✅ Modification tâches workflow (approbation)

**Cohérence** : ✅ Profil adapté à la décision

**SoD** : ✅ Incompatible avec Chargé d'affaire et Analyste (correct)

#### 6. Directeur Général
**Responsabilité** : Décision finale, supervision  
**Permissions** :
- ✅ Lecture métier complète

**Cohérence** : ✅ Profil lecture uniquement (décision via workflow)

**SoD** : ✅ Incompatible avec Chargé d'affaire et Analyste (correct)

---

### ⚠️ Rôles Opérations (PROBLÈME IDENTIFIÉ)

#### 7. Responsable des opérations
**Responsabilité** : Opérations post-décision (contrats, garanties, décaissement)  
**Permissions** :
- ✅ Lecture clients, crédit, garanties, workflow, CBS
- ✅ Génération contrats
- ✅ Gestion garanties complète (formalisation, main levée, dation)
- ✅ Gestion cautions
- ⚠️ **Décaissement CBS** : `disburse_creditapplication` + `initiate_disburse_creditapplication`
- ✅ Décisions restructure

**⚠️ Problème** : 
- Rôle trop large : mix opérations + décaissement
- Pas de séparation claire entre "préparation" et "exécution décaissement"
- Manque de contrôle final avant décaissement CBS

**Recommandation** : 
- Conserver ce rôle pour la gestion opérationnelle (contrats, garanties)
- Créer un rôle dédié "Administrateur de crédit" pour le contrôle final + décaissement

#### 8. Assistant des opérations
**Responsabilité** : Assistance opérationnelle  
**Permissions** :
- ✅ Lecture clients, crédit, garanties, workflow, CBS
- ✅ Génération contrats
- ✅ Gestion garanties & cautions
- ✅ Initiation décaissement (pas exécution)

**Cohérence** : ✅ Profil assistant cohérent

---

### ✅ Rôles Juridique (COHÉRENTS)

#### 9. Responsable Juridique
**Responsabilité** : Gestion juridique & contentieux  
**Permissions** :
- ✅ Lecture métier complète
- ✅ Gestion garanties complète
- ✅ Gestion cautions
- ✅ Gestion contentieux (dossiers, événements, parties, saisies, coûts)
- ✅ Génération contrats
- ✅ Opérations recouvrement

**Cohérence** : ✅ Profil complet pour aspect juridique

#### 10. Assistant juridique
**Responsabilité** : Assistance juridique  
**Permissions** : Sous-ensemble Responsable Juridique

**Cohérence** : ✅ Profil assistant cohérent

---

### ✅ Rôles Recouvrement (COHÉRENTS)

#### 11. Responsable recouvrement
**Responsabilité** : Gestion recouvrement & contentieux  
**Permissions** :
- ✅ Lecture clients, crédit, collections, garanties
- ✅ CRUD repayments
- ✅ Gestion dossiers recouvrement
- ✅ Gestion contentieux complet
- ✅ Restructure & write-off
- ✅ Dation & formalisation garanties

**Cohérence** : ✅ Profil complet pour recouvrement

**SoD** : ✅ Incompatible avec Audit (correct)

#### 12. Assistant recouvrement
**Responsabilité** : Assistance recouvrement  
**Permissions** : Sous-ensemble Responsable recouvrement

**Cohérence** : ✅ Profil assistant cohérent

**SoD** : ✅ Incompatible avec Audit (correct)

---

### ✅ Rôles Contrôle/Audit (COHÉRENTS)

#### 13-16. Contrôle Interne & Audit
**Responsabilité** : Contrôle et audit  
**Permissions** :
- ✅ Lecture métier complète
- ✅ Visites terrain uniquement (contrôle)
- ❌ Aucune écriture opérationnelle

**Cohérence** : ✅ Profils adaptés au contrôle

**SoD** : ✅ Incompatibilités avec opérations (correct)

---

### ✅ Rôles Finance/Comptabilité (COHÉRENTS)

#### 17-19. Chef comptable, Comptable, Resp. Admin & Financier
**Responsabilité** : Gestion financière & comptable  
**Permissions** :
- ✅ Lecture clients, crédit, collections
- ✅ Gestion encaissements
- ✅ (Chef) Lecture CBS & audit

**Cohérence** : ✅ Profils adaptés aux fonctions financières

---

### ✅ Rôle Consultation (COHÉRENT)

#### 20. Lecteur
**Responsabilité** : Consultation seule  
**Permissions** :
- ✅ Lecture métier (sauf CBS)
- ❌ Aucune écriture

**Cohérence** : ✅ Profil lecture pure

---

## 🆕 Nouveau Rôle : Administrateur de Crédit

### Justification

**Problème actuel** :
- Le "Responsable des opérations" fait tout : contrats, garanties, ET décaissement
- Pas de contrôle final dédié avant décaissement CBS
- Manque de séparation des tâches pour décaissement

**Solution** : Créer un rôle dédié au **contrôle final + décaissement CBS**

### Définition du Rôle

**Nom** : Administrateur de crédit

**Responsabilité** :
1. **Contrôle final pré-décaissement** :
   - Vérifier que tous les contrats sont signés et chargés
   - Vérifier que les garanties sont formalisées
   - Vérifier que les cautions sont actives
   - Vérifier conformité du dossier

2. **Exécution décaissement CBS** :
   - Initier et exécuter le décaissement dans le CBS
   - Responsabilité unique du décaissement

### Permissions

```python
_ADMINISTRATEUR_CREDIT_PERMS = (
    # Lecture complète métier
    *_READ_METIER,
    
    # Décaissement CBS (responsabilité principale)
    ("credits", "disburse_creditapplication"),
    ("credits", "initiate_disburse_creditapplication"),
    
    # Génération et vérification contrats
    ("contracts", "add_generatedcontract"),
    ("contracts", "change_generatedcontract"),
    ("contracts", "view_generatedcontract"),
    
    # Upload documents de vérification
    ("documents", "add_document"),
    ("documents", "change_document"),
    
    # Consultation et mise à jour garanties (vérification formalisation)
    ("guarantees", "change_guarantee"),
    ("guarantees", "view_guaranteemovement"),
    
    # Consultation cautions
    ("sureties", "view_suretyengagement"),
    
    # PAS de création/modification dossiers (rôle de contrôle final uniquement)
)
```

### Séparation des Tâches (SoD)

**Incompatible avec** :
- ❌ Chargé d'affaire (instruction)
- ❌ Analyste crédit (analyse)
- ❌ Comité de crédit (décision)

**Raison** : Séparation instruction/décision/décaissement

### Comparaison avec Responsable des Opérations

| Aspect | Resp. Opérations | Admin. Crédit |
|--------|------------------|---------------|
| **Focus** | Opérations post-décision | Contrôle final + décaissement |
| **Génération contrats** | ✅ | ✅ |
| **Gestion garanties** | ✅ Complète | ✅ Consultation + validation |
| **Décaissement CBS** | ✅ | ✅ |
| **Restructure** | ✅ | ❌ |
| **Instruction dossiers** | ❌ | ❌ |
| **Contrôle final** | ❌ | ✅ (Responsabilité principale) |

### Workflow Recommandé

```
1. Instruction → Chargé d'affaire
2. Analyse → Analyste crédit
3. Décision → Comité de crédit / DG
4. Opérations → Resp. Opérations (contrats, garanties)
5. Contrôle final + Décaissement → Administrateur de crédit ✨ (NOUVEAU)
```

---

## 📋 Recommandations

### Immédiat
- ✅ **Créer le rôle "Administrateur de crédit"** (fait)
- ✅ **Ajouter règles SoD** (fait)
- ⚠️ **Documenter le workflow** pour les utilisateurs

### Court Terme
- 🔄 **Réviser permissions Responsable Opérations** : Retirer décaissement si Admin Crédit dédié existe
- 📝 **Former les administrateurs de crédit** sur le contrôle final
- 🔍 **Auditer les décaissements** : Tracer qui fait quoi

### Moyen Terme
- 📊 **Dashboard Administrateur de crédit** : Liste dossiers prêts pour décaissement avec checklist
- 🔔 **Alertes automatiques** : Notifier Admin Crédit quand dossier prêt
- 📄 **Rapport de conformité** : Avant chaque décaissement

---

## ✅ Cohérence Globale

**Après ajout Administrateur de crédit** : ✅ **COHÉRENTE**

| Étape | Rôle | Permissions | SoD |
|-------|------|-------------|-----|
| Instruction | Chargé d'affaire | CRUD dossiers | ✅ |
| Analyse | Analyste crédit | CRUD analyses | ✅ |
| Décision | Comité/DG | Approbation workflow | ✅ |
| Opérations | Resp. Opérations | Contrats, garanties | ✅ |
| **Contrôle + Décaissement** | **Admin. Crédit** | **Vérification + CBS** | ✅ |
| Recouvrement | Resp. Recouvrement | Collections | ✅ |
| Contrôle | Audit/CI | Lecture seule | ✅ |
| Finance | Comptable | Encaissements | ✅ |

---

## 📝 Notes de Migration

Pour les instances existantes :
1. Créer le rôle "Administrateur de crédit" via commande `sync_role_packs`
2. Affecter des utilisateurs dédiés au rôle
3. (Optionnel) Retirer permission décaissement du "Responsable Opérations" si séparation souhaitée
4. Documenter et former

---

**État** : ✅ ANALYSE COMPLÈTE  
**Action** : ✅ NOUVEAU RÔLE CRÉÉ  
**Prêt** : ✅ POUR DÉPLOIEMENT

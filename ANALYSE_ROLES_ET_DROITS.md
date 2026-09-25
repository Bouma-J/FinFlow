# Analyse des Rôles et Droits - FinFlow

**Date** : 25 septembre 2026  
**Objectif** : Revue de cohérence des rôles existants + création Administrateur de crédit

---

## ⚠️ Distinction Fondamentale : Rôle vs Workflow

### Ce que définit un RÔLE (Permissions)

**Les rôles définissent ce qu'on peut FAIRE techniquement** :
- ✅ Créer/modifier des dossiers (CRUD)
- ✅ Lire des informations
- ✅ Générer des contrats
- ✅ Décaisser dans le CBS (action technique)
- ✅ Uploader des documents

**Analogie** : Les rôles sont comme des "clés" qui ouvrent des portes.

### Ce que définit le WORKFLOW (Décisions/Avis)

**Le workflow définit QUI intervient QUAND et COMMENT** :
- 📍 À quelle étape du processus
- 🎯 Type d'intervention : **Décision** (approuve/rejette) ou **Avis** (recommandation)
- 📋 Conditions de passage à l'étape suivante
- 👤 Rôle(s) assigné(s) à chaque étape

**Analogie** : Le workflow est le "plan du bâtiment" qui dit quelles portes ouvrir dans quel ordre.

### Exemple Concret

**Rôle "Analyste crédit"** :
- Permission : Peut créer/modifier analyses financières ✅
- Permission : Peut lire dossiers clients ✅
- Permission : Peut ajouter documents ✅

**Workflow "Validation crédit PME"** :
- Étape 2 : "Analyse crédit"
  - Rôle assigné : **Analyste crédit**
  - Type : **Avis** (recommande favorable/défavorable)
  - Condition : Doit avoir complété l'analyse
  
**Ce que l'analyste PEUT faire** = Rôle/Permissions  
**Ce que l'analyste DOIT faire à cette étape** = Workflow

### Important pour ce Document

**Ce document analyse les PERMISSIONS** (rôles), **PAS les workflows**.

Les workflows sont configurés séparément dans l'application selon vos processus métier.

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

### ⚠️ Distinction Rôle vs Workflow

**IMPORTANT** : Ce document définit les **PERMISSIONS** (ce qu'on peut faire techniquement).

**Les rôles NE définissent PAS** :
- ❌ Qui prend des décisions (approuve/rejette)
- ❌ Qui donne des avis
- ❌ À quelle étape du processus

**Cela est défini par le WORKFLOW/CIRCUIT** :
- Le workflow décide qui intervient à quelle étape
- Le workflow décide si c'est une décision ou un avis
- Le workflow décide les conditions de passage

### Justification

**Problème actuel** :
- Le "Responsable des opérations" fait tout : contrats, garanties, ET décaissement
- Pas de rôle dédié avec permissions spécifiques pour décaissement CBS
- Manque de séparation des tâches pour décaissement

**Solution** : Créer un rôle dédié avec **permissions spécifiques** pour décaissement CBS

### Définition du Rôle

**Nom** : Administrateur de crédit

**Permissions Techniques** (ce qu'il peut FAIRE) :
1. **Lecture métier complète** :
   - Consulter tous les dossiers, clients, garanties, contrats
   - Accès CBS pour vérification

2. **Gestion contrats** :
   - Générer contrats
   - Modifier contrats (ajouter signatures, documents)
   - Marquer contrats comme signés

3. **Vérification garanties** :
   - Consulter garanties
   - Modifier statut (ex: marquer comme formalisée)
   - Consulter cautions

4. **Décaissement CBS** (Permission principale) :
   - Initier décaissement dans CBS
   - Exécuter décaissement dans CBS
   - Permission technique : `disburse_creditapplication`

5. **Documents** :
   - Uploader documents de vérification
   - Modifier documents existants

**Permissions EXCLUES** :
- ❌ Créer/modifier dossiers de crédit
- ❌ Créer/modifier analyses financières
- ❌ Modifier décisions workflow (c'est le workflow qui décide)

### Utilisation dans le Workflow

**Exemple de configuration workflow** :

```
Étape 5 : "Vérification pré-décaissement"
  Rôle assigné : Administrateur de crédit
  Type : Avis (ou Décision selon configuration)
  Conditions :
    - Contrats signés : OUI
    - Garanties formalisées : OUI
    - Cautions actives : OUI
  
Étape 6 : "Décaissement CBS"
  Rôle assigné : Administrateur de crédit
  Action : Décaissement (bouton "Décaisser dans CBS")
  Conditions :
    - Étape 5 validée
    - Approbation finale obtenue
```

**Le workflow décidera** :
- Quand l'Administrateur de crédit intervient
- S'il doit donner un avis ou décider
- Quelles vérifications sont obligatoires

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

### Exemple de Workflow (Configuration Possible)

**Note** : Ceci est un EXEMPLE de configuration workflow, pas une définition du rôle.

```
Étape 1 : "Instruction"
  Rôle : Chargé d'affaire
  Permissions utilisées : CRUD dossiers, analyses, documents
  
Étape 2 : "Analyse crédit"
  Rôle : Analyste crédit
  Type : Avis
  Permissions utilisées : CRUD analyses financières
  
Étape 3 : "Décision Comité"
  Rôle : Comité de crédit
  Type : Décision (Approuve/Rejette)
  Permissions utilisées : Modification tâche workflow
  
Étape 4 : "Préparation contrats & garanties"
  Rôle : Resp. Opérations
  Type : Avis (préparation)
  Permissions utilisées : Génération contrats, gestion garanties
  
Étape 5 : "Vérification pré-décaissement" ✨
  Rôle : Administrateur de crédit
  Type : Avis (vérification conformité)
  Conditions : Contrats signés, garanties formalisées
  Permissions utilisées : Lecture complète, modification contrats/garanties
  
Étape 6 : "Décaissement CBS" ✨
  Rôle : Administrateur de crédit
  Action : Décaissement (technique)
  Permissions utilisées : disburse_creditapplication
```

**À configurer dans le workflow selon vos besoins :**
- Nombre d'étapes
- Qui décide vs qui donne un avis
- Conditions de passage
- Rôles assignés à chaque étape

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

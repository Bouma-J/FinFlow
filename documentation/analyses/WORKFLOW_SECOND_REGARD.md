# Workflow "Second Regard" - Write-off & Restructuration

## 📋 Vue d'ensemble

Ce document décrit le workflow de **double validation obligatoire** (Second Regard) implémenté pour les opérations sensibles sur les prêts :
- **Write-off** : Passage en perte d'un crédit irrécupérable
- **Restructuration** : Modification des termes d'un crédit en difficulté

## 🎯 Objectifs

### Conformité réglementaire
- Respect du principe de **séparation des tâches** (aucune opération sensible par une seule personne)
- **Traçabilité complète** pour les audits externes
- **Prévention de la fraude** par validation obligatoire

### Sécurité bancaire
- Aucun agent ne peut passer un crédit en perte seul
- Aucune restructuration sans validation hiérarchique
- Historique complet de toutes les demandes (approuvées/rejetées)

---

## 🔴 Workflow Write-off (Passage en Perte)

### Principe
Le write-off est l'acte de **sortir un crédit irrécupérable du bilan actif** et de le **passer en perte définitive**.

### Pré-requis obligatoires
- Crédit actif (statut `ACTIVE`)
- ≥ 180 jours de retard (sauf justification exceptionnelle)
- Provisionnement à **100%**
- Recours de recouvrement **épuisés** (amiable + judiciaire)

### Workflow complet

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. CRÉATION DE LA DEMANDE                    │
│  Agent de recouvrement / Chef d'agence                         │
│  - Sélectionne le prêt                                          │
│  - Remplit le formulaire :                                      │
│    • Motif (irrécupérable, décès, disparition, etc.)          │
│    • Solde restant dû                                           │
│    • Jours de retard                                            │
│    • Démarches de recouvrement effectuées                       │
│    • Statut des garanties                                       │
│    • Taux de provisionnement (doit être 100%)                   │
│    • Justification détaillée                                    │
│  → Statut: PENDING                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    2. VALIDATION (SECOND REGARD)                │
│  Validateur (Chef crédit / Directeur)                          │
│  Permission: approve_writeoff                                   │
│  - Examine la demande                                           │
│  - Vérifie la documentation                                     │
│  - Décision: APPROUVER ou REJETER                              │
│  - Saisit un commentaire                                        │
│  ⚠️  CONTRÔLE: Le validateur ≠ le demandeur                    │
│  → Statut: APPROVED ou REJECTED                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    3. EXÉCUTION                                 │
│  Agent autorisé                                                 │
│  Permission: execute_writeoff                                   │
│  - Déclenche l'exécution                                        │
│  - Système met à jour automatiquement :                         │
│    • Prêt → statut DEFAULTED                                    │
│    • Demande → statut EXECUTED                                  │
│  → Logs critiques générés automatiquement                       │
│  → Notification comptabilité                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Modèle de données : `LoanWriteOffRequest`

```python
class LoanWriteOffRequest:
    # Identification
    loan: ForeignKey(Loan)
    status: PENDING | APPROVED | REJECTED | CANCELLED | EXECUTED
    
    # Détails de la demande
    reason: WriteOffReason (choix multiple)
    outstanding_balance: Decimal  # Montant passé en perte
    days_past_due: int
    recovery_attempts: TextField  # Démarches effectuées
    guarantees_status: TextField
    accounting_provision_rate: Decimal  # Doit être 100%
    justification: TextField
    
    # Cycle de vie
    created_by: User (initiateur)
    created_at: DateTime
    reviewed_by: User (validateur)
    reviewed_at: DateTime
    review_comment: TextField
    executed_by: User (exécuteur)
    executed_at: DateTime
```

### Endpoints API

```http
# Créer une demande
POST /api/credits/loan-writeoff-requests/
{
  "loan": 123,
  "reason": "UNRECOVERABLE",
  "outstanding_balance": "50000.00",
  "days_past_due": 365,
  "recovery_attempts": "Relances amiables (3), mise en demeure (1), action judiciaire (1)",
  "guarantees_status": "Garanties réalisées sans succès",
  "accounting_provision_rate": "100.00",
  "justification": "Après 12 mois de recouvrement infructueux..."
}

# Approuver une demande
POST /api/credits/loan-writeoff-requests/{id}/approve/
{
  "comment": "Dossier complet, recours épuisés. Approuvé pour passage en perte."
}

# Rejeter une demande
POST /api/credits/loan-writeoff-requests/{id}/reject/
{
  "comment": "Provisionnement incomplet. Refaire la demande après mise à jour."
}

# Exécuter le write-off
POST /api/credits/loan-writeoff-requests/{id}/execute/
{}

# Annuler sa propre demande (initiateur uniquement)
POST /api/credits/loan-writeoff-requests/{id}/cancel/
{
  "reason": "Erreur de saisie, nouvelle demande en cours"
}
```

### Permissions Django

```python
# Créer une demande
credits.add_loanwriteoffrequest

# Approuver/rejeter
credits.approve_writeoff

# Exécuter
credits.execute_writeoff
```

---

## 🔄 Workflow Restructuration

### Principe
La restructuration consiste à **modifier les termes d'un crédit en difficulté** pour aider le client à rembourser et éviter le contentieux.

### Types de modifications possibles
- **Allongement de la durée** (réduction de la mensualité)
- **Période de grâce** (pause de remboursement temporaire)
- **Réduction du taux d'intérêt** (concession exceptionnelle)
- **Capitalisation des arriérés** (intégration des impayés dans le capital)

### Workflow complet

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. CRÉATION DE LA DEMANDE                    │
│  Chargé de clientèle / Chef d'agence                           │
│  - Sélectionne le prêt                                          │
│  - Remplit le formulaire :                                      │
│    • Motif (baisse de revenus, santé, force majeure, etc.)    │
│    • État actuel du prêt                                        │
│    • Nouveaux termes proposés :                                 │
│      - Nouvelle durée                                           │
│      - Nouveau taux (optionnel)                                 │
│      - Période de grâce                                         │
│      - Capitalisation des arriérés                              │
│    • Analyse de capacité révisée (revenus/charges)             │
│    • Garanties maintenues                                       │
│    • Justification détaillée                                    │
│  → Calcul automatique : nouvelle mensualité + surcoût          │
│  → Statut: PENDING                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    2. VALIDATION (SECOND REGARD)                │
│  Validateur (Directeur crédit / Directeur général)             │
│  Permission: approve_restructuring                              │
│  - Examine la demande                                           │
│  - Vérifie la nouvelle capacité de remboursement               │
│  - Évalue le risque résiduel                                    │
│  - Décision: APPROUVER ou REJETER                              │
│  - Saisit un commentaire                                        │
│  ⚠️  CONTRÔLE: Le validateur ≠ le demandeur                    │
│  → Statut: APPROVED ou REJECTED                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    3. EXÉCUTION                                 │
│  Agent autorisé                                                 │
│  Permission: execute_restructuring                              │
│  - Déclenche l'exécution                                        │
│  - Système met à jour automatiquement :                         │
│    • Prêt → nouveaux termes appliqués                           │
│    • Échéancier recalculé                                       │
│    • Demande → statut EXECUTED                                  │
│  → Logs détaillés générés automatiquement                       │
│  → Génération d'un avenant au contrat                           │
│  → Notification client                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Modèle de données : `LoanRestructuringRequest`

```python
class LoanRestructuringRequest:
    # Identification
    loan: ForeignKey(Loan)
    status: PENDING | APPROVED | REJECTED | CANCELLED | EXECUTED
    
    # Détails de la demande
    reason: RestructuringReason (choix multiple)
    
    # État actuel
    current_outstanding_balance: Decimal
    current_monthly_installment: Decimal
    current_remaining_months: int
    current_days_past_due: int
    
    # Nouveaux termes proposés
    new_duration_months: int
    new_interest_rate: Decimal (optionnel)
    grace_period_months: int (défaut: 0)
    capitalize_arrears: bool (défaut: False)
    arrears_amount: Decimal
    
    # Impact financier (calculé auto)
    new_monthly_installment: Decimal
    additional_interest_cost: Decimal
    
    # Analyse de capacité révisée
    client_revised_income: Decimal
    client_revised_expenses: Decimal
    revised_debt_ratio: Decimal
    
    # Garanties et conditions
    guarantees_maintained: bool (défaut: True)
    guarantees_comment: TextField
    special_conditions: TextField
    previous_restructuring_count: int (défaut: 0)
    
    justification: TextField
    
    # Cycle de vie
    created_by: User (initiateur)
    created_at: DateTime
    reviewed_by: User (validateur)
    reviewed_at: DateTime
    review_comment: TextField
    executed_by: User (exécuteur)
    executed_at: DateTime
```

### Endpoints API

```http
# Créer une demande
POST /api/credits/loan-restructuring-requests/
{
  "loan": 123,
  "reason": "INCOME_REDUCTION",
  "current_outstanding_balance": "80000.00",
  "current_monthly_installment": "8000.00",
  "current_remaining_months": 12,
  "current_days_past_due": 45,
  "new_duration_months": 24,
  "grace_period_months": 3,
  "capitalize_arrears": true,
  "arrears_amount": "12000.00",
  "client_revised_income": "150000.00",
  "client_revised_expenses": "100000.00",
  "revised_debt_ratio": "35.00",
  "guarantees_maintained": true,
  "justification": "Le client a perdu son emploi principal..."
}

# Approuver une demande
POST /api/credits/loan-restructuring-requests/{id}/approve/
{
  "comment": "Capacité de remboursement révisée acceptable. Approuvé."
}

# Rejeter une demande
POST /api/credits/loan-restructuring-requests/{id}/reject/
{
  "comment": "Taux d'endettement révisé trop élevé (>50%). Demander un apport supplémentaire."
}

# Exécuter la restructuration
POST /api/credits/loan-restructuring-requests/{id}/execute/
{}

# Annuler sa propre demande
POST /api/credits/loan-restructuring-requests/{id}/cancel/
{
  "reason": "Client a finalement trouvé d'autres solutions"
}
```

### Permissions Django

```python
# Créer une demande
credits.add_loanrestructuringrequest

# Approuver/rejeter
credits.approve_restructuring

# Exécuter
credits.execute_restructuring
```

---

## 🔒 Sécurité et contrôles

### Séparation des pouvoirs
```python
# Dans les viewsets, contrôle automatique
if obj.created_by_id == request.user.id:
    raise PermissionDenied(
        "Vous ne pouvez pas approuver votre propre demande "
        "(principe de séparation des pouvoirs)."
    )
```

### Validations métier

**Write-off :**
- ✅ Prêt doit être actif
- ✅ Minimum 180 jours de retard (sauf justification)
- ✅ Provisionnement à 100% obligatoire
- ✅ Solde restant dû > 0

**Restructuration :**
- ✅ Prêt doit être actif
- ✅ Nouvelle durée > durée restante
- ✅ Maximum 2 restructurations antérieures
- ✅ Période de grâce ≤ 6 mois (sauf justification)
- ✅ Cohérence arriérés capitalisés

### Traçabilité complète

Chaque demande génère des logs détaillés :

```python
logger.warning(
    f"WRITE-OFF EXÉCUTÉ: Prêt {loan.pk} passé en perte",
    extra={
        "request_id": self.pk,
        "loan_id": loan.pk,
        "outstanding_balance": float(self.outstanding_balance),
        "days_past_due": self.days_past_due,
        "reason": self.reason,
        "executed_by": user.pk,
        "approved_by": self.reviewed_by.pk,
        "requested_by": self.created_by.pk,
        "tenant_id": self.tenant_id,
    },
)
```

---

## 📊 Rapports et Audits

### Requêtes utiles

**Tous les write-offs du mois :**
```python
LoanWriteOffRequest.objects.filter(
    executed_at__gte=start_of_month,
    status="EXECUTED"
).select_related("loan", "created_by", "reviewed_by", "executed_by")
```

**Demandes en attente de validation :**
```python
LoanWriteOffRequest.objects.filter(status="PENDING")
LoanRestructuringRequest.objects.filter(status="PENDING")
```

**Historique d'un prêt :**
```python
loan.loanwriteoffrequest_set.all()
loan.loanrestructuringrequest_set.all()
```

### Exports pour audit

Les logs JSON structurés permettent de générer automatiquement :
- Rapport mensuel des write-offs (montants, raisons, validateurs)
- Rapport des restructurations (impact financier, taux de réussite)
- Tableau de bord des demandes (temps de traitement, taux d'approbation)

---

## 🎓 Formation utilisateurs

### Profils et rôles

| Rôle | Permissions | Actions autorisées |
|------|-------------|-------------------|
| **Chargé de recouvrement** | `add_loanwriteoffrequest` | Créer demande write-off |
| **Chargé de clientèle** | `add_loanrestructuringrequest` | Créer demande restructuration |
| **Chef crédit** | `approve_writeoff`<br>`approve_restructuring` | Valider les demandes |
| **Directeur** | `execute_writeoff`<br>`execute_restructuring` | Exécuter les opérations approuvées |

### Points clés à retenir

1. **Jamais d'opération directe** : Toujours passer par une demande
2. **Double validation obligatoire** : Initiateur ≠ Validateur
3. **Documentation complète** : Justification détaillée obligatoire
4. **Traçabilité permanente** : Impossible de supprimer l'historique

---

## 🚀 Migration depuis l'ancien système

### Avant (risque élevé)
```python
# ❌ N'importe qui pouvait faire :
loan.status = "DEFAULTED"
loan.save()
# → Aucune traçabilité, aucun contrôle
```

### Après (conforme et sécurisé)
```python
# ✅ Workflow obligatoire :
# 1. Créer la demande
request = LoanWriteOffRequest.objects.create(
    loan=loan,
    reason="UNRECOVERABLE",
    outstanding_balance=loan.outstanding_balance,
    days_past_due=365,
    recovery_attempts="...",
    justification="...",
    created_by=initiator
)

# 2. Validation par un supérieur
request.approve(validator, comment="...")

# 3. Exécution par un agent autorisé
loan = request.execute(executor)
# → Traçabilité complète, logs automatiques
```

---

## 📞 Support

En cas de question sur ce workflow :
- **Documentation technique** : Ce fichier + code source commenté
- **Formation** : Vidéos de démonstration disponibles
- **Support technique** : Équipe IT FinFlow

---

**Dernière mise à jour** : 2026-09-25  
**Version** : 1.0  
**Auteur** : Cursor AI Cloud Agent

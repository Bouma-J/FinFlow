# 🚀 GUIDE D'IMPLÉMENTATION - MODE DETAILED
## Analyse Financière FinFlow

---

**Date**: 25 septembre 2026  
**Objectif**: Implémenter le mode DETAILED complet frontend/backend  
**Priorité**: P0 - BLOQUANT  
**Effort Estimé**: 2-3 jours

---

## 📋 CONTEXTE

Le mode DETAILED permet de saisir les données financières période par période (mois par mois, trimestre par trimestre) plutôt qu'en moyennes. Le backend calcule automatiquement les moyennes pour les champs synthétiques.

**État actuel**:
- ✅ Backend: Calcul automatique des moyennes implémenté
- ❌ Frontend: Aucune interface de saisie période par période
- ❌ Conversion: Pas de conversion SYNTHETIC ↔ DETAILED

---

## 🎯 OBJECTIFS

1. **Frontend**: Créer interface de saisie période par période
2. **Backend**: Ajouter validation JSON detailed_data
3. **UX**: Permettre conversion entre modes
4. **Tests**: Valider le workflow complet

---

## 🔧 IMPLÉMENTATION

### 1. Types TypeScript - Correction

**Fichier**: `/workspace/frontend/src/types/financialAnalysis.ts`

#### Problème Actuel

```typescript
// Types incomplets et noms incohérents
export interface IncomePeriod {
  period_label?: string;
  salary_income?: number;
  other_income?: number;
  spouse_income?: number;
  rental_income?: number;
  pension_income?: number;
  investment_income?: number;
}
```

#### ✅ Solution Complète

```typescript
/**
 * Structure des données détaillées par période pour les revenus (INDIVIDUAL)
 */
export interface IncomePeriod {
  period_label?: string;
  
  // Revenus salariés
  salary_income?: number;
  spouse_income?: number;
  rental_income?: number;
  other_activity_income?: number;  // ⚠️ Correction: cohérence avec backend
  other_income?: number;
  
  // Activité génératrice de revenu (AGR)
  activity_turnover?: number;  // Nouveau
  activity_expenses?: number;  // Nouveau
}

/**
 * Structure des données détaillées par période pour les dépenses (INDIVIDUAL)
 */
export interface ExpensesPeriod {
  period_label?: string;
  
  // Dépenses ménage
  rent_expense?: number;  // ⚠️ Correction: rent → rent_expense
  food_expense?: number;
  utilities_expense?: number;
  transport_expense?: number;
  education_expense?: number;
  health_expense?: number;
  other_household_expenses?: number;
  
  // Charges informelles
  tontine_expense?: number;
  social_contributions?: number;
  family_support_expense?: number;
}

/**
 * Structure des données détaillées par période pour l'exploitation (CORPORATE)
 */
export interface ExploitationPeriod {
  period_label?: string;
  
  // Compte d'exploitation
  turnover?: number;
  cogs?: number;  // Cost of Goods Sold
  
  // Charges d'exploitation
  op_rent?: number;
  op_salaries?: number;
  op_utilities?: number;
  op_transport?: number;
  op_telecom?: number;
  op_taxes?: number;
  op_maintenance?: number;
  op_other?: number;
  
  // Amortissements et charges financières
  depreciation?: number;
  financial_charges?: number;
}

/**
 * Structure des données détaillées par période pour les mouvements bancaires
 */
export interface BankingPeriod {
  period_label?: string;
  credit_movements?: number;
  debit_movements?: number;
}

/**
 * Structure des données détaillées par période pour les contributions collectives (GROUP)
 */
export interface CollectivePeriod {
  period_label?: string;
  collective_contributions?: number;
  collective_other_income?: number;
  collective_operating_expenses?: number;
}

/**
 * Structure complète des données détaillées (JSON stocké dans detailed_data)
 */
export interface DetailedData {
  num_periods?: number;  // Nouveau: nombre de périodes
  
  income_detail?: IncomePeriod[];
  expenses_detail?: ExpensesPeriod[];
  exploitation_detail?: ExploitationPeriod[];
  banking_detail?: BankingPeriod[];
  collective_detail?: CollectivePeriod[];
}

/**
 * Helper pour créer une période vide
 */
export const createEmptyIncomePeriod = (index: number): IncomePeriod => ({
  period_label: `Période ${index + 1}`,
  salary_income: 0,
  spouse_income: 0,
  rental_income: 0,
  other_activity_income: 0,
  other_income: 0,
});

export const createEmptyExpensesPeriod = (index: number): ExpensesPeriod => ({
  period_label: `Période ${index + 1}`,
  rent_expense: 0,
  food_expense: 0,
  utilities_expense: 0,
  transport_expense: 0,
  education_expense: 0,
  health_expense: 0,
  other_household_expenses: 0,
  tontine_expense: 0,
  social_contributions: 0,
  family_support_expense: 0,
});

export const createEmptyExploitationPeriod = (index: number): ExploitationPeriod => ({
  period_label: `Période ${index + 1}`,
  turnover: 0,
  cogs: 0,
  op_rent: 0,
  op_salaries: 0,
  op_utilities: 0,
  op_transport: 0,
  op_telecom: 0,
  op_taxes: 0,
  op_maintenance: 0,
  op_other: 0,
  depreciation: 0,
  financial_charges: 0,
});
```

---

### 2. Composant Sélecteur de Mode

**Fichier**: `/workspace/frontend/src/components/financial-analysis/AnalysisModeSelector.tsx`

```typescript
import React from 'react';
import { AlertCircle, List, Table } from 'lucide-react';
import type { AnalysisMode } from '@/types/financialAnalysis';

interface AnalysisModeSelectorProps {
  currentMode: AnalysisMode;
  onChange: (mode: AnalysisMode) => void;
  disabled?: boolean;
  hasData?: boolean;  // Si des données existent, afficher avertissement conversion
}

export const AnalysisModeSelector: React.FC<AnalysisModeSelectorProps> = ({
  currentMode,
  onChange,
  disabled = false,
  hasData = false,
}) => {
  const handleModeChange = (newMode: AnalysisMode) => {
    if (disabled) return;
    
    if (hasData && currentMode !== newMode) {
      const confirmMessage = newMode === 'DETAILED'
        ? 'Passer en mode DÉTAILLÉ ?\n\nLes valeurs moyennes actuelles seront réparties uniformément sur toutes les périodes. Vous pourrez ensuite ajuster chaque période individuellement.'
        : 'Passer en mode SYNTHÉTIQUE ?\n\nLes moyennes seront calculées automatiquement à partir des périodes détaillées. Les données période par période seront conservées mais ne seront plus modifiables.';
      
      if (!confirm(confirmMessage)) {
        return;
      }
    }
    
    onChange(newMode);
  };

  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200 mb-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <Table size={20} />
        Mode d'analyse
      </h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mode SYNTHETIC */}
        <button
          type="button"
          onClick={() => handleModeChange('SYNTHETIC')}
          disabled={disabled}
          className={`p-6 rounded-lg border-2 transition-all text-left ${
            currentMode === 'SYNTHETIC'
              ? 'border-blue-500 bg-blue-50 shadow-md'
              : 'border-gray-200 bg-white hover:border-gray-300'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <div className="flex items-center gap-3 mb-3">
            <List size={24} className={currentMode === 'SYNTHETIC' ? 'text-blue-600' : 'text-gray-600'} />
            <div className="font-semibold text-lg">Mode Synthétique</div>
          </div>
          
          <p className="text-sm text-gray-600 mb-3">
            Saisie simplifiée avec valeurs moyennes mensuelles/annuelles.
          </p>
          
          <div className="space-y-1 text-xs text-gray-500">
            <div>✅ Rapide à remplir</div>
            <div>✅ Idéal pour revenus/dépenses stables</div>
            <div>✅ Recommandé pour salariés</div>
          </div>
        </button>

        {/* Mode DETAILED */}
        <button
          type="button"
          onClick={() => handleModeChange('DETAILED')}
          disabled={disabled}
          className={`p-6 rounded-lg border-2 transition-all text-left ${
            currentMode === 'DETAILED'
              ? 'border-blue-500 bg-blue-50 shadow-md'
              : 'border-gray-200 bg-white hover:border-gray-300'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <div className="flex items-center gap-3 mb-3">
            <Table size={24} className={currentMode === 'DETAILED' ? 'text-blue-600' : 'text-gray-600'} />
            <div className="font-semibold text-lg">Mode Détaillé</div>
          </div>
          
          <p className="text-sm text-gray-600 mb-3">
            Saisie période par période avec calcul automatique des moyennes.
          </p>
          
          <div className="space-y-1 text-xs text-gray-500">
            <div>✅ Analyse fine des variations</div>
            <div>✅ Détection tendances saisonnières</div>
            <div>✅ Obligatoire pour AGR/entreprises</div>
          </div>
        </button>
      </div>

      {/* Warning lors du changement */}
      {hasData && (
        <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
          <AlertCircle size={20} className="text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-yellow-800">
            <strong>Attention :</strong> Changer de mode convertira automatiquement vos données.
            Cette opération est réversible.
          </div>
        </div>
      )}
    </div>
  );
};
```

---

### 3. Composant Grille Période par Période

**Fichier**: `/workspace/frontend/src/components/financial-analysis/DetailedPeriodGrid.tsx`

```typescript
import React, { useState } from 'react';
import { Plus, Trash2, Calculator } from 'lucide-react';
import type { IncomePeriod, ExpensesPeriod, ExploitationPeriod } from '@/types/financialAnalysis';

interface DetailedPeriodGridProps<T> {
  title: string;
  periods: T[];
  onChange: (periods: T[]) => void;
  fields: {
    key: keyof T;
    label: string;
    type?: 'number' | 'text';
    suffix?: string;
  }[];
  createEmptyPeriod: (index: number) => T;
  disabled?: boolean;
  currency?: string;
}

export function DetailedPeriodGrid<T extends { period_label?: string }>({
  title,
  periods,
  onChange,
  fields,
  createEmptyPeriod,
  disabled = false,
  currency = 'XOF',
}: DetailedPeriodGridProps<T>) {
  const [showAverages, setShowAverages] = useState(true);

  const handlePeriodChange = (index: number, field: keyof T, value: any) => {
    const updated = [...periods];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
  };

  const handleAddPeriod = () => {
    const newPeriod = createEmptyPeriod(periods.length);
    onChange([...periods, newPeriod]);
  };

  const handleRemovePeriod = (index: number) => {
    if (periods.length <= 1) {
      alert('Vous devez conserver au moins une période.');
      return;
    }
    
    if (confirm('Supprimer cette période ?')) {
      const updated = periods.filter((_, i) => i !== index);
      onChange(updated);
    }
  };

  const calculateAverage = (field: keyof T): number => {
    if (periods.length === 0) return 0;
    
    const sum = periods.reduce((acc, period) => {
      const value = period[field];
      return acc + (typeof value === 'number' ? value : 0);
    }, 0);
    
    return sum / periods.length;
  };

  const calculateTotal = (field: keyof T): number => {
    return periods.reduce((acc, period) => {
      const value = period[field];
      return acc + (typeof value === 'number' ? value : 0);
    }, 0);
  };

  const formatMoney = (value: number): string => {
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value) + ' ' + currency;
  };

  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Calculator size={20} />
          {title}
        </h4>
        
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowAverages(!showAverages)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {showAverages ? 'Masquer' : 'Afficher'} les moyennes
          </button>
          
          <button
            type="button"
            onClick={handleAddPeriod}
            disabled={disabled}
            className="btn btn-sm btn-secondary flex items-center gap-2"
          >
            <Plus size={16} />
            Ajouter période
          </button>
        </div>
      </div>

      {/* Grille horizontale scrollable */}
      <div className="overflow-x-auto">
        <table className="min-w-full border border-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="sticky left-0 z-10 bg-gray-50 px-4 py-3 text-left text-sm font-semibold text-gray-900 border-r border-gray-200">
                Rubrique
              </th>
              
              {periods.map((period, index) => (
                <th
                  key={index}
                  className="px-4 py-3 text-center text-sm font-medium text-gray-900 border-r border-gray-200 min-w-[180px]"
                >
                  <input
                    type="text"
                    value={period.period_label || `Période ${index + 1}`}
                    onChange={(e) => handlePeriodChange(index, 'period_label' as keyof T, e.target.value)}
                    disabled={disabled}
                    className="w-full text-center bg-transparent border-none focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
                  />
                  
                  <button
                    type="button"
                    onClick={() => handleRemovePeriod(index)}
                    disabled={disabled || periods.length <= 1}
                    className="mt-1 text-red-500 hover:text-red-700 disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Supprimer période"
                  >
                    <Trash2 size={14} />
                  </button>
                </th>
              ))}
              
              {showAverages && (
                <>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-blue-900 bg-blue-50 border-r border-gray-200 min-w-[150px]">
                    Moyenne
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-green-900 bg-green-50 border-r border-gray-200 min-w-[150px]">
                    Total
                  </th>
                </>
              )}
            </tr>
          </thead>
          
          <tbody>
            {fields.map((field, fieldIndex) => (
              <tr
                key={String(field.key)}
                className={fieldIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
              >
                <td className="sticky left-0 z-10 px-4 py-3 text-sm font-medium text-gray-900 border-r border-gray-200 bg-inherit">
                  {field.label}
                </td>
                
                {periods.map((period, periodIndex) => (
                  <td key={periodIndex} className="px-4 py-3 border-r border-gray-200">
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={period[field.key] as any || ''}
                      onChange={(e) =>
                        handlePeriodChange(
                          periodIndex,
                          field.key,
                          e.target.value === '' ? 0 : parseFloat(e.target.value)
                        )
                      }
                      disabled={disabled}
                      className="w-full text-right px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    />
                  </td>
                ))}
                
                {showAverages && (
                  <>
                    <td className="px-4 py-3 text-sm text-right font-medium text-blue-900 bg-blue-50 border-r border-gray-200">
                      {formatMoney(calculateAverage(field.key))}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-semibold text-green-900 bg-green-50 border-r border-gray-200">
                      {formatMoney(calculateTotal(field.key))}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Aide */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-xs text-blue-800">
          💡 <strong>Info :</strong> Les moyennes et totaux sont calculés automatiquement.
          Les valeurs synthétiques seront mises à jour lors de la sauvegarde.
        </p>
      </div>
    </div>
  );
}
```

---

### 4. Intégration dans FinancialAnalysisForm

**Fichier**: `/workspace/frontend/src/components/FinancialAnalysisForm.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { AnalysisModeSelector } from './financial-analysis/AnalysisModeSelector';
import { DetailedPeriodGrid } from './financial-analysis/DetailedPeriodGrid';
import { IndividualSalarySection } from './financial-analysis/IndividualSalarySection';
// ... autres imports

export const FinancialAnalysisForm: React.FC<FinancialAnalysisFormProps> = ({
  creditApplicationId,
  clientType,
  existingData,
  onSave,
  onCancel,
  disabled = false,
}) => {
  const [formData, setFormData] = useState<Partial<FinancialAnalysis>>({
    credit_application: creditApplicationId,
    analysis_mode: existingData?.analysis_mode || 'SYNTHETIC',
    banking_observation_period_months: 3,
    detailed_data: existingData?.detailed_data || {
      num_periods: 3,
      income_detail: [],
      expenses_detail: [],
      exploitation_detail: [],
      banking_detail: [],
      collective_detail: [],
    },
    ...existingData,
  });

  const handleModeChange = (newMode: AnalysisMode) => {
    if (newMode === 'DETAILED' && formData.analysis_mode === 'SYNTHETIC') {
      // Conversion SYNTHETIC → DETAILED
      convertSyntheticToDetailed();
    }
    
    setFormData(prev => ({ ...prev, analysis_mode: newMode }));
  };

  const convertSyntheticToDetailed = () => {
    const numPeriods = 3;  // Par défaut, 3 périodes
    
    // Créer les périodes avec répartition uniforme
    const income_detail: IncomePeriod[] = Array.from({ length: numPeriods }, (_, i) => ({
      period_label: `Mois ${i + 1}`,
      salary_income: formData.salary_income || 0,
      spouse_income: formData.spouse_income || 0,
      rental_income: formData.rental_income || 0,
      other_activity_income: formData.other_activity_income || 0,
      other_income: formData.other_income || 0,
    }));

    const expenses_detail: ExpensesPeriod[] = Array.from({ length: numPeriods }, (_, i) => ({
      period_label: `Mois ${i + 1}`,
      rent_expense: formData.rent_expense || 0,
      food_expense: formData.food_expense || 0,
      utilities_expense: formData.utilities_expense || 0,
      transport_expense: formData.transport_expense || 0,
      education_expense: formData.education_expense || 0,
      health_expense: formData.health_expense || 0,
      other_household_expenses: formData.other_household_expenses || 0,
      tontine_expense: formData.tontine_expense || 0,
      social_contributions: formData.social_contributions || 0,
      family_support_expense: formData.family_support_expense || 0,
    }));

    setFormData(prev => ({
      ...prev,
      detailed_data: {
        num_periods: numPeriods,
        income_detail,
        expenses_detail,
        exploitation_detail: [],
        banking_detail: [],
        collective_detail: [],
      },
    }));
  };

  const renderFormSection = () => {
    const type = clientType.toUpperCase();
    
    if (formData.analysis_mode === 'DETAILED') {
      // Mode DETAILED: Afficher grilles période par période
      if (type === 'INDIVIDUAL' || type.includes('PHYSIQUE')) {
        return (
          <>
            <DetailedPeriodGrid
              title="Revenus par période"
              periods={formData.detailed_data?.income_detail || []}
              onChange={(periods) =>
                setFormData(prev => ({
                  ...prev,
                  detailed_data: {
                    ...prev.detailed_data,
                    income_detail: periods,
                  },
                }))
              }
              fields={[
                { key: 'salary_income', label: 'Salaire net' },
                { key: 'spouse_income', label: 'Revenu conjoint' },
                { key: 'rental_income', label: 'Revenus locatifs' },
                { key: 'other_activity_income', label: 'Autres activités' },
                { key: 'other_income', label: 'Autres revenus' },
              ]}
              createEmptyPeriod={createEmptyIncomePeriod}
              disabled={disabled || isSaving}
              currency="XOF"
            />

            <DetailedPeriodGrid
              title="Dépenses par période"
              periods={formData.detailed_data?.expenses_detail || []}
              onChange={(periods) =>
                setFormData(prev => ({
                  ...prev,
                  detailed_data: {
                    ...prev.detailed_data,
                    expenses_detail: periods,
                  },
                }))
              }
              fields={[
                { key: 'rent_expense', label: 'Loyer' },
                { key: 'food_expense', label: 'Alimentation' },
                { key: 'utilities_expense', label: 'Eau/Élec/Tel' },
                { key: 'transport_expense', label: 'Transport' },
                { key: 'education_expense', label: 'Scolarité' },
                { key: 'health_expense', label: 'Santé' },
                { key: 'other_household_expenses', label: 'Autres charges' },
                { key: 'tontine_expense', label: 'Tontines' },
                { key: 'social_contributions', label: 'Cotisations sociales' },
                { key: 'family_support_expense', label: 'Soutien familial' },
              ]}
              createEmptyPeriod={createEmptyExpensesPeriod}
              disabled={disabled || isSaving}
              currency="XOF"
            />
          </>
        );
      }
      
      // Similaire pour CORPORATE et GROUP...
    } else {
      // Mode SYNTHETIC: Afficher formulaires classiques
      return renderSyntheticForm();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border border-blue-200">
        {/* ... */}
      </div>

      {/* Sélecteur de mode */}
      <AnalysisModeSelector
        currentMode={formData.analysis_mode || 'SYNTHETIC'}
        onChange={handleModeChange}
        disabled={disabled || isSaving}
        hasData={hasExistingData()}
      />

      {/* Formulaire dynamique */}
      {renderFormSection()}

      {/* Boutons d'action */}
      <div className="flex items-center justify-between gap-4 pt-6 border-t border-gray-200">
        {/* ... */}
      </div>
    </form>
  );
};
```

---

### 5. Validation Backend JSON Schema

**Fichier**: `/workspace/backend/apps/credits/serializers.py`

```python
from rest_framework import serializers
from decimal import Decimal

class FinancialAnalysisSerializer(serializers.ModelSerializer):
    # ... champs existants
    
    def validate_detailed_data(self, value):
        """Valide la structure JSON du mode DETAILED."""
        if not value:
            return value
        
        if not isinstance(value, dict):
            raise serializers.ValidationError("Format JSON invalide")
        
        # Vérifier num_periods
        num_periods = value.get('num_periods')
        if num_periods is not None and (not isinstance(num_periods, int) or num_periods < 1):
            raise serializers.ValidationError("num_periods doit être un entier positif")
        
        # Valider chaque section
        errors = {}
        
        # Revenus (income_detail)
        if 'income_detail' in value:
            income_errors = self._validate_periods_list(
                value['income_detail'],
                'income_detail',
                allowed_fields=['period_label', 'salary_income', 'spouse_income', 
                               'rental_income', 'other_activity_income', 'other_income',
                               'activity_turnover', 'activity_expenses']
            )
            if income_errors:
                errors['income_detail'] = income_errors
        
        # Dépenses (expenses_detail)
        if 'expenses_detail' in value:
            expenses_errors = self._validate_periods_list(
                value['expenses_detail'],
                'expenses_detail',
                allowed_fields=['period_label', 'rent_expense', 'food_expense', 
                               'utilities_expense', 'transport_expense', 'education_expense',
                               'health_expense', 'other_household_expenses', 'tontine_expense',
                               'social_contributions', 'family_support_expense']
            )
            if expenses_errors:
                errors['expenses_detail'] = expenses_errors
        
        # Exploitation (exploitation_detail)
        if 'exploitation_detail' in value:
            exploitation_errors = self._validate_periods_list(
                value['exploitation_detail'],
                'exploitation_detail',
                allowed_fields=['period_label', 'turnover', 'cogs', 'op_rent', 
                               'op_salaries', 'op_utilities', 'op_transport', 'op_telecom',
                               'op_taxes', 'op_maintenance', 'op_other', 'depreciation',
                               'financial_charges']
            )
            if exploitation_errors:
                errors['exploitation_detail'] = exploitation_errors
        
        # Mouvements bancaires (banking_detail)
        if 'banking_detail' in value:
            banking_errors = self._validate_periods_list(
                value['banking_detail'],
                'banking_detail',
                allowed_fields=['period_label', 'credit_movements', 'debit_movements']
            )
            if banking_errors:
                errors['banking_detail'] = banking_errors
        
        # Contributions collectives (collective_detail)
        if 'collective_detail' in value:
            collective_errors = self._validate_periods_list(
                value['collective_detail'],
                'collective_detail',
                allowed_fields=['period_label', 'collective_contributions', 
                               'collective_other_income', 'collective_operating_expenses']
            )
            if collective_errors:
                errors['collective_detail'] = collective_errors
        
        if errors:
            raise serializers.ValidationError(errors)
        
        return value
    
    def _validate_periods_list(self, periods, section_name, allowed_fields):
        """Valide une liste de périodes."""
        if not isinstance(periods, list):
            return f"{section_name} doit être une liste"
        
        errors = []
        for i, period in enumerate(periods):
            if not isinstance(period, dict):
                errors.append(f"Période {i+1}: format invalide (dict attendu)")
                continue
            
            # Vérifier les champs
            for key, value in period.items():
                if key not in allowed_fields:
                    errors.append(f"Période {i+1}: champ '{key}' non autorisé")
                    continue
                
                # Valider les valeurs numériques
                if key != 'period_label' and value is not None:
                    if not isinstance(value, (int, float, Decimal)):
                        errors.append(f"Période {i+1}.{key}: valeur numérique attendue")
                    elif value < 0:
                        errors.append(f"Période {i+1}.{key}: valeur négative non autorisée")
        
        return errors if errors else None
    
    def validate(self, attrs):
        # ... validation existante
        
        # Valider cohérence mode/données
        analysis_mode = attrs.get('analysis_mode', self.instance.analysis_mode if self.instance else 'SYNTHETIC')
        detailed_data = attrs.get('detailed_data', {})
        
        if analysis_mode == 'DETAILED':
            # En mode DETAILED, au moins une section doit avoir des données
            has_data = any([
                detailed_data.get('income_detail'),
                detailed_data.get('expenses_detail'),
                detailed_data.get('exploitation_detail'),
                detailed_data.get('banking_detail'),
                detailed_data.get('collective_detail'),
            ])
            
            if not has_data:
                raise serializers.ValidationError({
                    'detailed_data': 'En mode DETAILED, au moins une section doit contenir des données'
                })
        
        return super().validate(attrs)
```

---

### 6. Endpoint de Conversion Backend

**Fichier**: `/workspace/backend/apps/credits/views.py`

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

class FinancialAnalysisViewSet(TenantScopedViewSet):
    # ... code existant
    
    @action(detail=True, methods=['post'])
    def convert_to_detailed(self, request, pk=None):
        """Convertit une analyse SYNTHETIC en DETAILED."""
        analysis = self.get_object()
        self._assert_mutable(analysis)
        
        if analysis.analysis_mode == self.serializer_class.Meta.model.AnalysisMode.DETAILED:
            return Response(
                {"detail": "L'analyse est déjà en mode détaillé"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Nombre de périodes (3 par défaut)
        num_periods = request.data.get('num_periods', 3)
        if not isinstance(num_periods, int) or num_periods < 1 or num_periods > 12:
            return Response(
                {"detail": "num_periods doit être entre 1 et 12"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer les périodes avec répartition uniforme
        detailed_data = {
            'num_periods': num_periods,
        }
        
        # Revenus (INDIVIDUAL)
        if analysis.is_individual:
            detailed_data['income_detail'] = [
                {
                    'period_label': f'Mois {i+1}',
                    'salary_income': float(analysis.salary_income or 0),
                    'spouse_income': float(analysis.spouse_income or 0),
                    'rental_income': float(analysis.rental_income or 0),
                    'other_activity_income': float(analysis.other_activity_income or 0),
                    'other_income': float(analysis.other_income or 0),
                }
                for i in range(num_periods)
            ]
            
            detailed_data['expenses_detail'] = [
                {
                    'period_label': f'Mois {i+1}',
                    'rent_expense': float(analysis.rent_expense or 0),
                    'food_expense': float(analysis.food_expense or 0),
                    'utilities_expense': float(analysis.utilities_expense or 0),
                    'transport_expense': float(analysis.transport_expense or 0),
                    'education_expense': float(analysis.education_expense or 0),
                    'health_expense': float(analysis.health_expense or 0),
                    'other_household_expenses': float(analysis.other_household_expenses or 0),
                    'tontine_expense': float(analysis.tontine_expense or 0),
                    'social_contributions': float(analysis.social_contributions or 0),
                    'family_support_expense': float(analysis.family_support_expense or 0),
                }
                for i in range(num_periods)
            ]
        
        # Exploitation (CORPORATE)
        if analysis.is_corporate:
            # Répartir le CA annuel sur les trimestres par défaut
            detailed_data['exploitation_detail'] = [
                {
                    'period_label': f'Trimestre {i+1}',
                    'turnover': float(analysis.turnover or 0) / num_periods,
                    'cogs': float(analysis.cogs or 0) / num_periods,
                    'op_rent': float(analysis.op_rent or 0) / num_periods,
                    'op_salaries': float(analysis.op_salaries or 0) / num_periods,
                    'op_utilities': float(analysis.op_utilities or 0) / num_periods,
                    'op_transport': float(analysis.op_transport or 0) / num_periods,
                    'op_telecom': float(analysis.op_telecom or 0) / num_periods,
                    'op_taxes': float(analysis.op_taxes or 0) / num_periods,
                    'op_maintenance': float(analysis.op_maintenance or 0) / num_periods,
                    'op_other': float(analysis.op_other or 0) / num_periods,
                    'depreciation': float(analysis.depreciation or 0) / num_periods,
                    'financial_charges': float(analysis.financial_charges or 0) / num_periods,
                }
                for i in range(num_periods)
            ]
        
        # Groupement (PROFESSIONAL)
        if analysis.is_groupement:
            detailed_data['collective_detail'] = [
                {
                    'period_label': f'Mois {i+1}',
                    'collective_contributions': float(analysis.collective_contributions or 0),
                    'collective_other_income': float(analysis.collective_other_income or 0),
                    'collective_operating_expenses': float(analysis.collective_operating_expenses or 0),
                }
                for i in range(num_periods)
            ]
        
        # Appliquer la conversion
        analysis.analysis_mode = analysis.AnalysisMode.DETAILED
        analysis.detailed_data = detailed_data
        analysis.save()
        
        return Response(self.get_serializer(analysis).data)
    
    @action(detail=True, methods=['post'])
    def convert_to_synthetic(self, request, pk=None):
        """Convertit une analyse DETAILED en SYNTHETIC."""
        analysis = self.get_object()
        self._assert_mutable(analysis)
        
        if analysis.analysis_mode == analysis.AnalysisMode.SYNTHETIC:
            return Response(
                {"detail": "L'analyse est déjà en mode synthétique"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Le calcul des moyennes est automatique dans save()
        # Il suffit de changer le mode
        analysis.analysis_mode = analysis.AnalysisMode.SYNTHETIC
        analysis.save()
        
        return Response(self.get_serializer(analysis).data)
```

---

## ✅ TESTS

### Test Unitaire Backend

**Fichier**: `/workspace/backend/apps/credits/tests/test_detailed_mode.py`

```python
import pytest
from decimal import Decimal
from apps.credits.models import FinancialAnalysis
from apps.credits.serializers import FinancialAnalysisSerializer

@pytest.mark.django_db
class TestDetailedMode:
    
    def test_compute_synthetic_from_detailed_income(self, financial_analysis):
        """Test calcul moyennes revenus depuis périodes détaillées."""
        detailed_data = {
            'num_periods': 3,
            'income_detail': [
                {'period_label': 'Mois 1', 'salary_income': 100000, 'spouse_income': 50000},
                {'period_label': 'Mois 2', 'salary_income': 120000, 'spouse_income': 50000},
                {'period_label': 'Mois 3', 'salary_income': 110000, 'spouse_income': 50000},
            ],
        }
        
        financial_analysis.analysis_mode = FinancialAnalysis.AnalysisMode.DETAILED
        financial_analysis.detailed_data = detailed_data
        financial_analysis.save()
        
        # Vérifier les moyennes calculées
        assert financial_analysis.salary_income == Decimal('110000')  # (100+120+110)/3
        assert financial_analysis.spouse_income == Decimal('50000')
    
    def test_validate_detailed_data_structure(self):
        """Test validation structure JSON detailed_data."""
        serializer = FinancialAnalysisSerializer()
        
        # Structure valide
        valid_data = {
            'num_periods': 2,
            'income_detail': [
                {'period_label': 'Mois 1', 'salary_income': 100000},
                {'period_label': 'Mois 2', 'salary_income': 120000},
            ],
        }
        result = serializer.validate_detailed_data(valid_data)
        assert result == valid_data
        
        # Structure invalide: income_detail n'est pas une liste
        with pytest.raises(ValidationError):
            serializer.validate_detailed_data({
                'income_detail': 'invalid',
            })
        
        # Structure invalide: valeur négative
        with pytest.raises(ValidationError):
            serializer.validate_detailed_data({
                'income_detail': [
                    {'period_label': 'Mois 1', 'salary_income': -50000},
                ],
            })
    
    def test_conversion_synthetic_to_detailed(self, api_client, financial_analysis):
        """Test endpoint de conversion SYNTHETIC → DETAILED."""
        financial_analysis.analysis_mode = FinancialAnalysis.AnalysisMode.SYNTHETIC
        financial_analysis.salary_income = Decimal('100000')
        financial_analysis.save()
        
        url = f'/api/financial-analyses/{financial_analysis.id}/convert_to_detailed/'
        response = api_client.post(url, {'num_periods': 3})
        
        assert response.status_code == 200
        data = response.json()
        assert data['analysis_mode'] == 'DETAILED'
        assert len(data['detailed_data']['income_detail']) == 3
        assert all(
            period['salary_income'] == 100000.0
            for period in data['detailed_data']['income_detail']
        )
```

---

## 📊 CHECKLIST D'IMPLÉMENTATION

### Phase 1: Types et Composants (Jour 1)

- [ ] Corriger types TypeScript (`financialAnalysis.ts`)
- [ ] Créer `AnalysisModeSelector.tsx`
- [ ] Créer `DetailedPeriodGrid.tsx`
- [ ] Ajouter helpers `createEmptyXPeriod`

### Phase 2: Intégration (Jour 2)

- [ ] Intégrer sélecteur dans `FinancialAnalysisForm`
- [ ] Implémenter conversion frontend SYNTHETIC → DETAILED
- [ ] Tester affichage grilles période par période
- [ ] Valider calcul moyennes en temps réel

### Phase 3: Backend (Jour 2-3)

- [ ] Ajouter validation JSON Schema
- [ ] Créer endpoint `convert_to_detailed`
- [ ] Créer endpoint `convert_to_synthetic`
- [ ] Tests unitaires validation
- [ ] Tests unitaires calculs

### Phase 4: Tests E2E (Jour 3)

- [ ] Test workflow SYNTHETIC complet
- [ ] Test workflow DETAILED complet
- [ ] Test conversion SYNTHETIC → DETAILED
- [ ] Test conversion DETAILED → SYNTHETIC
- [ ] Test calcul moyennes automatiques

---

## 🎯 RÉSULTAT ATTENDU

Après implémentation:

- ✅ Mode DETAILED utilisable
- ✅ Conversion bidirectionnelle fonctionnelle
- ✅ Validation complète des données
- ✅ UX fluide et intuitive
- ✅ Tests automatisés complets

**Impact**: Fonctionnalité majeure restaurée, workflow complet pour AGR et entreprises.

---

**Document créé le**: 25 septembre 2026  
**Prochaine Review**: Après implémentation Phase 1

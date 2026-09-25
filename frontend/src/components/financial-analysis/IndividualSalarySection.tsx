import React from 'react';
import { FieldModeToggle } from '../FieldModeToggle';
import { DetailedInputGrid } from '../DetailedInputGrid';
import type { AnalysisMode, FinancialAnalysis } from '../../types/financialAnalysis';

interface IndividualSalarySectionProps {
  data: Partial<FinancialAnalysis>;
  onChange: (updates: Partial<FinancialAnalysis>) => void;
  disabled?: boolean;
}

export const IndividualSalarySection: React.FC<IndividualSalarySectionProps> = ({
  data,
  onChange,
  disabled = false,
}) => {
  const mode = data.analysis_mode || 'SYNTHETIC';
  const periods = data.banking_observation_period_months || 3;

  const handleModeChange = (newMode: AnalysisMode) => {
    if (disabled) return;
    
    if (newMode !== mode) {
      const confirmed = window.confirm(
        `Changer de mode ${mode === 'SYNTHETIC' ? 'Synthétique' : 'Détaillé'} vers ${
          newMode === 'SYNTHETIC' ? 'Synthétique' : 'Détaillé'
        } ? ${
          newMode === 'DETAILED'
            ? 'Les valeurs synthétiques seront réparties uniformément sur les périodes.'
            : 'Les données détaillées seront moyennées.'
        }`
      );
      
      if (confirmed) {
        onChange({ analysis_mode: newMode });
      }
    }
  };

  const handleIncomeDetailChange = (periodIndex: number, fieldKey: string, value: number) => {
    const currentDetail = data.detailed_data?.income_detail || Array(periods).fill({});
    const updatedDetail = [...currentDetail];
    updatedDetail[periodIndex] = {
      ...updatedDetail[periodIndex],
      [fieldKey]: value,
    };
    onChange({
      detailed_data: {
        ...data.detailed_data,
        income_detail: updatedDetail,
      },
    });
  };

  const handleExpensesDetailChange = (periodIndex: number, fieldKey: string, value: number) => {
    const currentDetail = data.detailed_data?.expenses_detail || Array(periods).fill({});
    const updatedDetail = [...currentDetail];
    updatedDetail[periodIndex] = {
      ...updatedDetail[periodIndex],
      [fieldKey]: value,
    };
    onChange({
      detailed_data: {
        ...data.detailed_data,
        expenses_detail: updatedDetail,
      },
    });
  };

  const incomeFields = [
    { key: 'salary_income', label: 'Salaire net', format: 'money' as const },
    { key: 'spouse_income', label: 'Revenu conjoint', format: 'money' as const },
    { key: 'other_income', label: 'Autres revenus', format: 'money' as const },
    { key: 'rental_income', label: 'Revenus locatifs', format: 'money' as const },
  ];

  const expensesFields = [
    { key: 'rent_expense', label: 'Loyer', format: 'money' as const },
    { key: 'food_expense', label: 'Alimentation', format: 'money' as const },
    { key: 'transport_expense', label: 'Transport', format: 'money' as const },
    { key: 'education_expense', label: 'Éducation', format: 'money' as const },
    { key: 'health_expense', label: 'Santé', format: 'money' as const },
    { key: 'utilities_expense', label: 'Énergie/Eau', format: 'money' as const },
    { key: 'other_household_expenses', label: 'Autres dépenses', format: 'money' as const },
  ];

  const periodLabels = Array.from({ length: periods }, (_, i) => `Mois ${i + 1}`);
  const incomeValues = (data.detailed_data?.income_detail || Array(periods).fill({})) as Record<string, number>[];
  const expensesValues = (data.detailed_data?.expenses_detail || Array(periods).fill({})) as Record<string, number>[];

  return (
    <div className="space-y-6">
      {/* Mode Toggle */}
      <FieldModeToggle mode={mode} onModeChange={handleModeChange} disabled={disabled} />

      {/* Contexte employeur */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Contexte professionnel</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Employeur <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={data.employer_name || ''}
              onChange={(e) => onChange({ employer_name: e.target.value })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              placeholder="Nom de l'employeur"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type de contrat <span className="text-red-500">*</span>
            </label>
            <select
              value={data.contract_type || ''}
              onChange={(e) => onChange({ contract_type: e.target.value })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              required
            >
              <option value="">Sélectionner...</option>
              <option value="CDI">CDI (Contrat à Durée Indéterminée)</option>
              <option value="CDD">CDD (Contrat à Durée Déterminée)</option>
              <option value="INTERIM">Intérim</option>
              <option value="FONCTION_PUBLIQUE">Fonction publique</option>
              <option value="STAGE">Stage</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Personnes à charge
            </label>
            <input
              type="number"
              min="0"
              value={data.dependents_count || 0}
              onChange={(e) => onChange({ dependents_count: parseInt(e.target.value) || 0 })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Statut du logement
            </label>
            <select
              value={data.premises_status || ''}
              onChange={(e) => onChange({ premises_status: e.target.value })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
            >
              <option value="">Sélectionner...</option>
              <option value="PROPRIETAIRE">Propriétaire</option>
              <option value="LOCATAIRE">Locataire</option>
              <option value="HEBERGE">Hébergé</option>
              <option value="AUTRE">Autre</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Période d'observation (mois) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min="1"
              max="12"
              value={data.banking_observation_period_months || 3}
              onChange={(e) => onChange({ banking_observation_period_months: parseInt(e.target.value) || 3 })}
              disabled={disabled || mode === 'DETAILED'}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              required
            />
            {mode === 'DETAILED' && (
              <p className="text-xs text-gray-500 mt-1">
                En mode détaillé, le nombre de périodes est déterminé par les données saisies.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Revenus */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">💰 Revenus mensuels</h3>
        
        {mode === 'SYNTHETIC' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Salaire net moyen <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.salary_income || ''}
                onChange={(e) => onChange({ salary_income: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Revenu conjoint moyen
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.spouse_income || ''}
                onChange={(e) => onChange({ spouse_income: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Autres revenus moyens
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.other_income || ''}
                onChange={(e) => onChange({ other_income: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Revenus locatifs moyens
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.rental_income || ''}
                onChange={(e) => onChange({ rental_income: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
          </div>
        ) : (
          <DetailedInputGrid
            periods={periods}
            periodLabels={periodLabels}
            fields={incomeFields}
            values={incomeValues}
            onChange={handleIncomeDetailChange}
          />
        )}
      </div>

      {/* Dépenses */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">💸 Dépenses mensuelles</h3>
        
        {mode === 'SYNTHETIC' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Loyer moyen
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.rent_expense || ''}
                onChange={(e) => onChange({ rent_expense: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Alimentation moyenne
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.food_expense || ''}
                onChange={(e) => onChange({ food_expense: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Transport moyen
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.transport_expense || ''}
                onChange={(e) => onChange({ transport_expense: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Éducation moyenne
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.education_expense || ''}
                onChange={(e) => onChange({ education_expense: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Santé moyenne
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.health_expense || ''}
                onChange={(e) => onChange({ health_expense: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Énergie/Eau moyenne
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.utilities_expense || ''}
                onChange={(e) => onChange({ utilities_expense: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Autres dépenses moyennes
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.other_household_expenses || ''}
                onChange={(e) => onChange({ other_household_expenses: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Montant moyen"
              />
            </div>
          </div>
        ) : (
          <DetailedInputGrid
            periods={periods}
            periodLabels={periodLabels}
            fields={expensesFields}
            values={expensesValues}
            onChange={handleExpensesDetailChange}
          />
        )}
      </div>

      {/* Capacité de remboursement calculée */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">📊 Capacité de remboursement estimée</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Revenus totaux:</span>
            <span className="ml-2 font-medium text-gray-900">
              {((data.salary_income || 0) + (data.spouse_income || 0) + (data.other_income || 0) + (data.rental_income || 0)).toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Dépenses totales:</span>
            <span className="ml-2 font-medium text-gray-900">
              {((data.rent_expense || 0) + (data.food_expense || 0) + (data.transport_expense || 0) + (data.education_expense || 0) + (data.health_expense || 0) + (data.utilities_expense || 0) + (data.other_household_expenses || 0)).toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Reste à vivre:</span>
            <span className="ml-2 font-bold text-green-700">
              {(
                ((data.salary_income || 0) + (data.spouse_income || 0) + (data.other_income || 0) + (data.rental_income || 0)) -
                ((data.rent_expense || 0) + (data.food_expense || 0) + (data.transport_expense || 0) + (data.education_expense || 0) + (data.health_expense || 0) + (data.utilities_expense || 0) + (data.other_household_expenses || 0))
              ).toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

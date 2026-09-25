import React from 'react';
import { FieldModeToggle } from '../FieldModeToggle';
import { DetailedInputGrid } from '../DetailedInputGrid';
import type { AnalysisMode, FinancialAnalysis } from '../../types/financialAnalysis';

interface CorporateSectionProps {
  data: Partial<FinancialAnalysis>;
  onChange: (updates: Partial<FinancialAnalysis>) => void;
  disabled?: boolean;
}

export const CorporateSection: React.FC<CorporateSectionProps> = ({
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

  const handleExploitationDetailChange = (periodIndex: number, fieldKey: string, value: number) => {
    const currentDetail = data.detailed_data?.exploitation_detail || Array(periods).fill({});
    const updatedDetail = [...currentDetail];
    updatedDetail[periodIndex] = {
      ...updatedDetail[periodIndex],
      [fieldKey]: value,
    };
    onChange({
      detailed_data: {
        ...data.detailed_data,
        exploitation_detail: updatedDetail,
      },
    });
  };

  const handleBankingDetailChange = (periodIndex: number, fieldKey: string, value: number) => {
    const currentDetail = data.detailed_data?.banking_detail || Array(periods).fill({});
    const updatedDetail = [...currentDetail];
    updatedDetail[periodIndex] = {
      ...updatedDetail[periodIndex],
      [fieldKey]: value,
    };
    onChange({
      detailed_data: {
        ...data.detailed_data,
        banking_detail: updatedDetail,
      },
    });
  };

  const exploitationFields = [
    { key: 'turnover', label: 'Chiffre d\'affaires', format: 'money' as const },
    { key: 'purchases', label: 'Achats', format: 'money' as const },
    { key: 'inventory_start', label: 'Stock début', format: 'money' as const },
    { key: 'inventory_end', label: 'Stock fin', format: 'money' as const },
    { key: 'operating_expenses', label: 'Charges exploitation', format: 'money' as const },
    { key: 'staff_costs', label: 'Charges personnel', format: 'money' as const },
  ];

  const bankingFields = [
    { key: 'credit_movements', label: 'Flux créditeurs', format: 'money' as const },
    { key: 'debit_movements', label: 'Flux débiteurs', format: 'money' as const },
    { key: 'average_balance', label: 'Solde moyen', format: 'money' as const },
  ];

  const periodLabels = Array.from({ length: periods }, (_, i) => `Mois ${i + 1}`);
  const exploitationValues = (data.detailed_data?.exploitation_detail || Array(periods).fill({})) as Record<string, number>[];
  const bankingValues = (data.detailed_data?.banking_detail || Array(periods).fill({})) as Record<string, number>[];

  const calculateGrossMargin = () => {
    const turnover = data.turnover || 0;
    const cogs = data.cost_of_goods_sold || 0;
    return turnover - cogs;
  };

  const calculateEBITDA = () => {
    const grossMargin = calculateGrossMargin();
    const operatingExpenses = data.operating_expenses || 0;
    const staffCosts = data.staff_costs || 0;
    return grossMargin - operatingExpenses - staffCosts;
  };

  return (
    <div className="space-y-6">
      {/* Mode Toggle */}
      <FieldModeToggle mode={mode} onModeChange={handleModeChange} disabled={disabled} />

      {/* Environnement commercial */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Environnement commercial</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Clientèle cible <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={data.clientele || ''}
              onChange={(e) => onChange({ clientele: e.target.value })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              placeholder="Ex: Particuliers, B2B, Administration..."
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Zone de chalandise
            </label>
            <select
              value={data.catchment_area || ''}
              onChange={(e) => onChange({ catchment_area: e.target.value })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
            >
              <option value="">Sélectionner...</option>
              <option value="LOCALE">Locale</option>
              <option value="REGIONALE">Régionale</option>
              <option value="NATIONALE">Nationale</option>
              <option value="INTERNATIONALE">Internationale</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Régime fiscal
            </label>
            <select
              value={data.tax_regime || ''}
              onChange={(e) => onChange({ tax_regime: e.target.value })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
            >
              <option value="">Sélectionner...</option>
              <option value="REEL_SIMPLIFIE">Réel simplifié</option>
              <option value="REEL_NORMAL">Réel normal</option>
              <option value="MICRO_ENTREPRISE">Micro-entreprise</option>
              <option value="AUTRE">Autre</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Statut des locaux
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
              <option value="BAIL_COMMERCIAL">Bail commercial</option>
              <option value="AUTRE">Autre</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Délai moyen de paiement clients (jours)
            </label>
            <input
              type="number"
              min="0"
              value={data.avg_client_payment_days || ''}
              onChange={(e) => onChange({ avg_client_payment_days: parseInt(e.target.value) || 0 })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              placeholder="Ex: 30"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Délai moyen de paiement fournisseurs (jours)
            </label>
            <input
              type="number"
              min="0"
              value={data.avg_supplier_payment_days || ''}
              onChange={(e) => onChange({ avg_supplier_payment_days: parseInt(e.target.value) || 0 })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              placeholder="Ex: 60"
            />
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

      {/* Exploitation */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">💼 Compte d'exploitation</h3>
        
        {mode === 'SYNTHETIC' ? (
          <div className="space-y-6">
            {/* Chiffre d'affaires et marge */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Revenus</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Chiffre d'affaires moyen <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={data.turnover || ''}
                    onChange={(e) => onChange({ turnover: parseFloat(e.target.value) || 0 })}
                    disabled={disabled}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    placeholder="Montant moyen mensuel"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Coût des biens vendus moyen
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={data.cost_of_goods_sold || ''}
                    onChange={(e) => onChange({ cost_of_goods_sold: parseFloat(e.target.value) || 0 })}
                    disabled={disabled}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    placeholder="COGS"
                  />
                </div>
              </div>
            </div>

            {/* Stocks */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Gestion des stocks</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Achats moyens
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={data.purchases || ''}
                    onChange={(e) => onChange({ purchases: parseFloat(e.target.value) || 0 })}
                    disabled={disabled}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Stock initial moyen
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={data.inventory_start || ''}
                    onChange={(e) => onChange({ inventory_start: parseFloat(e.target.value) || 0 })}
                    disabled={disabled}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Stock final moyen
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={data.inventory_end || ''}
                    onChange={(e) => onChange({ inventory_end: parseFloat(e.target.value) || 0 })}
                    disabled={disabled}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                  />
                </div>
              </div>
            </div>

            {/* Charges */}
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Charges</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Charges d'exploitation moyennes
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={data.operating_expenses || ''}
                    onChange={(e) => onChange({ operating_expenses: parseFloat(e.target.value) || 0 })}
                    disabled={disabled}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    placeholder="Loyer, énergie, fournitures..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Charges de personnel moyennes
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={data.staff_costs || ''}
                    onChange={(e) => onChange({ staff_costs: parseFloat(e.target.value) || 0 })}
                    disabled={disabled}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    placeholder="Salaires, charges sociales..."
                  />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <DetailedInputGrid
            periods={periods}
            periodLabels={periodLabels}
            fields={exploitationFields}
            values={exploitationValues}
            onChange={handleExploitationDetailChange}
          />
        )}
      </div>

      {/* Relation bancaire */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">🏦 Analyse de la relation bancaire</h3>
        
        {mode === 'SYNTHETIC' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Flux créditeurs moyens mensuels
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.avg_monthly_credit_movements || ''}
                onChange={(e) => onChange({ avg_monthly_credit_movements: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Total des entrées"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Flux débiteurs moyens mensuels
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.avg_monthly_debit_movements || ''}
                onChange={(e) => onChange({ avg_monthly_debit_movements: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Total des sorties"
              />
            </div>
          </div>
        ) : (
          <DetailedInputGrid
            periods={periods}
            periodLabels={periodLabels}
            fields={bankingFields}
            values={bankingValues}
            onChange={handleBankingDetailChange}
          />
        )}
      </div>

      {/* Indicateurs clés calculés */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">📊 Indicateurs clés de performance</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-600">CA moyen:</span>
            <span className="ml-2 font-medium text-gray-900">
              {(data.turnover || 0).toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Marge brute:</span>
            <span className="ml-2 font-medium text-gray-900">
              {calculateGrossMargin().toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">EBITDA:</span>
            <span className="ml-2 font-bold text-green-700">
              {calculateEBITDA().toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Taux de marge:</span>
            <span className="ml-2 font-medium text-blue-700">
              {data.turnover && data.turnover > 0
                ? ((calculateGrossMargin() / data.turnover) * 100).toFixed(1)
                : '0'}
              %
            </span>
          </div>
          <div>
            <span className="text-gray-600">DSO (jours):</span>
            <span className="ml-2 font-medium text-gray-900">
              {data.avg_client_payment_days || 0}
            </span>
          </div>
          <div>
            <span className="text-gray-600">DPO (jours):</span>
            <span className="ml-2 font-medium text-gray-900">
              {data.avg_supplier_payment_days || 0}
            </span>
          </div>
          <div>
            <span className="text-gray-600">BFR estimé:</span>
            <span className="ml-2 font-medium text-orange-700">
              {(
                ((data.turnover || 0) * (data.avg_client_payment_days || 0)) / 30 -
                ((data.cost_of_goods_sold || 0) * (data.avg_supplier_payment_days || 0)) / 30
              ).toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Rotation stock:</span>
            <span className="ml-2 font-medium text-gray-900">
              {data.inventory_end && data.inventory_end > 0 && data.cost_of_goods_sold
                ? ((data.cost_of_goods_sold * 12) / data.inventory_end).toFixed(1)
                : 'N/A'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

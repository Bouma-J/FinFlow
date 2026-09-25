import React from 'react';
import { FieldModeToggle } from '../FieldModeToggle';
import { DetailedInputGrid } from '../DetailedInputGrid';
import type { AnalysisMode, FinancialAnalysis } from '../../types/financialAnalysis';

interface GroupSectionProps {
  data: Partial<FinancialAnalysis>;
  onChange: (updates: Partial<FinancialAnalysis>) => void;
  disabled?: boolean;
}

export const GroupSection: React.FC<GroupSectionProps> = ({
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

  const handleCollectiveDetailChange = (periodIndex: number, fieldKey: string, value: number) => {
    const currentDetail = data.detailed_data?.collective_detail || Array(periods).fill({});
    const updatedDetail = [...currentDetail];
    updatedDetail[periodIndex] = {
      ...updatedDetail[periodIndex],
      [fieldKey]: value,
    };
    onChange({
      detailed_data: {
        ...data.detailed_data,
        collective_detail: updatedDetail,
      },
    });
  };

  const collectiveFields = [
    { key: 'contributions', label: 'Cotisations', format: 'money' as const },
    { key: 'collective_savings', label: 'Épargne collective', format: 'money' as const },
    { key: 'solidarity_fund', label: 'Fonds de solidarité', format: 'money' as const },
  ];

  const periodLabels = Array.from({ length: periods }, (_, i) => `Mois ${i + 1}`);
  const collectiveValues = (data.detailed_data?.collective_detail || Array(periods).fill({})) as Record<string, number>[];

  const calculateTotalResources = () => {
    return (
      (data.collective_contributions || 0) +
      (data.collective_savings || 0) +
      (data.solidarity_fund || 0)
    );
  };

  const calculateAverageContributionPerMember = () => {
    const members = data.member_count || 1;
    return (data.collective_contributions || 0) / members;
  };

  return (
    <div className="space-y-6">
      {/* Mode Toggle */}
      <FieldModeToggle mode={mode} onModeChange={handleModeChange} disabled={disabled} />

      {/* Structure du groupement */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Structure du groupement</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type de groupement <span className="text-red-500">*</span>
            </label>
            <select
              value={data.group_structure || ''}
              onChange={(e) => onChange({ group_structure: e.target.value })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              required
            >
              <option value="">Sélectionner...</option>
              <option value="COOPERATIVE">Coopérative</option>
              <option value="ASSOCIATION">Association</option>
              <option value="GIE">Groupement d'Intérêt Économique (GIE)</option>
              <option value="TONTINE">Tontine</option>
              <option value="GROUPEMENT_AGRICOLE">Groupement agricole</option>
              <option value="GROUPEMENT_FEMMES">Groupement de femmes</option>
              <option value="AUTRE">Autre</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nombre de membres <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              min="2"
              value={data.member_count || ''}
              onChange={(e) => onChange({ member_count: parseInt(e.target.value) || 0 })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              placeholder="Nombre de membres actifs"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Zone d'activité
            </label>
            <select
              value={data.catchment_area || ''}
              onChange={(e) => onChange({ catchment_area: e.target.value })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
            >
              <option value="">Sélectionner...</option>
              <option value="VILLAGE">Village</option>
              <option value="COMMUNE">Commune</option>
              <option value="DEPARTEMENT">Département</option>
              <option value="REGION">Région</option>
              <option value="NATIONALE">Nationale</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Secteur d'activité principal
            </label>
            <input
              type="text"
              value={data.clientele || ''}
              onChange={(e) => onChange({ clientele: e.target.value })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              placeholder="Ex: Agriculture, Artisanat, Commerce..."
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

      {/* Finances collectives */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">💰 Finances collectives</h3>
        
        {mode === 'SYNTHETIC' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cotisations moyennes mensuelles <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.collective_contributions || ''}
                onChange={(e) => onChange({ collective_contributions: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Total des cotisations"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                Total collecté auprès de tous les membres
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Épargne collective moyenne mensuelle
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.collective_savings || ''}
                onChange={(e) => onChange({ collective_savings: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Épargne accumulée"
              />
              <p className="text-xs text-gray-500 mt-1">
                Montant épargné pour projets collectifs
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fonds de solidarité moyen mensuel
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={data.solidarity_fund || ''}
                onChange={(e) => onChange({ solidarity_fund: parseFloat(e.target.value) || 0 })}
                disabled={disabled}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                placeholder="Fonds d'entraide"
              />
              <p className="text-xs text-gray-500 mt-1">
                Fonds d'aide mutuelle et solidarité
              </p>
            </div>
          </div>
        ) : (
          <DetailedInputGrid
            periods={periods}
            periodLabels={periodLabels}
            fields={collectiveFields}
            values={collectiveValues}
            onChange={handleCollectiveDetailChange}
          />
        )}
      </div>

      {/* Activité du groupement (optionnel) */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">💼 Activité économique (optionnel)</h3>
        <p className="text-sm text-gray-600 mb-4">
          Si le groupement exerce une activité économique collective (production, commercialisation...)
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Chiffre d'affaires collectif moyen
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={data.turnover || ''}
              onChange={(e) => onChange({ turnover: parseFloat(e.target.value) || 0 })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              placeholder="Revenus des activités collectives"
            />
          </div>
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
              placeholder="Frais de fonctionnement"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Achats collectifs moyens
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={data.purchases || ''}
              onChange={(e) => onChange({ purchases: parseFloat(e.target.value) || 0 })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              placeholder="Achats mutualisés"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Stock collectif moyen
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={data.inventory_end || ''}
              onChange={(e) => onChange({ inventory_end: parseFloat(e.target.value) || 0 })}
              disabled={disabled}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
              placeholder="Valeur du stock"
            />
          </div>
        </div>
      </div>

      {/* Relation bancaire */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">🏦 Relation bancaire collective</h3>
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
              placeholder="Total des entrées sur le compte"
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
              placeholder="Total des sorties du compte"
            />
          </div>
        </div>
      </div>

      {/* Indicateurs de solidité du groupement */}
      <div className="bg-green-50 p-4 rounded-lg border border-green-200">
        <h4 className="text-sm font-semibold text-green-900 mb-2">📊 Indicateurs de solidité du groupement</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Membres actifs:</span>
            <span className="ml-2 font-bold text-gray-900">
              {data.member_count || 0}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Ressources totales:</span>
            <span className="ml-2 font-bold text-green-700">
              {calculateTotalResources().toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Cotisation/membre:</span>
            <span className="ml-2 font-medium text-blue-700">
              {calculateAverageContributionPerMember().toFixed(2)}
            </span>
          </div>
          <div>
            <span className="text-gray-600">Taux d'épargne:</span>
            <span className="ml-2 font-medium text-purple-700">
              {data.collective_contributions && data.collective_contributions > 0
                ? (((data.collective_savings || 0) / data.collective_contributions) * 100).toFixed(1)
                : '0'}
              %
            </span>
          </div>
          {data.turnover && data.turnover > 0 && (
            <>
              <div>
                <span className="text-gray-600">CA collectif:</span>
                <span className="ml-2 font-medium text-gray-900">
                  {data.turnover.toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-gray-600">CA/membre:</span>
                <span className="ml-2 font-medium text-orange-700">
                  {(data.turnover / (data.member_count || 1)).toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-gray-600">Marge nette:</span>
                <span className="ml-2 font-bold text-green-700">
                  {(data.turnover - (data.operating_expenses || 0) - (data.purchases || 0)).toFixed(2)}
                </span>
              </div>
              <div>
                <span className="text-gray-600">Marge/membre:</span>
                <span className="ml-2 font-medium text-green-700">
                  {((data.turnover - (data.operating_expenses || 0) - (data.purchases || 0)) / (data.member_count || 1)).toFixed(2)}
                </span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Note d'information */}
      <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
        <div className="flex items-start gap-2">
          <span className="text-yellow-600 text-lg">ℹ️</span>
          <div className="text-sm text-yellow-800">
            <strong>Note importante:</strong> Pour les groupements, l'analyse financière évalue la capacité collective
            de remboursement. Les ressources régulières (cotisations, épargne) et la solidarité entre membres sont
            des facteurs clés de la décision de crédit.
          </div>
        </div>
      </div>
    </div>
  );
};

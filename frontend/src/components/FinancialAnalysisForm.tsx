import React, { useState, useEffect } from 'react';
import { IndividualSalarySection } from './financial-analysis/IndividualSalarySection';
import { IndividualBusinessSection } from './financial-analysis/IndividualBusinessSection';
import { CorporateSection } from './financial-analysis/CorporateSection';
import { GroupSection } from './financial-analysis/GroupSection';
import type { FinancialAnalysis } from '../types/financialAnalysis';

interface FinancialAnalysisFormProps {
  creditApplicationId: string | number;
  clientType: string;
  existingData?: Partial<FinancialAnalysis>;
  onSave?: (data: Partial<FinancialAnalysis>) => Promise<void>;
  onCancel?: () => void;
  disabled?: boolean;
}

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
    analysis_mode: 'SYNTHETIC',
    banking_observation_period_months: 3,
    ...existingData,
  });

  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (existingData) {
      setFormData({
        credit_application: creditApplicationId,
        analysis_mode: 'SYNTHETIC',
        banking_observation_period_months: 3,
        ...existingData,
      });
    }
  }, [existingData, creditApplicationId]);

  const handleFormUpdate = (updates: Partial<FinancialAnalysis>) => {
    setFormData((prev) => ({
      ...prev,
      ...updates,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!onSave) return;

    setIsSaving(true);
    setSaveError(null);

    try {
      await onSave(formData);
    } catch (error) {
      console.error('Error saving financial analysis:', error);
      setSaveError(
        error instanceof Error
          ? error.message
          : 'Une erreur est survenue lors de l\'enregistrement'
      );
    } finally {
      setIsSaving(false);
    }
  };

  const getClientTypeLabel = () => {
    const type = clientType.toUpperCase();
    if (type === 'INDIVIDUAL' || type.includes('PHYSIQUE')) {
      return 'Personne Physique';
    } else if (type === 'CORPORATE' || type.includes('MORALE') || type.includes('ENTREPRISE')) {
      return 'Personne Morale (Entreprise)';
    } else if (type === 'GROUP' || type.includes('GROUPEMENT') || type.includes('COOPERATIVE')) {
      return 'Groupement / Coopérative';
    }
    return 'Type de client inconnu';
  };

  const getClientTypeIcon = () => {
    const type = clientType.toUpperCase();
    if (type === 'INDIVIDUAL' || type.includes('PHYSIQUE')) {
      return '👤';
    } else if (type === 'CORPORATE' || type.includes('MORALE') || type.includes('ENTREPRISE')) {
      return '🏢';
    } else if (type === 'GROUP' || type.includes('GROUPEMENT') || type.includes('COOPERATIVE')) {
      return '👥';
    }
    return '❓';
  };

  const renderFormSection = () => {
    const type = clientType.toUpperCase();
    
    // For INDIVIDUAL, we need to determine if it's salary or business
    // This should ideally come from the credit application data
    // For now, we'll check if they have employer_name (salary) or clientele (business)
    if (type === 'INDIVIDUAL' || type.includes('PHYSIQUE')) {
      // Simple heuristic: if employer_name exists or is being filled, show salary form
      // If clientele exists and no employer_name, show business form
      const hasSalaryData = formData.employer_name || formData.salary_income;
      const hasBusinessData = formData.clientele || formData.turnover;
      
      if (hasBusinessData && !hasSalaryData) {
        return (
          <IndividualBusinessSection
            data={formData}
            onChange={handleFormUpdate}
            disabled={disabled || isSaving}
          />
        );
      } else {
        // Default to salary section for individuals
        return (
          <IndividualSalarySection
            data={formData}
            onChange={handleFormUpdate}
            disabled={disabled || isSaving}
          />
        );
      }
    }

    if (type === 'CORPORATE' || type.includes('MORALE') || type.includes('ENTREPRISE')) {
      return (
        <CorporateSection
          data={formData}
          onChange={handleFormUpdate}
          disabled={disabled || isSaving}
        />
      );
    }

    if (type === 'GROUP' || type.includes('GROUPEMENT') || type.includes('COOPERATIVE')) {
      return (
        <GroupSection
          data={formData}
          onChange={handleFormUpdate}
          disabled={disabled || isSaving}
        />
      );
    }

    return (
      <div className="bg-red-50 p-6 rounded-lg border border-red-200">
        <p className="text-red-700">
          Type de client non reconnu: {clientType}
        </p>
      </div>
    );
  };

  // Show type selector for INDIVIDUAL clients
  const type = clientType.toUpperCase();
  const shouldShowTypeSelector = type === 'INDIVIDUAL' || type.includes('PHYSIQUE');
  const currentIndividualType = formData.employer_name || formData.salary_income ? 'SALARY' : 'BUSINESS';

  const handleIndividualTypeChange = (type: 'SALARY' | 'BUSINESS') => {
    if (type !== currentIndividualType) {
      const confirmed = window.confirm(
        `Changer le type d'analyse de ${
          currentIndividualType === 'SALARY' ? 'Salarié' : 'Activité Génératrice de Revenu'
        } vers ${type === 'SALARY' ? 'Salarié' : 'Activité Génératrice de Revenu'} ? Les données existantes seront conservées si possibles.`
      );
      
      if (confirmed) {
        // Clear type-specific fields
        if (type === 'SALARY') {
          // Switching to salary, clear business-specific fields
          setFormData((prev) => ({
            ...prev,
            turnover: undefined,
            cost_of_goods_sold: undefined,
            operating_expenses: undefined,
            staff_costs: undefined,
            purchases: undefined,
            inventory_start: undefined,
            inventory_end: undefined,
          }));
        } else {
          // Switching to business, clear salary-specific fields
          setFormData((prev) => ({
            ...prev,
            employer_name: undefined,
            contract_type: undefined,
            salary_income: undefined,
            spouse_income: undefined,
            pension_income: undefined,
            investment_income: undefined,
          }));
        }
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border border-blue-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              {getClientTypeIcon()} Analyse Financière
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Type de client : <span className="font-semibold">{getClientTypeLabel()}</span>
            </p>
            {formData.analysis_mode && (
              <p className="text-xs text-gray-500 mt-1">
                Mode : <span className="font-medium">{formData.analysis_mode === 'SYNTHETIC' ? 'Synthétique (Moyennes)' : 'Détaillé (Période par période)'}</span>
              </p>
            )}
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-600">Dossier de crédit</div>
            <div className="text-lg font-bold text-blue-700">#{creditApplicationId}</div>
          </div>
        </div>
      </div>

      {/* Individual Type Selector (only for INDIVIDUAL clients) */}
      {shouldShowTypeSelector && (
        <div className="bg-white p-6 rounded-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Type d'analyse pour personne physique</h3>
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => handleIndividualTypeChange('SALARY')}
              disabled={disabled || isSaving}
              className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                currentIndividualType === 'SALARY'
                  ? 'border-blue-500 bg-blue-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              } ${disabled || isSaving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div className="text-3xl mb-2">💼</div>
              <div className="font-semibold text-gray-900">Salarié</div>
              <div className="text-xs text-gray-600 mt-1">
                Revenus fixes, employeur identifié
              </div>
            </button>
            <button
              type="button"
              onClick={() => handleIndividualTypeChange('BUSINESS')}
              disabled={disabled || isSaving}
              className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                currentIndividualType === 'BUSINESS'
                  ? 'border-blue-500 bg-blue-50 shadow-md'
                  : 'border-gray-200 bg-white hover:border-gray-300'
              } ${disabled || isSaving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <div className="text-3xl mb-2">🛒</div>
              <div className="font-semibold text-gray-900">Activité Génératrice de Revenu (AGR)</div>
              <div className="text-xs text-gray-600 mt-1">
                Commerce, artisanat, agriculture...
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {saveError && (
        <div className="bg-red-50 p-4 rounded-lg border border-red-200">
          <div className="flex items-start gap-2">
            <span className="text-red-500 text-xl">⚠️</span>
            <div>
              <p className="font-semibold text-red-900">Erreur lors de l'enregistrement</p>
              <p className="text-sm text-red-700 mt-1">{saveError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Dynamic Form Section */}
      {renderFormSection()}

      {/* Action Buttons */}
      <div className="flex items-center justify-between gap-4 pt-6 border-t border-gray-200">
        <div className="text-sm text-gray-500">
          {formData.updated_at && (
            <span>Dernière modification : {new Date(formData.updated_at).toLocaleString('fr-FR')}</span>
          )}
        </div>
        <div className="flex gap-3">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              disabled={isSaving}
              className="px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Annuler
            </button>
          )}
          <button
            type="submit"
            disabled={disabled || isSaving}
            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSaving ? (
              <>
                <span className="animate-spin">⏳</span>
                Enregistrement...
              </>
            ) : (
              <>
                <span>💾</span>
                Enregistrer l'analyse
              </>
            )}
          </button>
        </div>
      </div>

      {/* Help Information */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <div className="flex items-start gap-2">
          <span className="text-blue-600 text-lg">💡</span>
          <div className="text-sm text-blue-800">
            <strong>Aide :</strong> L'analyse financière doit être complète avant de pouvoir soumettre le dossier de crédit.
            Utilisez le mode <strong>Synthétique</strong> pour une saisie rapide avec des moyennes, ou le mode <strong>Détaillé</strong> pour
            un suivi période par période qui calculera automatiquement les moyennes.
          </div>
        </div>
      </div>
    </form>
  );
};

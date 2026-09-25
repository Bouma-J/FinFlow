import React from 'react';
import { X, User, Building2, Users, TrendingUp, TrendingDown, Wallet, ShoppingCart, type LucideIcon } from 'lucide-react';
import type { FinancialAnalysis } from '../api/types';

interface FinancialAnalysisDetailsModalProps {
  analysis: FinancialAnalysis;
  currency: string;
  onClose: () => void;
}

export const FinancialAnalysisDetailsModal: React.FC<FinancialAnalysisDetailsModalProps> = ({
  analysis,
  currency,
  onClose,
}) => {
  const isCorp = analysis.client_type === 'CORPORATE';
  const isGroup = analysis.client_type === 'PROFESSIONAL';
  const isIndividual = !isCorp && !isGroup;

  const formatMoney = (value: string | number | null | undefined): string => {
    if (value === null || value === undefined || value === '') return '—';
    const num = typeof value === 'string' ? parseFloat(value) : value;
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(num) + ' ' + currency;
  };

  const formatNumber = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '—';
    return value.toString();
  };

  // Check if we have detailed period data
  const hasDetailedData = !!analysis.detailed_data;
  const detailedData = hasDetailedData ? (typeof analysis.detailed_data === 'string' ? JSON.parse(analysis.detailed_data) : analysis.detailed_data) : null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        className="modal-content" 
        style={{ maxWidth: '1200px', maxHeight: '90vh', overflow: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1.5rem',
          borderBottom: '1px solid #e5e7eb',
          position: 'sticky',
          top: 0,
          backgroundColor: 'white',
          zIndex: 10,
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
              Détails de l'analyse financière
            </h2>
            <p style={{ margin: '0.25rem 0 0 0', color: '#6b7280', fontSize: '0.875rem' }}>
              {isCorp ? '🏢 Entreprise' : isGroup ? '👥 Groupement' : '👤 Particulier'} · 
              Mode {analysis.analysis_mode === 'DETAILED' ? 'Détaillé' : 'Synthétique'} ·
              Période d'observation : {analysis.banking_observation_period_months || 3} mois
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              borderRadius: '0.375rem',
            }}
            className="hover-bg"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '1.5rem' }}>
          {/* Context Section */}
          <Section 
            title="Contexte" 
            icon={isIndividual ? User : isCorp ? Building2 : Users}
          >
            <Table>
              <tbody>
                {isIndividual && (
                  <>
                    <TableRow label="Employeur" value={analysis.employer_name || '—'} />
                    <TableRow label="Type de contrat" value={analysis.contract_type || '—'} />
                    <TableRow label="Personnes à charge" value={formatNumber(analysis.dependents_count)} />
                    <TableRow label="Statut du logement" value={analysis.premises_status || '—'} />
                  </>
                )}
                {isCorp && (
                  <>
                    <TableRow label="Clientèle cible" value={analysis.clientele || '—'} />
                    <TableRow label="Zone de chalandise" value={analysis.catchment_area || '—'} />
                    <TableRow label="Régime fiscal" value={analysis.tax_regime || '—'} />
                    <TableRow label="Statut des locaux" value={analysis.premises_status || '—'} />
                    <TableRow label="Délai paiement clients (jours)" value={formatNumber(analysis.avg_client_payment_days)} />
                    <TableRow label="Délai paiement fournisseurs (jours)" value={formatNumber(analysis.avg_supplier_payment_days)} />
                  </>
                )}
                {isGroup && (
                  <>
                    <TableRow label="Type de groupement" value={analysis.group_structure || '—'} />
                    <TableRow label="Nombre de membres" value={formatNumber(analysis.member_count)} />
                    <TableRow label="Zone d'activité" value={analysis.catchment_area || '—'} />
                    <TableRow label="Secteur d'activité" value={analysis.clientele || '—'} />
                  </>
                )}
                <TableRow 
                  label="Période d'observation" 
                  value={`${analysis.banking_observation_period_months || 3} mois`} 
                />
              </tbody>
            </Table>
          </Section>

          {/* Income/Revenue Section */}
          {isIndividual && (
            <Section title="Revenus mensuels" icon={TrendingUp}>
              {analysis.analysis_mode === 'DETAILED' && detailedData?.income_detail ? (
                <DetailedTable
                  periods={detailedData.income_detail}
                  fields={[
                    { key: 'salary_income', label: 'Salaire net' },
                    { key: 'spouse_income', label: 'Revenu conjoint' },
                    { key: 'other_income', label: 'Autres revenus' },
                    { key: 'rental_income', label: 'Revenus locatifs' },
                  ]}
                  currency={currency}
                />
              ) : (
                <Table>
                  <tbody>
                    <TableRow label="Salaire net moyen" value={formatMoney(analysis.salary_income)} />
                    <TableRow label="Revenu conjoint moyen" value={formatMoney(analysis.spouse_income)} />
                    <TableRow label="Autres revenus moyens" value={formatMoney(analysis.other_income)} />
                    <TableRow label="Revenus locatifs moyens" value={formatMoney(analysis.rental_income)} />
                    <TableRow 
                      label="Total revenus" 
                      value={formatMoney(analysis.total_income)} 
                      emphasized 
                    />
                  </tbody>
                </Table>
              )}
            </Section>
          )}

          {/* Expenses Section */}
          {isIndividual && (
            <Section title="Dépenses mensuelles" icon={TrendingDown}>
              {analysis.analysis_mode === 'DETAILED' && detailedData?.expenses_detail ? (
                <DetailedTable
                  periods={detailedData.expenses_detail}
                  fields={[
                    { key: 'rent_expense', label: 'Loyer' },
                    { key: 'food_expense', label: 'Alimentation' },
                    { key: 'transport_expense', label: 'Transport' },
                    { key: 'education_expense', label: 'Éducation' },
                    { key: 'health_expense', label: 'Santé' },
                    { key: 'utilities_expense', label: 'Énergie/Eau' },
                    { key: 'other_household_expenses', label: 'Autres dépenses' },
                  ]}
                  currency={currency}
                />
              ) : (
                <Table>
                  <tbody>
                    <TableRow label="Loyer moyen" value={formatMoney(analysis.rent_expense)} />
                    <TableRow label="Alimentation moyenne" value={formatMoney(analysis.food_expense)} />
                    <TableRow label="Transport moyen" value={formatMoney(analysis.transport_expense)} />
                    <TableRow label="Éducation moyenne" value={formatMoney(analysis.education_expense)} />
                    <TableRow label="Santé moyenne" value={formatMoney(analysis.health_expense)} />
                    <TableRow label="Énergie/Eau moyenne" value={formatMoney(analysis.utilities_expense)} />
                    <TableRow label="Autres dépenses moyennes" value={formatMoney(analysis.other_household_expenses)} />
                    <TableRow 
                      label="Total charges" 
                      value={formatMoney(analysis.total_household_charges)} 
                      emphasized 
                    />
                  </tbody>
                </Table>
              )}
            </Section>
          )}

          {/* Exploitation Section (Corporate & Individual Business) */}
          {(isCorp || (isIndividual && analysis.turnover)) && (
            <Section title="Compte d'exploitation" icon={ShoppingCart}>
              {analysis.analysis_mode === 'DETAILED' && detailedData?.exploitation_detail ? (
                <DetailedTable
                  periods={detailedData.exploitation_detail}
                  fields={[
                    { key: 'turnover', label: 'Chiffre d\'affaires' },
                    { key: 'cogs', label: 'Coût biens vendus' },
                    { key: 'op_rent', label: 'Loyer professionnel' },
                    { key: 'op_salaries', label: 'Salaires' },
                    { key: 'op_utilities', label: 'Énergie/Eau' },
                    { key: 'op_transport', label: 'Transport' },
                    { key: 'op_telecom', label: 'Télécom' },
                    { key: 'op_taxes', label: 'Taxes' },
                    { key: 'op_maintenance', label: 'Maintenance' },
                    { key: 'op_other', label: 'Autres charges' },
                  ]}
                  currency={currency}
                />
              ) : (
                <Table>
                  <tbody>
                    <TableRow label="Chiffre d'affaires moyen" value={formatMoney(analysis.turnover)} />
                    <TableRow label="Coût des biens vendus" value={formatMoney(analysis.cogs)} />
                    <TableRow label="Loyer professionnel" value={formatMoney(analysis.op_rent)} />
                    <TableRow label="Salaires" value={formatMoney(analysis.op_salaries)} />
                    <TableRow label="Énergie/Eau" value={formatMoney(analysis.op_utilities)} />
                    <TableRow label="Transport" value={formatMoney(analysis.op_transport)} />
                    <TableRow label="Télécom" value={formatMoney(analysis.op_telecom)} />
                    <TableRow label="Taxes" value={formatMoney(analysis.op_taxes)} />
                    <TableRow label="Maintenance" value={formatMoney(analysis.op_maintenance)} />
                    <TableRow label="Autres charges" value={formatMoney(analysis.op_other)} />
                    <TableRow 
                      label="Marge brute" 
                      value={formatMoney(analysis.gross_margin)} 
                      emphasized 
                    />
                    <TableRow 
                      label="EBE (EBITDA)" 
                      value={formatMoney(analysis.ebe)} 
                      emphasized 
                    />
                  </tbody>
                </Table>
              )}
            </Section>
          )}

          {/* Group Finances Section */}
          {isGroup && (
            <Section title="Finances collectives" icon={Wallet}>
              {analysis.analysis_mode === 'DETAILED' && detailedData?.collective_detail ? (
                <DetailedTable
                  periods={detailedData.collective_detail}
                  fields={[
                    { key: 'contributions', label: 'Cotisations' },
                    { key: 'collective_savings', label: 'Épargne collective' },
                    { key: 'solidarity_fund', label: 'Fonds de solidarité' },
                  ]}
                  currency={currency}
                />
              ) : (
                <Table>
                  <tbody>
                    <TableRow label="Cotisations moyennes" value={formatMoney(analysis.collective_contributions)} />
                    <TableRow label="Épargne collective" value={formatMoney(analysis.collective_savings)} />
                    <TableRow label="Fonds de solidarité" value={formatMoney(analysis.solidarity_fund)} />
                    <TableRow 
                      label="Ressources totales" 
                      value={formatMoney(
                        (parseFloat(analysis.collective_contributions || '0') +
                         parseFloat(analysis.collective_savings || '0') +
                         parseFloat(analysis.solidarity_fund || '0')).toString()
                      )} 
                      emphasized 
                    />
                  </tbody>
                </Table>
              )}
            </Section>
          )}

          {/* Banking Movements Section */}
          <Section title="Mouvements bancaires" icon={Wallet}>
            {analysis.analysis_mode === 'DETAILED' && detailedData?.banking_detail ? (
              <DetailedTable
                periods={detailedData.banking_detail}
                fields={[
                  { key: 'credit_movements', label: 'Flux créditeurs' },
                  { key: 'debit_movements', label: 'Flux débiteurs' },
                  { key: 'average_balance', label: 'Solde moyen' },
                ]}
                currency={currency}
              />
            ) : (
              <Table>
                <tbody>
                  <TableRow 
                    label="Flux créditeurs moyens mensuels" 
                    value={formatMoney(analysis.avg_monthly_credit_movements)} 
                  />
                  <TableRow 
                    label="Flux débiteurs moyens mensuels" 
                    value={formatMoney(analysis.avg_monthly_debit_movements)} 
                  />
                </tbody>
              </Table>
            )}
          </Section>

          {/* Capacity Summary */}
          <Section title="Capacité de remboursement" icon={TrendingUp}>
            <Table>
              <tbody>
                {isIndividual && (
                  <>
                    <TableRow label="Total revenus" value={formatMoney(analysis.total_income)} />
                    <TableRow label="Total charges" value={formatMoney(analysis.total_household_charges)} />
                    <TableRow 
                      label="Reste à vivre" 
                      value={formatMoney(analysis.disposable_income)} 
                      emphasized 
                    />
                  </>
                )}
                {isCorp && (
                  <>
                    <TableRow label="EBE (EBITDA)" value={formatMoney(analysis.ebe)} />
                    <TableRow 
                      label="Cash-flow" 
                      value={formatMoney(analysis.cash_flow)} 
                      emphasized 
                    />
                  </>
                )}
                {isGroup && (
                  <TableRow 
                    label="Capacité collective" 
                    value={formatMoney(analysis.collective_capacity)} 
                    emphasized 
                  />
                )}
                <TableRow 
                  label="Capacité de remboursement" 
                  value={formatMoney(analysis.repayment_capacity)} 
                  emphasized 
                />
                <TableRow 
                  label="Taux d'endettement" 
                  value={analysis.debt_ratio ? `${Number(analysis.debt_ratio).toFixed(1)} %` : '—'} 
                  emphasized 
                />
              </tbody>
            </Table>
          </Section>
        </div>

        {/* Footer */}
        <div style={{
          padding: '1rem 1.5rem',
          borderTop: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'flex-end',
          position: 'sticky',
          bottom: 0,
          backgroundColor: 'white',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1.5rem',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
};

// Helper Components

interface SectionProps {
  title: string;
  icon: LucideIcon;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, icon: Icon, children }) => (
  <div style={{ marginBottom: '2rem' }}>
    <h3 style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      fontSize: '1.125rem',
      fontWeight: 600,
      marginBottom: '1rem',
      color: '#1f2937',
    }}>
      <Icon size={20} />
      {title}
    </h3>
    {children}
  </div>
);

interface TableProps {
  children: React.ReactNode;
}

const Table: React.FC<TableProps> = ({ children }) => (
  <table style={{
    width: '100%',
    borderCollapse: 'collapse',
    backgroundColor: 'white',
    border: '1px solid #e5e7eb',
    borderRadius: '0.5rem',
    overflow: 'hidden',
  }}>
    {children}
  </table>
);

interface TableRowProps {
  label: string;
  value: string;
  emphasized?: boolean;
}

const TableRow: React.FC<TableRowProps> = ({ label, value, emphasized = false }) => (
  <tr style={{
    borderBottom: '1px solid #f3f4f6',
    backgroundColor: emphasized ? '#f0f9ff' : 'transparent',
  }}>
    <td style={{
      padding: '0.75rem 1rem',
      fontWeight: emphasized ? 600 : 500,
      color: '#374151',
      width: '50%',
    }}>
      {label}
    </td>
    <td style={{
      padding: '0.75rem 1rem',
      textAlign: 'right',
      fontWeight: emphasized ? 700 : 400,
      color: emphasized ? '#1e40af' : '#1f2937',
    }}>
      {value}
    </td>
  </tr>
);

interface DetailedTableProps {
  periods: any[];
  fields: { key: string; label: string }[];
  currency: string;
}

const DetailedTable: React.FC<DetailedTableProps> = ({ periods, fields, currency }) => {
  const formatMoney = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '—';
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value) + ' ' + currency;
  };

  const calculateAverage = (fieldKey: string): number => {
    const values = periods
      .map(p => parseFloat(p[fieldKey] || '0'))
      .filter(v => !isNaN(v) && v !== 0);
    return values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
  };

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{
        width: '100%',
        borderCollapse: 'collapse',
        backgroundColor: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: '0.5rem',
        fontSize: '0.875rem',
      }}>
        <thead>
          <tr style={{ backgroundColor: '#f9fafb', borderBottom: '2px solid #e5e7eb' }}>
            <th style={{
              padding: '0.75rem',
              textAlign: 'left',
              fontWeight: 600,
              color: '#374151',
              position: 'sticky',
              left: 0,
              backgroundColor: '#f9fafb',
            }}>
              Poste
            </th>
            {periods.map((_, idx) => (
              <th key={idx} style={{
                padding: '0.75rem',
                textAlign: 'right',
                fontWeight: 600,
                color: '#374151',
                minWidth: '120px',
              }}>
                {periods[idx].period_label || `Période ${idx + 1}`}
              </th>
            ))}
            <th style={{
              padding: '0.75rem',
              textAlign: 'right',
              fontWeight: 600,
              color: '#374151',
              backgroundColor: '#eff6ff',
              minWidth: '120px',
            }}>
              Moyenne
            </th>
          </tr>
        </thead>
        <tbody>
          {fields.map((field, fieldIdx) => (
            <tr key={field.key} style={{
              borderBottom: fieldIdx < fields.length - 1 ? '1px solid #e5e7eb' : 'none',
              backgroundColor: fieldIdx % 2 === 0 ? 'white' : '#f9fafb',
            }}>
              <td style={{
                padding: '0.75rem',
                fontWeight: 500,
                color: '#374151',
                position: 'sticky',
                left: 0,
                backgroundColor: fieldIdx % 2 === 0 ? 'white' : '#f9fafb',
              }}>
                {field.label}
              </td>
              {periods.map((period, periodIdx) => (
                <td key={periodIdx} style={{
                  padding: '0.75rem',
                  textAlign: 'right',
                  color: '#1f2937',
                }}>
                  {formatMoney(period[field.key])}
                </td>
              ))}
              <td style={{
                padding: '0.75rem',
                textAlign: 'right',
                fontWeight: 600,
                color: '#1f2937',
                backgroundColor: '#eff6ff',
              }}>
                {formatMoney(calculateAverage(field.key))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

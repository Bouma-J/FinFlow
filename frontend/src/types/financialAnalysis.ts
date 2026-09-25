/**
 * Types pour l'analyse financière avec support SYNTHETIC/DETAILED
 */

export type AnalysisMode = 'SYNTHETIC' | 'DETAILED';

export type ClientType = 'INDIVIDUAL' | 'CORPORATE' | 'GROUP';

/**
 * Structure des données détaillées par période pour les revenus
 */
export interface IncomePeriod {
  period_label?: string;
  salary_income?: number;
  other_income?: number;
  spouse_income?: number;
  rental_income?: number;
  pension_income?: number;
  investment_income?: number;
}

/**
 * Structure des données détaillées par période pour les dépenses
 */
export interface ExpensesPeriod {
  period_label?: string;
  rent?: number;
  food?: number;
  transport?: number;
  education?: number;
  health?: number;
  utilities?: number;
  other_expenses?: number;
}

/**
 * Structure des données détaillées par période pour l'exploitation (entreprises)
 */
export interface ExploitationPeriod {
  period_label?: string;
  turnover?: number;
  cost_of_goods_sold?: number;
  operating_expenses?: number;
  staff_costs?: number;
  inventory_start?: number;
  inventory_end?: number;
  purchases?: number;
}

/**
 * Structure des données détaillées par période pour les mouvements bancaires
 */
export interface BankingPeriod {
  period_label?: string;
  credit_movements?: number;
  debit_movements?: number;
  average_balance?: number;
}

/**
 * Structure des données détaillées par période pour les contributions collectives (groupements)
 */
export interface CollectivePeriod {
  period_label?: string;
  contributions?: number;
  collective_savings?: number;
  solidarity_fund?: number;
}

/**
 * Structure complète des données détaillées (JSON stocké dans detailed_data)
 */
export interface DetailedData {
  income_detail?: IncomePeriod[];
  expenses_detail?: ExpensesPeriod[];
  exploitation_detail?: ExploitationPeriod[];
  banking_detail?: BankingPeriod[];
  collective_detail?: CollectivePeriod[];
}

/**
 * Interface pour l'analyse financière complète
 */
export interface FinancialAnalysis {
  id?: number;
  credit_application?: string | number;
  analysis_mode: AnalysisMode;
  detailed_data?: DetailedData;
  
  // Champs de contexte (déplacés depuis CreditApplication)
  employer_name?: string;
  contract_type?: string;
  dependents_count?: number;
  premises_status?: string;
  tax_regime?: string;
  avg_client_payment_days?: number;
  avg_supplier_payment_days?: number;
  clientele?: string;
  catchment_area?: string;
  banking_observation_period_months?: number;
  
  // Revenus (synthétiques ou calculés automatiquement si mode DETAILED)
  salary_income?: number;
  other_income?: number;
  spouse_income?: number;
  rental_income?: number;
  pension_income?: number;
  investment_income?: number;
  total_income?: number;
  
  // Dépenses (synthétiques ou calculées automatiquement si mode DETAILED)
  rent?: number;
  food?: number;
  transport?: number;
  education?: number;
  health?: number;
  utilities?: number;
  other_expenses?: number;
  total_expenses?: number;
  
  // Exploitation (entreprises) - synthétiques ou calculés automatiquement si mode DETAILED
  turnover?: number;
  cost_of_goods_sold?: number;
  gross_margin?: number;
  operating_expenses?: number;
  staff_costs?: number;
  ebitda?: number;
  net_profit?: number;
  inventory_start?: number;
  inventory_end?: number;
  purchases?: number;
  
  // Mouvements bancaires - synthétiques ou calculés automatiquement si mode DETAILED
  avg_monthly_credit_movements?: number;
  avg_monthly_debit_movements?: number;
  
  // Contributions collectives (groupements) - synthétiques ou calculées automatiquement si mode DETAILED
  collective_contributions?: number;
  collective_savings?: number;
  solidarity_fund?: number;
  
  // Informations de gestion (groupement)
  member_count?: number;
  group_structure?: string;
  
  // Méta
  created_at?: string;
  updated_at?: string;
}

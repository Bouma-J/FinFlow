/**
 * Types pour l'analyse financière avec support SYNTHETIC/DETAILED
 */

export type AnalysisMode = 'SYNTHETIC' | 'DETAILED';

export type ClientType = 'INDIVIDUAL' | 'CORPORATE' | 'GROUP';

/**
 * Structure des données détaillées par période pour les revenus (INDIVIDUAL)
 */
export interface IncomePeriod {
  period_label?: string;
  
  // Revenus salariés
  salary_income?: number;
  spouse_income?: number;
  rental_income?: number;
  other_activity_income?: number;
  other_income?: number;
  
  // Activité génératrice de revenu (AGR)
  activity_turnover?: number;
  activity_expenses?: number;
}

/**
 * Structure des données détaillées par période pour les dépenses (INDIVIDUAL)
 */
export interface ExpensesPeriod {
  period_label?: string;
  
  // Dépenses ménage
  rent_expense?: number;
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
  
  // Revenus & coûts
  turnover?: number;
  cogs?: number;  // cost_of_goods_sold
  
  // Charges d'exploitation détaillées
  op_rent?: number;
  op_salaries?: number;
  op_utilities?: number;
  op_transport?: number;
  op_telecom?: number;
  op_taxes?: number;
  op_maintenance?: number;
  op_other?: number;
  
  // Amortissement & charges financières
  depreciation?: number;
  financial_charges?: number;
  
  // Stocks
  stock_value?: number;
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
 * Helper functions pour créer des périodes vides
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

export const createEmptyBankingPeriod = (index: number): BankingPeriod => ({
  period_label: `Période ${index + 1}`,
  credit_movements: 0,
  debit_movements: 0,
  average_balance: 0,
});

export const createEmptyCollectivePeriod = (index: number): CollectivePeriod => ({
  period_label: `Période ${index + 1}`,
  contributions: 0,
  collective_savings: 0,
  solidarity_fund: 0,
});

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
  rent_expense?: number;
  food_expense?: number;
  transport_expense?: number;
  education_expense?: number;
  health_expense?: number;
  utilities_expense?: number;
  other_household_expenses?: number;
  total_expenses?: number;
  
  // Exploitation (entreprises) - synthétiques ou calculés automatiquement si mode DETAILED
  turnover?: number;
  cogs?: number;
  op_rent?: number;
  op_salaries?: number;
  op_utilities?: number;
  op_transport?: number;
  op_telecom?: number;
  op_taxes?: number;
  op_maintenance?: number;
  op_other?: number;
  depreciation?: number;
  financial_charges?: number;
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

import type { AnalysisMode, FinancialAnalysis } from "@/types/financialAnalysis";

type Row = Record<string, number | string>;

const SPREAD: { detail: string; fields: [string, string][] }[] = [
  {
    detail: "income_detail",
    fields: [
      ["salary_income", "salary_income"],
      ["spouse_income", "spouse_income"],
      ["rental_income", "rental_income"],
      ["other_activity_income", "other_activity_income"],
      ["other_income", "other_income"],
    ],
  },
  {
    detail: "expenses_detail",
    fields: [
      ["rent_expense", "rent_expense"],
      ["food_expense", "food_expense"],
      ["utilities_expense", "utilities_expense"],
      ["transport_expense", "transport_expense"],
      ["education_expense", "education_expense"],
      ["health_expense", "health_expense"],
      ["other_household_expenses", "other_household_expenses"],
    ],
  },
  {
    detail: "exploitation_detail",
    fields: [
      ["turnover", "turnover"],
      ["cogs", "cogs"],
      ["op_rent", "op_rent"],
      ["op_salaries", "op_salaries"],
      ["op_utilities", "op_utilities"],
      ["op_transport", "op_transport"],
      ["op_telecom", "op_telecom"],
      ["op_taxes", "op_taxes"],
      ["op_maintenance", "op_maintenance"],
      ["op_other", "op_other"],
    ],
  },
  {
    detail: "collective_detail",
    fields: [
      ["collective_contributions", "contributions"],
      ["collective_savings", "collective_savings"],
    ],
  },
  {
    detail: "banking_detail",
    fields: [
      ["avg_monthly_credit_movements", "credit_movements"],
      ["avg_monthly_debit_movements", "debit_movements"],
    ],
  },
];

function num(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function average(rows: Row[] | undefined, field: string): number | undefined {
  if (!rows?.length) return undefined;
  const values = rows.map((row) => num(row[field]));
  if (!values.some((value) => value !== 0)) return undefined;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

/** Répartit les moyennes ou recalcule les moyennes selon le mode choisi. */
export function applyAnalysisMode(
  data: Partial<FinancialAnalysis>,
  mode: AnalysisMode,
): Partial<FinancialAnalysis> {
  const periods = data.banking_observation_period_months || 3;
  if (mode === "DETAILED") {
    const detailed: Record<string, Row[]> = { ...(data.detailed_data || {}) };
    for (const block of SPREAD) {
      detailed[block.detail] = Array.from({ length: periods }, (_, index) => {
        const row: Row = { period_label: `Mois ${index + 1}` };
        for (const [source, target] of block.fields) {
          const value = num((data as Record<string, unknown>)[source]);
          if (value) row[target] = value;
        }
        return row;
      });
    }
    return { ...data, analysis_mode: mode, detailed_data: detailed as FinancialAnalysis["detailed_data"] };
  }

  const next: Partial<FinancialAnalysis> = { ...data, analysis_mode: mode };
  const detailed = data.detailed_data || {};
  for (const block of SPREAD) {
    const rows = (detailed as Record<string, Row[] | undefined>)[block.detail];
    for (const [source, target] of block.fields) {
      const value = average(rows, target);
      if (value !== undefined) {
        (next as Record<string, unknown>)[source] = value;
      }
    }
  }
  return next;
}

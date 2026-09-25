import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, TrendingDown, TrendingUp } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "@/api/client";
import {
  Badge,
  PageHeader,
  formatMoney,
} from "@/components/ui";

interface EvolutionData {
  old_value: number;
  new_value: number;
  change_pct: number | null;
  trend: "INCREASE" | "DECREASE" | "STABLE" | "NEW";
}

interface ComparisonData {
  client_id: number;
  current_application_id: number;
  has_previous_analyses: boolean;
  previous_analyses_count: number;
  
  previous_analyses: any[];
  current_analysis: any;
  
  income_comparison: any;
  expenses_comparison: any;
  exploitation_comparison: any;
  ratios_comparison: any;
  score_comparison: any;
  
  key_insights: Array<{
    category: string;
    message: string;
    severity: "POSITIVE" | "WARNING";
  }>;
  
  recommendation_summary: {
    trend: string;
    risk_level: string;
    renewal_recommended: boolean;
    comment: string;
    positive_indicators_count: number;
    warning_indicators_count: number;
  };
}

type TabId =
  | "overview"
  | "income"
  | "ratios"
  | "exploitation"
  | "score";

const TABS: Array<{ id: TabId; label: string; icon: string }> = [
  { id: "overview", label: "Vue d'ensemble", icon: "📊" },
  { id: "income", label: "Revenus & Charges", icon: "💰" },
  { id: "ratios", label: "Ratios Clés", icon: "⭐" },
  { id: "exploitation", label: "Exploitation", icon: "🏭" },
  { id: "score", label: "Scores", icon: "🎯" },
];

function EvolutionBadge({ data }: { data: EvolutionData | null }) {
  if (!data || data.change_pct === null) {
    return <Badge value="N/A" tone="muted" />;
  }

  const { change_pct, trend } = data;
  const tone =
    trend === "INCREASE"
      ? "success"
      : trend === "DECREASE"
        ? "danger"
        : "muted";
  const Icon = trend === "INCREASE" ? TrendingUp : TrendingDown;
  const label = `${change_pct > 0 ? "+" : ""}${change_pct.toFixed(1)}%`;

  return (
    <span className="inline-flex items-center gap-1">
      <Icon className="w-3 h-3" />
      <Badge value={label} tone={tone} />
    </span>
  );
}

function ComparisonRow({
  label,
  oldValue,
  newValue,
  evolution,
  format = "number",
}: {
  label: string;
  oldValue: number | null;
  newValue: number | null;
  evolution: EvolutionData | null;
  format?: "number" | "money" | "percent";
}) {
  const formatValue = (val: number | null) => {
    if (val === null || val === undefined) return "—";
    if (format === "money") return formatMoney(val, "XOF");
    if (format === "percent") return `${val.toFixed(1)}%`;
    return val.toLocaleString();
  };

  return (
    <tr>
      <td className="px-4 py-3 text-sm font-medium text-gray-700">{label}</td>
      <td className="px-4 py-3 text-sm text-gray-600 text-right">
        {formatValue(oldValue)}
      </td>
      <td className="px-4 py-3 text-sm font-semibold text-gray-900 text-right">
        {formatValue(newValue)}
      </td>
      <td className="px-4 py-3 text-center">
        <EvolutionBadge data={evolution} />
      </td>
    </tr>
  );
}

export function CreditHistoryComparisonPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const comparison = useQuery({
    queryKey: ["financial-comparison", id],
    queryFn: async () => {
      const response = await api.get<ComparisonData>(
        `/applications-comparison/${id}/financial-comparison/`,
      );
      return response.data;
    },
  });

  if (!id) {
    return <div>Erreur : ID de dossier manquant</div>;
  }

  return (
    <div className="page-shell">
      <div className="page-chrome">
        <PageHeader
          icon={TrendingUp}
          title="Comparaison avec historique"
          subtitle="Analyse comparative des données financières"
        />

        <div className="mb-6">
          <Link
            to={`/dossiers/${id}`}
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-4 h-4" />
            Retour au dossier
          </Link>
        </div>

        {comparison.isLoading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="mb-4">Chargement...</div>
            </div>
          </div>
        )}

        {comparison.isError && (
          <div className="bg-red-50 border border-red-200 rounded p-4">
            <p className="text-red-800">
              Erreur lors du chargement de la comparaison
            </p>
          </div>
        )}

        {comparison.data && !comparison.isLoading && (
          <>
            {!comparison.data.has_previous_analyses ? (
              <div className="card">
                <div className="card-body text-center py-12">
                  <div className="text-6xl mb-4">🆕</div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Premier crédit de ce client
                  </h3>
                  <p className="text-gray-600">
                    Aucun historique de crédit antérieur n'est disponible pour
                    la comparaison.
                  </p>
                </div>
              </div>
            ) : (
              <>
                {/* Onglets */}
                <div className="border-b border-gray-200 mb-6">
                  <nav className="flex gap-4">
                    {TABS.map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                          activeTab === tab.id
                            ? "border-primary-500 text-primary-600"
                            : "border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300"
                        }`}
                      >
                        <span className="mr-2">{tab.icon}</span>
                        {tab.label}
                      </button>
                    ))}
                  </nav>
                </div>

                {/* Contenu des onglets */}
                <div className="space-y-6">
                  {activeTab === "overview" && (
                    <OverviewTab data={comparison.data} />
                  )}
                  {activeTab === "income" && (
                    <IncomeTab data={comparison.data} />
                  )}
                  {activeTab === "ratios" && (
                    <RatiosTab data={comparison.data} />
                  )}
                  {activeTab === "exploitation" && (
                    <ExploitationTab data={comparison.data} />
                  )}
                  {activeTab === "score" && (
                    <ScoreTab data={comparison.data} />
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// Onglet Vue d'ensemble
// ============================================================================

function OverviewTab({ data }: { data: ComparisonData }) {
  const { key_insights, recommendation_summary } = data;

  return (
    <div className="space-y-6">
      {/* Résumé */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Résumé de la comparaison</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-3 gap-6">
            <div>
              <div className="text-sm text-gray-500 mb-1">Crédits antérieurs</div>
              <div className="text-2xl font-bold text-gray-900">
                {data.previous_analyses_count}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500 mb-1">Indicateurs positifs</div>
              <div className="text-2xl font-bold text-green-600">
                {recommendation_summary.positive_indicators_count}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500 mb-1">Points de vigilance</div>
              <div className="text-2xl font-bold text-orange-600">
                {recommendation_summary.warning_indicators_count}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recommandation */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Recommandation</h3>
        </div>
        <div className="card-body">
          <div className="flex items-start gap-4">
            <div className="text-4xl">
              {recommendation_summary.renewal_recommended ? "✅" : "⚠️"}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Badge
                  value={
                    recommendation_summary.renewal_recommended
                      ? "Renouvellement recommandé"
                      : "Renouvellement non recommandé"
                  }
                  tone={
                    recommendation_summary.renewal_recommended
                      ? "success"
                      : "warning"
                  }
                />
                <Badge
                  value={`Risque ${
                    recommendation_summary.risk_level === "LOW"
                      ? "faible"
                      : recommendation_summary.risk_level === "MEDIUM"
                        ? "moyen"
                        : "élevé"
                  }`}
                  tone={
                    recommendation_summary.risk_level === "LOW"
                      ? "success"
                      : recommendation_summary.risk_level === "MEDIUM"
                        ? "warning"
                        : "danger"
                  }
                />
              </div>
              <p className="text-gray-700">{recommendation_summary.comment}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Insights */}
      {key_insights.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Insights automatiques</h3>
          </div>
          <div className="card-body">
            <ul className="space-y-3">
              {key_insights.map((insight, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="text-xl flex-shrink-0">
                    {insight.severity === "POSITIVE" ? "✅" : "⚠️"}
                  </span>
                  <div>
                    <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
                      {insight.category}
                    </div>
                    <div
                      className={`text-sm ${
                        insight.severity === "POSITIVE"
                          ? "text-green-700"
                          : "text-orange-700"
                      }`}
                    >
                      {insight.message}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Onglet Revenus & Charges
// ============================================================================

function IncomeTab({ data }: { data: ComparisonData }) {
  const { income_comparison, expenses_comparison } = data;

  if (!income_comparison || income_comparison.no_history) {
    return <div>Pas de données de comparaison disponibles</div>;
  }

  return (
    <div className="space-y-6">
      {/* Revenus */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Revenus (Particulier)</h3>
        </div>
        <div className="card-body">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                  Poste
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                  Moyenne précédente
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                  Crédit actuel
                </th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">
                  Évolution
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <ComparisonRow
                label="Salaire net"
                oldValue={income_comparison.salary_income?.old_value}
                newValue={income_comparison.salary_income?.new_value}
                evolution={income_comparison.salary_income}
                format="money"
              />
              <ComparisonRow
                label="Revenus conjoint"
                oldValue={income_comparison.spouse_income?.old_value}
                newValue={income_comparison.spouse_income?.new_value}
                evolution={income_comparison.spouse_income}
                format="money"
              />
              <ComparisonRow
                label="Loyers perçus"
                oldValue={income_comparison.rental_income?.old_value}
                newValue={income_comparison.rental_income?.new_value}
                evolution={income_comparison.rental_income}
                format="money"
              />
              <ComparisonRow
                label="Activité secondaire"
                oldValue={income_comparison.other_activity_income?.old_value}
                newValue={income_comparison.other_activity_income?.new_value}
                evolution={income_comparison.other_activity_income}
                format="money"
              />
              <tr className="bg-gray-50 font-semibold">
                <td className="px-4 py-3 text-sm text-gray-900">TOTAL REVENUS</td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right">
                  {formatMoney(
                    income_comparison.total_income?.old_value || 0,
                    "XOF",
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right">
                  {formatMoney(
                    income_comparison.total_income?.new_value || 0,
                    "XOF",
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <EvolutionBadge data={income_comparison.total_income} />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Charges */}
      {expenses_comparison && !expenses_comparison.no_history && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Charges du ménage</h3>
          </div>
          <div className="card-body">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                    Poste
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                    Moyenne précédente
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                    Crédit actuel
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">
                    Évolution
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                <ComparisonRow
                  label="Loyer / Logement"
                  oldValue={expenses_comparison.rent_expense?.old_value}
                  newValue={expenses_comparison.rent_expense?.new_value}
                  evolution={expenses_comparison.rent_expense}
                  format="money"
                />
                <ComparisonRow
                  label="Alimentation"
                  oldValue={expenses_comparison.food_expense?.old_value}
                  newValue={expenses_comparison.food_expense?.new_value}
                  evolution={expenses_comparison.food_expense}
                  format="money"
                />
                <ComparisonRow
                  label="Eau / Électricité"
                  oldValue={expenses_comparison.utilities_expense?.old_value}
                  newValue={expenses_comparison.utilities_expense?.new_value}
                  evolution={expenses_comparison.utilities_expense}
                  format="money"
                />
                <ComparisonRow
                  label="Transport"
                  oldValue={expenses_comparison.transport_expense?.old_value}
                  newValue={expenses_comparison.transport_expense?.new_value}
                  evolution={expenses_comparison.transport_expense}
                  format="money"
                />
                <tr className="bg-gray-50 font-semibold">
                  <td className="px-4 py-3 text-sm text-gray-900">
                    TOTAL CHARGES
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 text-right">
                    {formatMoney(
                      expenses_comparison.total_charges?.old_value || 0,
                      "XOF",
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 text-right">
                    {formatMoney(
                      expenses_comparison.total_charges?.new_value || 0,
                      "XOF",
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <EvolutionBadge data={expenses_comparison.total_charges} />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Onglet Ratios Clés
// ============================================================================

function RatiosTab({ data }: { data: ComparisonData }) {
  const { ratios_comparison } = data;

  if (!ratios_comparison || ratios_comparison.no_history) {
    return <div>Pas de données de comparaison disponibles</div>;
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">⭐ Indicateurs Clés</h3>
        </div>
        <div className="card-body">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                  Indicateur
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                  Moyenne précédente
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                  Crédit actuel
                </th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">
                  Évolution
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <ComparisonRow
                label="Mensualité institution"
                oldValue={ratios_comparison.new_installment?.old_value}
                newValue={ratios_comparison.new_installment?.new_value}
                evolution={ratios_comparison.new_installment}
                format="money"
              />
              <ComparisonRow
                label="Capacité de remboursement"
                oldValue={ratios_comparison.repayment_capacity?.old_value}
                newValue={ratios_comparison.repayment_capacity?.new_value}
                evolution={ratios_comparison.repayment_capacity}
                format="money"
              />
              <ComparisonRow
                label="Taux d'endettement (%)"
                oldValue={ratios_comparison.debt_ratio?.old_value}
                newValue={ratios_comparison.debt_ratio?.new_value}
                evolution={ratios_comparison.debt_ratio}
                format="percent"
              />
              {ratios_comparison.dscr && (
                <ComparisonRow
                  label="DSCR (Couverture dette)"
                  oldValue={ratios_comparison.dscr?.old_value}
                  newValue={ratios_comparison.dscr?.new_value}
                  evolution={ratios_comparison.dscr}
                  format="number"
                />
              )}
              <ComparisonRow
                label="Couverture garanties (%)"
                oldValue={ratios_comparison.guarantee_coverage?.old_value}
                newValue={ratios_comparison.guarantee_coverage?.new_value}
                evolution={ratios_comparison.guarantee_coverage}
                format="percent"
              />
            </tbody>
          </table>

          {/* Stress test */}
          {ratios_comparison.debt_ratio_stress && (
            <div className="mt-6 pt-6 border-t">
              <h4 className="text-sm font-semibold text-gray-900 mb-3">
                📈 Stress Test (Baisse de revenus -20%)
              </h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-gray-50 rounded">
                  <div className="text-xs text-gray-500 mb-1">
                    Taux d'endettement sous stress
                  </div>
                  <div className="text-lg font-semibold text-gray-900">
                    {ratios_comparison.debt_ratio_stress.new_value?.toFixed(1)}%
                  </div>
                  <EvolutionBadge data={ratios_comparison.debt_ratio_stress} />
                </div>
                {ratios_comparison.dscr_stress && (
                  <div className="p-4 bg-gray-50 rounded">
                    <div className="text-xs text-gray-500 mb-1">
                      DSCR sous stress
                    </div>
                    <div className="text-lg font-semibold text-gray-900">
                      {ratios_comparison.dscr_stress.new_value?.toFixed(2)}
                    </div>
                    <EvolutionBadge data={ratios_comparison.dscr_stress} />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Onglet Exploitation
// ============================================================================

function ExploitationTab({ data }: { data: ComparisonData }) {
  const { exploitation_comparison } = data;

  if (!exploitation_comparison || exploitation_comparison.no_history) {
    return (
      <div className="card">
        <div className="card-body text-center py-12">
          <p className="text-gray-600">
            Données d'exploitation non disponibles (client particulier ou pas
            d'historique entreprise)
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">🏭 Compte d'Exploitation (Entreprise)</h3>
        </div>
        <div className="card-body">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">
                  Poste
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                  Moyenne précédente
                </th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">
                  Crédit actuel
                </th>
                <th className="px-4 py-3 text-center text-sm font-medium text-gray-700">
                  Évolution
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <ComparisonRow
                label="Chiffre d'affaires"
                oldValue={exploitation_comparison.turnover?.old_value}
                newValue={exploitation_comparison.turnover?.new_value}
                evolution={exploitation_comparison.turnover}
                format="money"
              />
              <ComparisonRow
                label="Coût marchandises"
                oldValue={exploitation_comparison.cogs?.old_value}
                newValue={exploitation_comparison.cogs?.new_value}
                evolution={exploitation_comparison.cogs}
                format="money"
              />
              <ComparisonRow
                label="Marge brute"
                oldValue={exploitation_comparison.gross_margin?.old_value}
                newValue={exploitation_comparison.gross_margin?.new_value}
                evolution={exploitation_comparison.gross_margin}
                format="money"
              />
              <ComparisonRow
                label="Charges d'exploitation"
                oldValue={exploitation_comparison.operating_expenses?.old_value}
                newValue={exploitation_comparison.operating_expenses?.new_value}
                evolution={exploitation_comparison.operating_expenses}
                format="money"
              />
              <tr className="bg-gray-50 font-semibold">
                <td className="px-4 py-3 text-sm text-gray-900">
                  RÉSULTAT NET
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right">
                  {formatMoney(
                    exploitation_comparison.net_result?.old_value || 0,
                    "XOF",
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right">
                  {formatMoney(
                    exploitation_comparison.net_result?.new_value || 0,
                    "XOF",
                  )}
                </td>
                <td className="px-4 py-3 text-center">
                  <EvolutionBadge data={exploitation_comparison.net_result} />
                </td>
              </tr>
            </tbody>
          </table>

          {/* Marges */}
          <div className="mt-6 pt-6 border-t">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">Marges</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded">
                <div className="text-xs text-gray-500 mb-1">Marge brute</div>
                <div className="text-lg font-semibold text-gray-900">
                  {exploitation_comparison.gross_margin_pct?.new_value?.toFixed(1)}%
                </div>
                <EvolutionBadge data={exploitation_comparison.gross_margin_pct} />
              </div>
              <div className="p-4 bg-gray-50 rounded">
                <div className="text-xs text-gray-500 mb-1">Marge nette</div>
                <div className="text-lg font-semibold text-gray-900">
                  {exploitation_comparison.net_margin_pct?.new_value?.toFixed(1)}%
                </div>
                <EvolutionBadge data={exploitation_comparison.net_margin_pct} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Onglet Scores
// ============================================================================

function ScoreTab({ data }: { data: ComparisonData }) {
  const { score_comparison } = data;

  if (!score_comparison || score_comparison.no_history) {
    return <div>Pas de données de comparaison disponibles</div>;
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">🎯 Évolution du Score</h3>
        </div>
        <div className="card-body">
          <div className="flex items-center justify-between mb-6">
            <div>
              <div className="text-sm text-gray-500 mb-1">Score actuel</div>
              <div className="text-4xl font-bold text-gray-900">
                {score_comparison.current_score?.toFixed(0) || "N/A"}
                <span className="text-lg text-gray-500">/100</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500 mb-1">Évolution</div>
              <EvolutionBadge data={score_comparison.score_evolution} />
            </div>
          </div>

          {/* Historique des scores */}
          {score_comparison.scores_history &&
            score_comparison.scores_history.length > 0 && (
              <div className="pt-6 border-t">
                <h4 className="text-sm font-semibold text-gray-900 mb-3">
                  Historique
                </h4>
                <div className="space-y-2">
                  {score_comparison.scores_history.map(
                    (score: any, idx: number) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded"
                      >
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {score.application_reference}
                          </div>
                          <div className="text-xs text-gray-500">
                            {score.analysis_date
                              ? new Date(score.analysis_date).toLocaleDateString()
                              : "N/A"}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold text-gray-900">
                            {score.internal_score?.toFixed(0) || "N/A"}
                          </div>
                          <Badge
                            value={
                              score.recommendation === "FAVORABLE"
                                ? "Favorable"
                                : score.recommendation === "CONDITIONAL"
                                  ? "Conditionnel"
                                  : "Défavorable"
                            }
                            tone={
                              score.recommendation === "FAVORABLE"
                                ? "success"
                                : score.recommendation === "CONDITIONAL"
                                  ? "warning"
                                  : "danger"
                            }
                          />
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </div>
            )}

          {/* Recommandation actuelle */}
          <div className="pt-6 border-t">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">
              Recommandation actuelle
            </h4>
            <Badge
              value={
                score_comparison.current_recommendation === "FAVORABLE"
                  ? "Favorable"
                  : score_comparison.current_recommendation === "CONDITIONAL"
                    ? "Favorable sous conditions"
                    : "Défavorable"
              }
              tone={
                score_comparison.current_recommendation === "FAVORABLE"
                  ? "success"
                  : score_comparison.current_recommendation === "CONDITIONAL"
                    ? "warning"
                    : "danger"
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}

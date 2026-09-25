import { useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowRight, ArrowUpRight, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { Badge, Spinner } from "@/components/ui";

interface Alert {
  level: string;
  category: string;
  message: string;
  blocking: boolean;
}

interface ComparisonSummary {
  has_history: boolean;
  previous_credits_count: number;
  active_credits_count: number;
  repayment_rate: number;
  score_trend: "INCREASE" | "DECREASE" | "STABLE" | "NEW" | null;
  recommendation: boolean | null;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | null;
  main_alerts: Alert[];
  positive_indicators: number;
  warning_indicators: number;
}

interface Props {
  applicationId: number | string;
}

const TREND_ICONS = {
  INCREASE: ArrowUpRight,
  DECREASE: ArrowDownRight,
  STABLE: ArrowRight,
  NEW: TrendingUp,
};

const TREND_COLORS = {
  INCREASE: "text-green-600",
  DECREASE: "text-red-600",
  STABLE: "text-blue-600",
  NEW: "text-gray-600",
};

const TREND_LABELS = {
  INCREASE: "En amélioration",
  DECREASE: "En baisse",
  STABLE: "Stable",
  NEW: "Nouveau client",
};

export function ComparisonSummaryWidget({ applicationId }: Props) {
  const summary = useQuery({
    queryKey: ["comparison-summary", applicationId],
    queryFn: async () => {
      const response = await api.get<ComparisonSummary>(
        `/applications-comparison/${applicationId}/comparison-summary/`,
      );
      return response.data;
    },
  });

  if (summary.isLoading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">📊 Comparaison avec historique</h3>
        </div>
        <div className="card-body flex items-center justify-center py-8">
          <Spinner />
        </div>
      </div>
    );
  }

  if (summary.isError || !summary.data) {
    return null; // Ne pas afficher si erreur
  }

  const data = summary.data;

  // Si pas d'historique, affichage simplifié
  if (!data.has_history) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">📊 Historique client</h3>
        </div>
        <div className="card-body">
          <div className="flex items-center gap-2 text-gray-600">
            <TrendingUp className="w-5 h-5" />
            <span className="text-sm">
              Premier crédit de ce client dans l'institution
            </span>
          </div>
        </div>
      </div>
    );
  }

  const TrendIcon = data.score_trend ? TREND_ICONS[data.score_trend] : TrendingUp;
  const trendColor = data.score_trend ? TREND_COLORS[data.score_trend] : "text-gray-600";
  const trendLabel = data.score_trend ? TREND_LABELS[data.score_trend] : "N/A";

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">📊 Comparaison avec historique</h3>
      </div>
      <div className="card-body space-y-4">
        {/* Résumé principal */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
              Crédits antérieurs
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {data.previous_credits_count}
            </div>
            {data.active_credits_count > 0 && (
              <div className="text-xs text-orange-600 mt-1">
                {data.active_credits_count} actif(s)
              </div>
            )}
          </div>

          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
              Taux de remboursement
            </div>
            <div
              className={`text-2xl font-bold ${
                data.repayment_rate >= 80
                  ? "text-green-600"
                  : data.repayment_rate >= 60
                    ? "text-orange-600"
                    : "text-red-600"
              }`}
            >
              {data.repayment_rate.toFixed(0)}%
            </div>
          </div>
        </div>

        {/* Tendance du score */}
        <div className="pt-4 border-t">
          <div className="flex items-center gap-2 mb-2">
            <TrendIcon className={`w-5 h-5 ${trendColor}`} />
            <span className="text-sm font-medium text-gray-700">
              Évolution du profil
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              value={trendLabel}
              tone={
                data.score_trend === "INCREASE"
                  ? "success"
                  : data.score_trend === "DECREASE"
                    ? "danger"
                    : "muted"
              }
            />
            {data.positive_indicators > 0 && (
              <span className="text-xs text-green-600">
                +{data.positive_indicators} indicateurs positifs
              </span>
            )}
            {data.warning_indicators > 0 && (
              <span className="text-xs text-orange-600">
                {data.warning_indicators} vigilances
              </span>
            )}
          </div>
        </div>

        {/* Recommandation */}
        {data.recommendation !== null && (
          <div className="pt-4 border-t">
            <div className="flex items-center gap-2">
              {data.recommendation ? (
                <>
                  <div className="flex-shrink-0 w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm font-medium text-green-700">
                    Renouvellement recommandé
                  </span>
                </>
              ) : (
                <>
                  <div className="flex-shrink-0 w-2 h-2 bg-red-500 rounded-full"></div>
                  <span className="text-sm font-medium text-red-700">
                    Renouvellement non recommandé
                  </span>
                </>
              )}
            </div>
            {data.risk_level && (
              <div className="text-xs text-gray-600 mt-1">
                Niveau de risque :{" "}
                <span
                  className={`font-medium ${
                    data.risk_level === "LOW"
                      ? "text-green-600"
                      : data.risk_level === "MEDIUM"
                        ? "text-orange-600"
                        : "text-red-600"
                  }`}
                >
                  {data.risk_level === "LOW"
                    ? "Faible"
                    : data.risk_level === "MEDIUM"
                      ? "Moyen"
                      : "Élevé"}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Alertes principales */}
        {data.main_alerts.length > 0 && (
          <div className="pt-4 border-t">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
              Alertes
            </div>
            <ul className="space-y-1.5">
              {data.main_alerts.slice(0, 3).map((alert, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs">
                  <span className="flex-shrink-0 mt-0.5">
                    {alert.level === "ERROR"
                      ? "🔴"
                      : alert.level === "WARNING"
                        ? "🟠"
                        : alert.level === "SUCCESS"
                          ? "🟢"
                          : "ℹ️"}
                  </span>
                  <span
                    className={`${
                      alert.level === "ERROR"
                        ? "text-red-700"
                        : alert.level === "WARNING"
                          ? "text-orange-700"
                          : alert.level === "SUCCESS"
                            ? "text-green-700"
                            : "text-gray-700"
                    }`}
                  >
                    {alert.message}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Lien vers la comparaison détaillée */}
        <div className="pt-4 border-t">
          <Link
            to={`/dossiers/${applicationId}/comparaison-historique`}
            className="btn btn-secondary btn-sm w-full"
          >
            Voir comparaison détaillée →
          </Link>
        </div>
      </div>
    </div>
  );
}

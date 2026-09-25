import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle, Info, XCircle } from "lucide-react";
import { api } from "@/api/client";
import { Spinner } from "@/components/ui";

interface Alert {
  level: "ERROR" | "WARNING" | "SUCCESS" | "INFO";
  category: string;
  message: string;
  blocking: boolean;
}

interface EligibilityData {
  eligibility: {
    eligible: boolean;
    alerts: Alert[];
    repayment_rate: number;
    history_summary: {
      total_credits: number;
      active_credits: number;
      max_days_late: number;
    };
  };
  history: {
    total_disbursed: number;
    total_borrowed: number;
    total_repaid: number;
    repayment_rate: number;
    has_litigation: boolean;
    has_dation: boolean;
    has_restructuring: boolean;
    has_writeoff: boolean;
    last_disbursement_date: string | null;
  };
}

interface Props {
  clientId: number | null;
  onEligibilityChecked?: (eligible: boolean, alerts: Alert[]) => void;
}

export function ClientRenewalEligibilityAlert({
  clientId,
  onEligibilityChecked,
}: Props) {
  const eligibility = useQuery({
    queryKey: ["client-renewal-eligibility", clientId],
    queryFn: async () => {
      if (!clientId) return null;
      const response = await api.get<EligibilityData>(
        `/clients/${clientId}/renewal-eligibility/`,
      );
      return response.data;
    },
    enabled: !!clientId,
  });

  // Appeler le callback quand les données changent
  useEffect(() => {
    if (eligibility.data && onEligibilityChecked) {
      const { eligible, alerts } = eligibility.data.eligibility;
      onEligibilityChecked(eligible, alerts);
    }
  }, [eligibility.data, onEligibilityChecked]);

  if (!clientId) {
    return null;
  }

  if (eligibility.isLoading) {
    return (
      <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="flex items-center gap-2">
          <Spinner />
          <span className="text-sm text-gray-600">
            Vérification de l'historique du client...
          </span>
        </div>
      </div>
    );
  }

  if (eligibility.isError) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center gap-2">
          <XCircle className="w-5 h-5 text-red-600" />
          <span className="text-sm text-red-800">
            Erreur lors de la vérification de l'historique
          </span>
        </div>
      </div>
    );
  }

  if (!eligibility.data) {
    return null;
  }

  const { eligibility: elig, history } = eligibility.data;
  const { eligible, alerts, repayment_rate } = elig;

  // Séparer les alertes par niveau
  const errorAlerts = alerts.filter((a) => a.level === "ERROR");
  const warningAlerts = alerts.filter((a) => a.level === "WARNING");
  const successAlerts = alerts.filter((a) => a.level === "SUCCESS");
  const infoAlerts = alerts.filter((a) => a.level === "INFO");

  // Déterminer la couleur de fond principale
  let bgColor = "bg-gray-50";
  let borderColor = "border-gray-200";
  let textColor = "text-gray-800";

  if (errorAlerts.length > 0) {
    bgColor = "bg-red-50";
    borderColor = "border-red-200";
    textColor = "text-red-800";
  } else if (warningAlerts.length > 0) {
    bgColor = "bg-orange-50";
    borderColor = "border-orange-200";
    textColor = "text-orange-800";
  } else if (successAlerts.length > 0) {
    bgColor = "bg-green-50";
    borderColor = "border-green-200";
    textColor = "text-green-800";
  }

  return (
    <div className={`p-4 border rounded-lg ${bgColor} ${borderColor}`}>
      {/* En-tête */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className={`font-semibold ${textColor}`}>
            {eligible ? "✅ Historique client vérifié" : "🔴 Attention"}
          </h3>
          <div className="text-sm text-gray-600 mt-1">
            {history.total_disbursed > 0 ? (
              <>
                <span className="font-medium">
                  {history.total_disbursed} crédit(s) antérieur(s)
                </span>
                {" • "}
                <span>
                  Taux de remboursement global :{" "}
                  <span
                    className={`font-semibold ${
                      repayment_rate >= 80
                        ? "text-green-600"
                        : repayment_rate >= 60
                          ? "text-orange-600"
                          : "text-red-600"
                    }`}
                  >
                    {repayment_rate.toFixed(1)}%
                  </span>
                </span>
              </>
            ) : (
              <span className="italic">Premier crédit de ce client</span>
            )}
          </div>
        </div>

        {history.total_disbursed > 0 && (
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => {
              // TODO: Ouvrir modal ou page d'historique complet
              window.open(`/clients/${clientId}/history`, "_blank");
            }}
          >
            Voir historique complet
          </button>
        )}
      </div>

      {/* Alertes bloquantes (ERROR) */}
      {errorAlerts.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-2">
            <XCircle className="w-5 h-5 text-red-600" />
            <span className="font-semibold text-red-800">
              Alertes bloquantes ({errorAlerts.length})
            </span>
          </div>
          <ul className="space-y-1.5">
            {errorAlerts.map((alert, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-red-600 mt-0.5">❌</span>
                <span className="text-red-800">{alert.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Avertissements (WARNING) */}
      {warningAlerts.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="w-5 h-5 text-orange-600" />
            <span className="font-semibold text-orange-800">
              Avertissements ({warningAlerts.length})
            </span>
          </div>
          <ul className="space-y-1.5">
            {warningAlerts.map((alert, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-orange-600 mt-0.5">⚠️</span>
                <span className="text-orange-800">{alert.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Informations positives (SUCCESS) */}
      {successAlerts.length > 0 && errorAlerts.length === 0 && (
        <div className="mb-2">
          <ul className="space-y-1.5">
            {successAlerts.map((alert, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-green-600 mt-0.5">✅</span>
                <span className="text-green-800">{alert.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Informations complémentaires (INFO) */}
      {infoAlerts.length > 0 && (
        <div>
          <ul className="space-y-1 text-sm text-gray-600">
            {infoAlerts.map((alert, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-blue-600 mt-0.5">ℹ️</span>
                <span>{alert.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Statut final */}
      {!eligible && (
        <div className="mt-3 pt-3 border-t border-red-300">
          <div className="flex items-center gap-2 text-sm font-semibold text-red-800">
            <XCircle className="w-4 h-4" />
            <span>
              La création d'un nouveau dossier pour ce client est actuellement
              bloquée
            </span>
          </div>
        </div>
      )}

      {eligible && warningAlerts.length > 0 && (
        <div className="mt-3 pt-3 border-t border-orange-300">
          <div className="flex items-center gap-2 text-sm text-orange-800">
            <Info className="w-4 h-4" />
            <span>
              Vous pouvez continuer, mais une vigilance particulière est
              recommandée
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, Check, FileText, RefreshCw, X } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import type { Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  FilterField,
  FilterSelect,
  ListFilters,
  SearchInput,
  countActive,
} from "@/components/ListFilters";
import {
  Badge,
  DEFAULT_PAGE_SIZE,
  PageHeader,
  PaginationBar,
  QueryStatus,
  TenantScopeNotice,
  formatDate,
  formatMoney,
} from "@/components/ui";

type LoanRestructuringRequest = {
  id: string;
  loan: string;
  loan_display: string;
  status: string;
  reason: string;
  current_outstanding_balance: string;
  current_monthly_installment: string;
  current_remaining_months: number;
  current_days_past_due: number;
  new_duration_months: number;
  new_interest_rate: string | null;
  grace_period_months: number;
  capitalize_arrears: boolean;
  arrears_amount: string;
  new_monthly_installment: string | null;
  additional_interest_cost: string | null;
  client_revised_income: string | null;
  client_revised_expenses: string | null;
  revised_debt_ratio: string | null;
  guarantees_maintained: boolean;
  guarantees_comment: string;
  special_conditions: string;
  previous_restructuring_count: number;
  justification: string;
  created_by: string;
  created_by_display: string;
  created_at: string;
  reviewed_by: string | null;
  reviewed_by_display: string;
  reviewed_at: string | null;
  review_comment: string;
  executed_by: string | null;
  executed_by_display: string;
  executed_at: string | null;
  can_approve: boolean;
  can_reject: boolean;
  can_execute: boolean;
  can_cancel: boolean;
};

const STATUS_LABELS: Record<string, string> = {
  PENDING: "En attente",
  APPROVED: "Approuvée",
  REJECTED: "Rejetée",
  CANCELLED: "Annulée",
  EXECUTED: "Exécutée",
};

const STATUS_TONES: Record<
  string,
  "success" | "warning" | "danger" | "info" | "muted"
> = {
  PENDING: "warning",
  APPROVED: "success",
  REJECTED: "danger",
  CANCELLED: "muted",
  EXECUTED: "info",
};

const REASON_LABELS: Record<string, string> = {
  TEMPORARY_DIFFICULTY: "Difficultés temporaires",
  INCOME_REDUCTION: "Baisse de revenus",
  HEALTH_ISSUES: "Problèmes de santé",
  BUSINESS_DOWNTURN: "Baisse d'activité",
  FORCE_MAJEURE: "Force majeure",
  AVOID_DEFAULT: "Prévenir le défaut",
  OTHER: "Autre raison",
};

const LIST_PAGE_SIZE = Math.max(15, DEFAULT_PAGE_SIZE);

export function LoanRestructuringRequestsPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [selectedRequest, setSelectedRequest] =
    useState<LoanRestructuringRequest | null>(null);
  const [actionDialog, setActionDialog] = useState<
    "approve" | "reject" | "execute" | "cancel" | null
  >(null);
  const [actionComment, setActionComment] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const queryClient = useQueryClient();

  function setFilter<T>(setter: (v: T) => void) {
    return (value: T) => {
      setter(value);
      setPage(1);
    };
  }

  const list = useQuery({
    queryKey: [
      "loan-restructuring-requests",
      activeTenant,
      page,
      LIST_PAGE_SIZE,
      status,
      search,
    ],
    queryFn: async () =>
      (
        await api.get<Paginated<LoanRestructuringRequest>>(
          "/loan-restructuring-requests/",
          {
            params: {
              page,
              page_size: LIST_PAGE_SIZE,
              ...(status ? { status } : {}),
              ...(search.trim() ? { search: search.trim() } : {}),
            },
          },
        )
      ).data,
    enabled: !needsTenant,
  });

  const performAction = useMutation({
    mutationFn: async ({
      id,
      action,
      comment,
    }: {
      id: string;
      action: string;
      comment?: string;
    }) => {
      return await api.post(`/loan-restructuring-requests/${id}/${action}/`, {
        comment: comment || "",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["loan-restructuring-requests"] });
      setNotice("Action effectuée avec succès");
      setActionDialog(null);
      setSelectedRequest(null);
      setActionComment("");
    },
    onError: (error: any) => {
      const message =
        error.response?.data?.detail ||
        error.response?.data?.comment?.[0] ||
        "Une erreur est survenue";
      setNotice(message);
    },
  });

  const handleAction = (action: "approve" | "reject" | "execute" | "cancel") => {
    if (!selectedRequest) return;
    performAction.mutate({
      id: selectedRequest.id,
      action,
      comment: actionComment,
    });
  };

  const openActionDialog = (
    request: LoanRestructuringRequest,
    action: "approve" | "reject" | "execute" | "cancel",
  ) => {
    setSelectedRequest(request);
    setActionDialog(action);
    setActionComment("");
  };

  const closeActionDialog = () => {
    setActionDialog(null);
    setSelectedRequest(null);
    setActionComment("");
  };

  return (
    <div className="page-shell page-shell--list">
      <div className="list-page-chrome">
        <PageHeader
          icon={RefreshCw}
          title="Demandes de Restructuration"
          subtitle="Demandes de modification des termes des crédits en difficulté"
        />
        {needsTenant && <TenantScopeNotice />}

        <ListFilters
          search={
            <SearchInput
              value={search}
              onChange={setFilter(setSearch)}
              placeholder="Réf. dossier, client…"
            />
          }
          activeCount={countActive(search, status)}
          onReset={() => {
            setSearch("");
            setStatus("");
            setPage(1);
          }}
        >
          <FilterField label="Statut">
            <FilterSelect value={status} onChange={setFilter(setStatus)}>
              <option value="">Tous</option>
              <option value="PENDING">En attente</option>
              <option value="APPROVED">Approuvée</option>
              <option value="REJECTED">Rejetée</option>
              <option value="EXECUTED">Exécutée</option>
              <option value="CANCELLED">Annulée</option>
            </FilterSelect>
          </FilterField>
        </ListFilters>

        {notice && (
          <p className="form-error" role="status">
            {notice}
          </p>
        )}
        <QueryStatus
          isLoading={list.isLoading}
          isError={list.isError}
          onRetry={() => void list.refetch()}
        >
          <></>
        </QueryStatus>

        {list.data && (
          <>
            <div className="list-table-wrapper">
              <table className="list-table">
                <thead>
                  <tr>
                    <th>Prêt</th>
                    <th>Statut</th>
                    <th>Motif</th>
                    <th>Durée actuelle</th>
                    <th>Nouvelle durée</th>
                    <th>Mensualité actuelle</th>
                    <th>Nouvelle mensualité</th>
                    <th>Demandé par</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.results.length === 0 && (
                    <tr>
                      <td colSpan={9} className="text-center text-gray-500">
                        Aucune demande trouvée
                      </td>
                    </tr>
                  )}
                  {list.data.results.map((request) => (
                    <tr key={request.id}>
                      <td>
                        <div className="font-medium">{request.loan_display}</div>
                      </td>
                      <td>
                        <Badge
                          value={STATUS_LABELS[request.status] || request.status}
                          tone={STATUS_TONES[request.status]}
                        />
                      </td>
                      <td>
                        <span className="text-sm">
                          {REASON_LABELS[request.reason] || request.reason}
                        </span>
                      </td>
                      <td>
                        <span className="text-sm">
                          {request.current_remaining_months} mois
                        </span>
                      </td>
                      <td>
                        <span className="text-sm font-semibold text-blue-600">
                          {request.new_duration_months} mois
                        </span>
                      </td>
                      <td>
                        <span className="text-sm">
                          {formatMoney(request.current_monthly_installment, "XOF")}
                        </span>
                      </td>
                      <td>
                        <span className="text-sm font-semibold text-green-600">
                          {request.new_monthly_installment
                            ? formatMoney(request.new_monthly_installment, "XOF")
                            : "—"}
                        </span>
                      </td>
                      <td>
                        <div className="text-sm">{request.created_by_display}</div>
                        <div className="text-xs text-gray-500">
                          {formatDate(request.created_at)}
                        </div>
                      </td>
                      <td>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => setSelectedRequest(request)}
                          >
                            <FileText className="w-4 h-4" />
                          </button>
                          {request.can_approve && (
                            <button
                              type="button"
                              className="btn btn-success btn-sm"
                              onClick={() => openActionDialog(request, "approve")}
                            >
                              <Check className="w-4 h-4" />
                            </button>
                          )}
                          {request.can_reject && (
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              onClick={() => openActionDialog(request, "reject")}
                            >
                              <X className="w-4 h-4" />
                            </button>
                          )}
                          {request.can_execute && (
                            <button
                              type="button"
                              className="btn btn-primary btn-sm"
                              onClick={() => openActionDialog(request, "execute")}
                            >
                              Exécuter
                            </button>
                          )}
                          {request.can_cancel && (
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              onClick={() => openActionDialog(request, "cancel")}
                            >
                              <Ban className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <PaginationBar
              page={page}
              count={list.data.count}
              pageSize={LIST_PAGE_SIZE}
              onPageChange={setPage}
            />
          </>
        )}
      </div>

      {/* Dialog de détails */}
      {selectedRequest && !actionDialog && (
        <div
          className="modal-backdrop modal-backdrop--top"
          onClick={() => setSelectedRequest(null)}
        >
          <div
            className="modal-card modal-card--xl"
            onClick={(event) => event.stopPropagation()}
          >
            <h3>Détails de la demande de restructuration</h3>
            <div className="space-y-6">
              {/* Informations générales */}
              <div>
                <h3 className="text-lg font-semibold mb-3">Informations générales</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700">Prêt</label>
                    <div className="mt-1">{selectedRequest.loan_display}</div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Statut</label>
                    <div className="mt-1">
                      <Badge
                        value={
                          STATUS_LABELS[selectedRequest.status] ||
                          selectedRequest.status
                        }
                        tone={STATUS_TONES[selectedRequest.status]}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Motif</label>
                    <div className="mt-1">{REASON_LABELS[selectedRequest.reason]}</div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Restructurations antérieures
                    </label>
                    <div className="mt-1">
                      <Badge
                        value={`${selectedRequest.previous_restructuring_count} fois`}
                        tone={
                          selectedRequest.previous_restructuring_count === 0
                            ? "success"
                            : selectedRequest.previous_restructuring_count === 1
                              ? "warning"
                              : "danger"
                        }
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* État actuel */}
              <div className="border-t pt-4">
                <h3 className="text-lg font-semibold mb-3">État actuel du prêt</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Solde restant dû
                    </label>
                    <div className="mt-1 font-semibold">
                      {formatMoney(selectedRequest.current_outstanding_balance, "XOF")}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Mensualité actuelle
                    </label>
                    <div className="mt-1">
                      {formatMoney(selectedRequest.current_monthly_installment, "XOF")}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Mois restants
                    </label>
                    <div className="mt-1">
                      {selectedRequest.current_remaining_months} mois
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Jours de retard
                    </label>
                    <div className="mt-1">
                      {selectedRequest.current_days_past_due > 0 ? (
                        <Badge
                          value={`${selectedRequest.current_days_past_due} jours`}
                          tone="danger"
                        />
                      ) : (
                        <Badge value="À jour" tone="success" />
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Nouveaux termes */}
              <div className="border-t pt-4">
                <h3 className="text-lg font-semibold mb-3">Nouveaux termes proposés</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Nouvelle durée
                    </label>
                    <div className="mt-1 font-semibold text-blue-600">
                      {selectedRequest.new_duration_months} mois
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Nouveau taux
                    </label>
                    <div className="mt-1">
                      {selectedRequest.new_interest_rate
                        ? `${selectedRequest.new_interest_rate}%`
                        : "Inchangé"}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Période de grâce
                    </label>
                    <div className="mt-1">
                      {selectedRequest.grace_period_months > 0
                        ? `${selectedRequest.grace_period_months} mois`
                        : "Aucune"}
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Arriérés capitalisés
                    </label>
                    <div className="mt-1">
                      {selectedRequest.capitalize_arrears ? (
                        <span className="font-semibold">
                          Oui — {formatMoney(selectedRequest.arrears_amount, "XOF")}
                        </span>
                      ) : (
                        "Non"
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Impact financier */}
              {selectedRequest.new_monthly_installment && (
                <div className="border-t pt-4">
                  <h3 className="text-lg font-semibold mb-3">
                    Impact financier (calculé)
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700">
                        Nouvelle mensualité
                      </label>
                      <div className="mt-1 font-semibold text-green-600">
                        {formatMoney(selectedRequest.new_monthly_installment, "XOF")}
                      </div>
                    </div>
                    {selectedRequest.additional_interest_cost && (
                      <div>
                        <label className="text-sm font-medium text-gray-700">
                          Surcoût d'intérêts
                        </label>
                        <div className="mt-1 font-semibold text-orange-600">
                          {formatMoney(selectedRequest.additional_interest_cost, "XOF")}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Capacité révisée */}
              {selectedRequest.client_revised_income && (
                <div className="border-t pt-4">
                  <h3 className="text-lg font-semibold mb-3">
                    Capacité de remboursement révisée
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700">
                        Revenus révisés
                      </label>
                      <div className="mt-1">
                        {formatMoney(selectedRequest.client_revised_income, "XOF")}
                      </div>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700">
                        Charges révisées
                      </label>
                      <div className="mt-1">
                        {formatMoney(
                          selectedRequest.client_revised_expenses || "0",
                          "XOF",
                        )}
                      </div>
                    </div>
                    {selectedRequest.revised_debt_ratio && (
                      <div>
                        <label className="text-sm font-medium text-gray-700">
                          Taux d'endettement révisé
                        </label>
                        <div className="mt-1">
                          <Badge
                            value={`${selectedRequest.revised_debt_ratio}%`}
                            tone={
                              parseFloat(selectedRequest.revised_debt_ratio) <= 40
                                ? "success"
                                : parseFloat(selectedRequest.revised_debt_ratio) <= 50
                                  ? "warning"
                                  : "danger"
                            }
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Garanties */}
              <div className="border-t pt-4">
                <h3 className="text-lg font-semibold mb-3">Garanties</h3>
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Garanties maintenues
                  </label>
                  <div className="mt-1">
                    <Badge
                      value={
                        selectedRequest.guarantees_maintained
                          ? "Maintenues"
                          : "Non maintenues"
                      }
                      tone={
                        selectedRequest.guarantees_maintained ? "success" : "danger"
                      }
                    />
                  </div>
                </div>
                {selectedRequest.guarantees_comment && (
                  <div className="mt-3">
                    <label className="text-sm font-medium text-gray-700">
                      Commentaire
                    </label>
                    <div className="mt-1 p-3 bg-gray-50 rounded border text-sm whitespace-pre-wrap">
                      {selectedRequest.guarantees_comment}
                    </div>
                  </div>
                )}
              </div>

              {/* Justification */}
              <div className="border-t pt-4">
                <label className="text-sm font-medium text-gray-700">
                  Justification de la demande
                </label>
                <div className="mt-1 p-3 bg-gray-50 rounded border text-sm whitespace-pre-wrap">
                  {selectedRequest.justification}
                </div>
              </div>

              {selectedRequest.special_conditions && (
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Conditions particulières
                  </label>
                  <div className="mt-1 p-3 bg-gray-50 rounded border text-sm whitespace-pre-wrap">
                    {selectedRequest.special_conditions}
                  </div>
                </div>
              )}

              {/* Cycle de vie */}
              <div className="border-t pt-4">
                <h3 className="text-lg font-semibold mb-3">Cycle de vie</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700">
                      Demandé par
                    </label>
                    <div className="mt-1">{selectedRequest.created_by_display}</div>
                    <div className="text-xs text-gray-500">
                      {formatDate(selectedRequest.created_at)}
                    </div>
                  </div>
                  {selectedRequest.reviewed_by_display && (
                    <div>
                      <label className="text-sm font-medium text-gray-700">
                        Validé par
                      </label>
                      <div className="mt-1">{selectedRequest.reviewed_by_display}</div>
                      <div className="text-xs text-gray-500">
                        {formatDate(selectedRequest.reviewed_at || "")}
                      </div>
                    </div>
                  )}
                </div>

                {selectedRequest.review_comment && (
                  <div className="mt-4">
                    <label className="text-sm font-medium text-gray-700">
                      Commentaire du validateur
                    </label>
                    <div className="mt-1 p-3 bg-blue-50 rounded border border-blue-200 text-sm whitespace-pre-wrap">
                      {selectedRequest.review_comment}
                    </div>
                  </div>
                )}

                {selectedRequest.executed_by_display && (
                  <div className="mt-4">
                    <label className="text-sm font-medium text-gray-700">
                      Exécuté par
                    </label>
                    <div className="mt-1">{selectedRequest.executed_by_display}</div>
                    <div className="text-xs text-gray-500">
                      {formatDate(selectedRequest.executed_at || "")}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Dialog d'action */}
      {actionDialog && selectedRequest && (
        <div className="modal-backdrop modal-backdrop--top" onClick={closeActionDialog}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <h3>
                {actionDialog === "approve" && "Approuver la demande"}
                {actionDialog === "reject" && "Rejeter la demande"}
                {actionDialog === "execute" && "Exécuter la restructuration"}
                {actionDialog === "cancel" && "Annuler la demande"}
              </h3>
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded">
                <p className="text-sm text-amber-800">
                  {actionDialog === "approve" &&
                    "Vous allez approuver cette demande de restructuration. Cette action nécessite une vérification complète de la capacité de remboursement révisée."}
                  {actionDialog === "reject" &&
                    "Vous allez rejeter cette demande. Un commentaire est obligatoire pour justifier le rejet."}
                  {actionDialog === "execute" &&
                    "⚠️ ATTENTION : Cette action modifiera définitivement les termes du prêt (durée, taux, échéancier)."}
                  {actionDialog === "cancel" &&
                    "Vous allez annuler votre demande. Elle ne pourra plus être validée."}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">
                  {actionDialog === "reject"
                    ? "Commentaire (obligatoire)"
                    : "Commentaire"}
                </label>
                <textarea
                  className="w-full mt-1 p-2 border rounded"
                  rows={4}
                  value={actionComment}
                  onChange={(e) => setActionComment(e.target.value)}
                  placeholder={
                    actionDialog === "reject"
                      ? "Expliquez pourquoi vous rejetez cette demande..."
                      : "Commentaire optionnel..."
                  }
                />
              </div>

              <div className="flex gap-2 justify-end">
                <button type="button" className="btn btn-ghost" onClick={closeActionDialog}>
                  Annuler
                </button>
                <button
                  type="button"
                  className={
                    actionDialog === "approve" ? "btn btn-success" : "btn btn-primary"
                  }
                  onClick={() => handleAction(actionDialog)}
                  disabled={
                    performAction.isPending ||
                    (actionDialog === "reject" && !actionComment.trim())
                  }
                >
                  {performAction.isPending ? "En cours..." : "Confirmer"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

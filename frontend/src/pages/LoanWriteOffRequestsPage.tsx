import { useMutation, useQuery, useQueryClient } from "@tantml:react-query";
import { AlertCircle, Ban, Check, FileText, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { api } from "@/api/client";
import type { Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { PermLink } from "@/components/PermLink";
import {
  FilterField,
  FilterSelect,
  ListFilters,
  SearchInput,
  countActive,
} from "@/components/ListFilters";
import {
  Badge,
  Button,
  DEFAULT_PAGE_SIZE,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  PageHeader,
  PaginationBar,
  QueryStatus,
  TenantScopeNotice,
  formatDate,
  formatMoney,
} from "@/components/ui";

type LoanWriteOffRequest = {
  id: string;
  loan: string;
  loan_display: string;
  status: string;
  reason: string;
  outstanding_balance: string;
  days_past_due: number;
  recovery_attempts: string;
  guarantees_status: string;
  accounting_provision_rate: string;
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

const STATUS_COLORS: Record<string, string> = {
  PENDING: "warning",
  APPROVED: "success",
  REJECTED: "error",
  CANCELLED: "gray",
  EXECUTED: "blue",
};

const REASON_LABELS: Record<string, string> = {
  UNRECOVERABLE: "Créance irrécupérable",
  DEBTOR_DECEASED: "Décès du débiteur",
  DEBTOR_DISAPPEARED: "Disparition du débiteur",
  LEGAL_EXHAUSTED: "Recours judiciaires épuisés",
  COST_BENEFIT: "Coût de recouvrement > montant",
  OTHER: "Autre raison",
};

const LIST_PAGE_SIZE = Math.max(15, DEFAULT_PAGE_SIZE);

export function LoanWriteOffRequestsPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [selectedRequest, setSelectedRequest] =
    useState<LoanWriteOffRequest | null>(null);
  const [actionDialog, setActionDialog] = useState<
    "approve" | "reject" | "execute" | "cancel" | null
  >(null);
  const [actionComment, setActionComment] = useState("");

  const queryClient = useQueryClient();

  function setFilter<T>(setter: (v: T) => void) {
    return (value: T) => {
      setter(value);
      setPage(1);
    };
  }

  const list = useQuery({
    queryKey: ["loan-writeoff-requests", activeTenant, page, LIST_PAGE_SIZE, status, search],
    queryFn: async () =>
      (
        await api.get<Paginated<LoanWriteOffRequest>>("/loan-writeoff-requests/", {
          params: {
            page,
            page_size: LIST_PAGE_SIZE,
            ...(status ? { status } : {}),
            ...(search.trim() ? { search: search.trim() } : {}),
          },
        })
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
      return await api.post(`/loan-writeoff-requests/${id}/${action}/`, {
        comment: comment || "",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["loan-writeoff-requests"] });
      toast.success("Action effectuée avec succès");
      setActionDialog(null);
      setSelectedRequest(null);
      setActionComment("");
    },
    onError: (error: any) => {
      const message =
        error.response?.data?.detail ||
        error.response?.data?.comment?.[0] ||
        "Une erreur est survenue";
      toast.error(message);
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
    request: LoanWriteOffRequest,
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
          icon={AlertCircle}
          title="Demandes de Write-off"
          subtitle="Demandes de passage en perte des crédits irrécupérables"
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

        <QueryStatus query={list} />

        {list.data && (
          <>
            <div className="list-table-wrapper">
              <table className="list-table">
                <thead>
                  <tr>
                    <th>Prêt</th>
                    <th>Statut</th>
                    <th>Motif</th>
                    <th>Solde à passer en perte</th>
                    <th>Jours de retard</th>
                    <th>Demandé par</th>
                    <th>Date demande</th>
                    <th>Validé par</th>
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
                        <Badge color={STATUS_COLORS[request.status] as any}>
                          {STATUS_LABELS[request.status]}
                        </Badge>
                      </td>
                      <td>
                        <span className="text-sm">
                          {REASON_LABELS[request.reason] || request.reason}
                        </span>
                      </td>
                      <td>
                        <span className="font-semibold text-red-600">
                          {formatMoney(request.outstanding_balance, "XOF")}
                        </span>
                      </td>
                      <td>
                        <Badge color="error">{request.days_past_due} jours</Badge>
                      </td>
                      <td>
                        <div className="text-sm">{request.created_by_display}</div>
                        <div className="text-xs text-gray-500">
                          {formatDate(request.created_at)}
                        </div>
                      </td>
                      <td>
                        <div className="text-sm">
                          {formatDate(request.created_at)}
                        </div>
                      </td>
                      <td>
                        {request.reviewed_by_display ? (
                          <div>
                            <div className="text-sm">
                              {request.reviewed_by_display}
                            </div>
                            <div className="text-xs text-gray-500">
                              {formatDate(request.reviewed_at || "")}
                            </div>
                          </div>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setSelectedRequest(request)}
                          >
                            <FileText className="w-4 h-4" />
                          </Button>
                          {request.can_approve && (
                            <Button
                              size="sm"
                              color="success"
                              onClick={() => openActionDialog(request, "approve")}
                            >
                              <Check className="w-4 h-4" />
                            </Button>
                          )}
                          {request.can_reject && (
                            <Button
                              size="sm"
                              color="error"
                              onClick={() => openActionDialog(request, "reject")}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          )}
                          {request.can_execute && (
                            <Button
                              size="sm"
                              color="primary"
                              onClick={() => openActionDialog(request, "execute")}
                            >
                              Exécuter
                            </Button>
                          )}
                          {request.can_cancel && (
                            <Button
                              size="sm"
                              color="gray"
                              onClick={() => openActionDialog(request, "cancel")}
                            >
                              <Ban className="w-4 h-4" />
                            </Button>
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
              setPage={setPage}
              pageSize={LIST_PAGE_SIZE}
              totalCount={list.data.count}
            />
          </>
        )}
      </div>

      {/* Dialog de détails */}
      {selectedRequest && !actionDialog && (
        <Dialog open onOpenChange={() => setSelectedRequest(null)}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Détails de la demande de write-off</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Prêt
                  </label>
                  <div className="mt-1">{selectedRequest.loan_display}</div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Statut
                  </label>
                  <div className="mt-1">
                    <Badge color={STATUS_COLORS[selectedRequest.status] as any}>
                      {STATUS_LABELS[selectedRequest.status]}
                    </Badge>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Motif
                  </label>
                  <div className="mt-1">
                    {REASON_LABELS[selectedRequest.reason]}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Solde à passer en perte
                  </label>
                  <div className="mt-1 font-semibold text-red-600">
                    {formatMoney(selectedRequest.outstanding_balance, "XOF")}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Jours de retard
                  </label>
                  <div className="mt-1">
                    <Badge color="error">
                      {selectedRequest.days_past_due} jours
                    </Badge>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Taux de provisionnement
                  </label>
                  <div className="mt-1">
                    {selectedRequest.accounting_provision_rate}%
                  </div>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">
                  Justification
                </label>
                <div className="mt-1 p-3 bg-gray-50 rounded border text-sm whitespace-pre-wrap">
                  {selectedRequest.justification}
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700">
                  Démarches de recouvrement
                </label>
                <div className="mt-1 p-3 bg-gray-50 rounded border text-sm whitespace-pre-wrap">
                  {selectedRequest.recovery_attempts}
                </div>
              </div>

              {selectedRequest.guarantees_status && (
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Statut des garanties
                  </label>
                  <div className="mt-1 p-3 bg-gray-50 rounded border text-sm whitespace-pre-wrap">
                    {selectedRequest.guarantees_status}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
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
                    <div className="mt-1">
                      {selectedRequest.reviewed_by_display}
                    </div>
                    <div className="text-xs text-gray-500">
                      {formatDate(selectedRequest.reviewed_at || "")}
                    </div>
                  </div>
                )}
              </div>

              {selectedRequest.review_comment && (
                <div>
                  <label className="text-sm font-medium text-gray-700">
                    Commentaire du validateur
                  </label>
                  <div className="mt-1 p-3 bg-blue-50 rounded border border-blue-200 text-sm whitespace-pre-wrap">
                    {selectedRequest.review_comment}
                  </div>
                </div>
              )}

              {selectedRequest.executed_by_display && (
                <div>
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
          </DialogContent>
        </Dialog>
      )}

      {/* Dialog d'action */}
      {actionDialog && selectedRequest && (
        <Dialog open onOpenChange={closeActionDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {actionDialog === "approve" && "Approuver la demande"}
                {actionDialog === "reject" && "Rejeter la demande"}
                {actionDialog === "execute" && "Exécuter le write-off"}
                {actionDialog === "cancel" && "Annuler la demande"}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded">
                <p className="text-sm text-amber-800">
                  {actionDialog === "approve" &&
                    "Vous allez approuver cette demande de passage en perte. Cette action nécessite une vérification complète du dossier."}
                  {actionDialog === "reject" &&
                    "Vous allez rejeter cette demande. Un commentaire est obligatoire pour justifier le rejet."}
                  {actionDialog === "execute" &&
                    "⚠️ ATTENTION : Cette action est IRRÉVERSIBLE. Le prêt sera définitivement passé en perte (statut DEFAULTED)."}
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
                <Button variant="secondary" onClick={closeActionDialog}>
                  Annuler
                </Button>
                <Button
                  color={
                    actionDialog === "execute"
                      ? "error"
                      : actionDialog === "approve"
                        ? "success"
                        : "primary"
                  }
                  onClick={() => handleAction(actionDialog)}
                  disabled={
                    performAction.isPending ||
                    (actionDialog === "reject" && !actionComment.trim())
                  }
                >
                  {performAction.isPending ? "En cours..." : "Confirmer"}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

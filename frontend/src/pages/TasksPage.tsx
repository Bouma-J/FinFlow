import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Bell,
  Building2,
  CalendarClock,
  ClipboardCheck,
  FileText,
  Layers,
  RotateCcw,
  Search,
  User,
  UserCircle,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { MyDossierRow } from "@/api/types";
import {
  Badge,
  EmptyState,
  PageHeader,
  QueryStatus,
  formatDate,
  formatMoney,
} from "@/components/ui";

const MY_TASK_LABELS: Record<string, string> = {
  PENDING: "À traiter",
  APPROVED: "Traité (approuvé)",
  RETURNED: "Traité (retourné)",
  REJECTED: "Traité (rejeté)",
  SKIPPED: "Ignoré",
};

function clientKind(t: MyDossierRow["client_type"]): "particulier" | "entreprise" {
  return t === "INDIVIDUAL" ? "particulier" : "entreprise";
}

export function TasksPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["my-dossiers"],
    queryFn: async () =>
      (await api.get<{ results: MyDossierRow[] }>("/approval-tasks/my_dossiers/"))
        .data,
  });

  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [clientTypeFilter, setClientTypeFilter] = useState("");
  const [initiatorFilter, setInitiatorFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [onlyActionable, setOnlyActionable] = useState(false);

  const rows = useMemo(() => data?.results ?? [], [data]);

  const statusOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const r of rows) if (r.status) map.set(r.status, r.status_display);
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [rows]);

  const initiatorOptions = useMemo(() => {
    const seen = new Set<string>();
    for (const r of rows) if (r.created_by_display) seen.add(r.created_by_display);
    return Array.from(seen).sort();
  }, [rows]);

  const actionableCount = useMemo(
    () => rows.filter((r) => r.is_actionable).length,
    [rows],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const from = dateFrom ? new Date(dateFrom) : null;
    const to = dateTo ? new Date(`${dateTo}T23:59:59`) : null;
    return rows.filter((r) => {
      if (onlyActionable && !r.is_actionable) return false;
      if (statusFilter && r.status !== statusFilter) return false;
      if (clientTypeFilter && clientKind(r.client_type) !== clientTypeFilter)
        return false;
      if (initiatorFilter && r.created_by_display !== initiatorFilter)
        return false;
      if ((from || to) && r.created_at) {
        const d = new Date(r.created_at);
        if (from && d < from) return false;
        if (to && d > to) return false;
      }
      if (!q) return true;
      const haystack = [
        r.reference,
        r.client_display,
        r.product_label,
        r.created_by_display,
        r.definition_name,
        r.current_step_name,
        r.my_step_name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [
    rows,
    query,
    statusFilter,
    clientTypeFilter,
    initiatorFilter,
    dateFrom,
    dateTo,
    onlyActionable,
  ]);

  const hasFilters =
    !!query ||
    !!statusFilter ||
    !!clientTypeFilter ||
    !!initiatorFilter ||
    !!dateFrom ||
    !!dateTo ||
    onlyActionable;

  function resetFilters() {
    setQuery("");
    setStatusFilter("");
    setClientTypeFilter("");
    setInitiatorFilter("");
    setDateFrom("");
    setDateTo("");
    setOnlyActionable(false);
  }

  return (
    <div className="page-shell">
      <PageHeader
        icon={ClipboardCheck}
        title="Mes validations"
        subtitle="Tous les dossiers de vos niveaux de validation"
      />
      <QueryStatus
        isLoading={isLoading}
        isError={isError}
        isEmpty={rows.length === 0}
        emptyMessage="Aucun dossier ne concerne vos niveaux de validation."
        onRetry={() => refetch()}
      >
        <>
          <div className="valid-filters">
            <div className="list-toolbar">
              <div className="toolbar-search">
                <Search size={16} />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Rechercher (référence, client, produit, initiateur, étape)…"
                />
                {query && (
                  <button
                    type="button"
                    className="toolbar-clear"
                    aria-label="Effacer la recherche"
                    onClick={() => setQuery("")}
                  >
                    <X size={15} />
                  </button>
                )}
              </div>
              <button
                type="button"
                className={`chip-toggle${onlyActionable ? " is-on" : ""}`}
                onClick={() => setOnlyActionable((v) => !v)}
                title="N'afficher que les dossiers en attente de mon action"
              >
                <Bell size={14} />À traiter ({actionableCount})
              </button>
            </div>

            <div className="filter-row">
              <label className="filter-field">
                <span>Statut</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="">Tous</option>
                  {statusOptions.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="filter-field">
                <span>Type de client</span>
                <select
                  value={clientTypeFilter}
                  onChange={(e) => setClientTypeFilter(e.target.value)}
                >
                  <option value="">Tous</option>
                  <option value="particulier">Particulier</option>
                  <option value="entreprise">Entreprise</option>
                </select>
              </label>

              <label className="filter-field">
                <span>Initiateur</span>
                <select
                  value={initiatorFilter}
                  onChange={(e) => setInitiatorFilter(e.target.value)}
                >
                  <option value="">Tous</option>
                  {initiatorOptions.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="filter-field">
                <span>Créé du</span>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </label>

              <label className="filter-field">
                <span>au</span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </label>

              {hasFilters && (
                <button
                  type="button"
                  className="btn btn-ghost btn-sm filter-reset"
                  onClick={resetFilters}
                >
                  <RotateCcw size={14} />
                  Réinitialiser
                </button>
              )}
              <span className="toolbar-count">
                {filtered.length} / {rows.length} dossier(s)
              </span>
            </div>
          </div>

          {filtered.length === 0 ? (
            <EmptyState message="Aucun dossier ne correspond à vos critères." />
          ) : (
            <div className="valid-grid">
              {filtered.map((r) => {
                const overdue =
                  r.is_actionable &&
                  !!r.my_task_due_at &&
                  new Date(r.my_task_due_at) < new Date();
                return (
                  <Link
                    key={`${r.target_kind || "CREDIT"}-${r.id}`}
                    to={r.detail_path || `/dossiers/${r.id}`}
                    className={`valid-card${r.is_actionable ? " is-actionable" : ""}${
                      overdue ? " is-overdue" : ""
                    }`}
                  >
                    <div className="valid-card-top">
                      <span className="valid-ref">
                        <FileText size={15} />
                        {r.reference || "—"}
                      </span>
                      <Badge value={r.status} label={r.status_display} />
                    </div>

                    <div className="valid-client">
                      {r.client_type === "INDIVIDUAL" ? (
                        <User size={14} />
                      ) : (
                        <Building2 size={14} />
                      )}
                      {r.client_display}
                    </div>

                    <div className="valid-amount">
                      {formatMoney(r.amount_requested, r.currency || "XOF")}
                      <small>{r.product_label || "Montant demandé"}</small>
                    </div>

                    <div className="valid-meta">
                      <span className="valid-chip">
                        <Layers />
                        {r.current_step_name || r.definition_name}
                      </span>
                      {r.created_by_display && (
                        <span className="valid-chip">
                          <UserCircle />
                          {r.created_by_display}
                        </span>
                      )}
                      {r.created_at && (
                        <span className="valid-chip">
                          <CalendarClock />
                          {formatDate(r.created_at)}
                        </span>
                      )}
                    </div>

                    <div className="valid-card-foot">
                      {r.my_task_status ? (
                        <Badge
                          value={r.is_actionable ? "PENDING" : "APPROVED"}
                          label={
                            MY_TASK_LABELS[r.my_task_status] ?? r.my_task_status
                          }
                        />
                      ) : (
                        <Badge value="SUBMITTED" label="En amont" />
                      )}
                      <span className="valid-open">
                        Ouvrir le dossier
                        <ArrowRight size={16} />
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </>
      </QueryStatus>
    </div>
  );
}

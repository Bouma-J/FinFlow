import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleDollarSign, Download } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import type {
  AgentCollectionDashboard,
  CollectionCase,
  CollectionEscalationRule,
  CollectionStage,
  HearingAgendaItem,
  Paginated,
  ParClass,
} from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import {
  Badge,
  PageHeader,
  PaginationBar,
  QueryStatus,
  formatMoney,
} from "@/components/ui";

const PAR_OPTIONS: { value: "" | ParClass; label: string }[] = [
  { value: "", label: "Toutes classes PAR" },
  { value: "PAR0", label: "Sain" },
  { value: "PAR1_30", label: "PAR 1-30" },
  { value: "PAR31_90", label: "PAR 31-90" },
  { value: "PAR91_180", label: "PAR 91-180" },
  { value: "PAR180_PLUS", label: "PAR > 180" },
];

const STAGE_OPTIONS = [
  { value: "", label: "Tous stades" },
  { value: "AMICABLE", label: "Amiable" },
  { value: "PRECONTENTIOUS", label: "Précontentieux" },
  { value: "LITIGATION", label: "Contentieux" },
  { value: "CLOSED", label: "Clôturé" },
];

const ESCALATION_STAGES: {
  value: Exclude<CollectionStage, "CLOSED">;
  label: string;
}[] = [
  { value: "AMICABLE", label: "Amiable" },
  { value: "PRECONTENTIOUS", label: "Précontentieux" },
  { value: "LITIGATION", label: "Contentieux" },
];

export function CollectionsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const qc = useQueryClient();
  const canManageCase = hasPerm(user, "collections.change_collectioncase");
  const [page, setPage] = useState(1);
  const [parClass, setParClass] = useState("");
  const [stage, setStage] = useState("");
  const [openOnly, setOpenOnly] = useState(true);
  const [mine, setMine] = useState(!canManageCase);
  const [unassigned, setUnassigned] = useState(false);
  const [followupDue, setFollowupDue] = useState(() =>
    Boolean(
      (location.state as { followupDue?: boolean } | null)?.followupDue,
    ),
  );
  const [brokenPromises, setBrokenPromises] = useState(false);
  const [search, setSearch] = useState("");
  const [dashScope, setDashScope] = useState<"mine" | "team">(
    canManageCase ? "team" : "mine",
  );
  const [showRules, setShowRules] = useState(false);
  const [ruleDays, setRuleDays] = useState("31");
  const [ruleStage, setRuleStage] =
    useState<Exclude<CollectionStage, "CLOSED">>("PRECONTENTIOUS");
  const [ruleLabel, setRuleLabel] = useState("");
  const [refreshNotice, setRefreshNotice] = useState<string | null>(null);

  useEffect(() => {
    const fromHub = (location.state as { followupDue?: boolean } | null)
      ?.followupDue;
    if (fromHub) {
      setFollowupDue(true);
      setPage(1);
    }
  }, [location.state]);

  const canManageRules = hasPerm(
    user,
    "collections.change_collectionescalationrule",
  );

  const dashboard = useQuery({
    queryKey: ["collection-agent-dashboard", dashScope],
    queryFn: async () =>
      (
        await api.get<AgentCollectionDashboard>(
          "/collection-cases/agent-dashboard/",
          { params: { scope: dashScope } },
        )
      ).data,
  });

  const hearings = useQuery({
    queryKey: ["hearings-agenda"],
    queryFn: async () =>
      (
        await api.get<HearingAgendaItem[]>(
          "/collection-cases/hearings-agenda/",
          { params: { within_days: 30 } },
        )
      ).data,
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: [
      "collection-cases",
      page,
      parClass,
      stage,
      openOnly,
      mine,
      unassigned,
      followupDue,
      brokenPromises,
      search,
    ],
    queryFn: async () =>
      (
        await api.get<Paginated<CollectionCase>>("/collection-cases/", {
          params: {
            page,
            ...(parClass ? { par_class: parClass } : {}),
            ...(stage ? { stage } : {}),
            ...(openOnly ? { open: 1 } : {}),
            ...(mine ? { mine: 1 } : {}),
            ...(unassigned ? { unassigned: 1 } : {}),
            ...(followupDue ? { followup_due: 1 } : {}),
            ...(brokenPromises ? { broken_promises: 1 } : {}),
            ...(search.trim() ? { search: search.trim() } : {}),
            ordering: followupDue ? "next_action_date" : "-days_overdue",
          },
        })
      ).data,
  });

  const refreshOverdue = useMutation({
    mutationFn: async () => {
      const res = await api.post(
        "/collection-cases/refresh-overdue/",
        {},
        { validateStatus: (s) => s === 200 || s === 202 },
      );
      return { httpStatus: res.status, data: res.data as Record<string, unknown> };
    },
    onSuccess: async (payload) => {
      const invalidate = () => {
        qc.invalidateQueries({ queryKey: ["collection-cases"] });
        qc.invalidateQueries({ queryKey: ["collection-agent-dashboard"] });
      };
      invalidate();
      setRefreshNotice(null);
      const taskId =
        typeof payload.data?.task_id === "string"
          ? payload.data.task_id
          : null;
      if (payload.httpStatus === 202 && taskId) {
        setRefreshNotice("Recalcul en cours…");
        try {
          const { pollAsyncTask } = await import("@/utils/pollAsyncTask");
          await pollAsyncTask(taskId, {
            intervalMs: 3000,
            maxAttempts: 40,
            onTick: invalidate,
          });
          invalidate();
          setRefreshNotice("Retards recalculés.");
        } catch (e) {
          setRefreshNotice(
            e instanceof Error
              ? e.message
              : "Échec du recalcul des retards.",
          );
        }
      } else if (payload.httpStatus === 200) {
        setRefreshNotice("Retards recalculés.");
      }
    },
    onError: () => {
      setRefreshNotice("Impossible de lancer le recalcul des retards.");
    },
  });

  const rules = useQuery({
    queryKey: ["collection-escalation-rules"],
    queryFn: async () =>
      (
        await api.get<Paginated<CollectionEscalationRule>>(
          "/collection-escalation-rules/",
        )
      ).data,
    enabled: showRules && canManageRules,
  });

  const addRule = useMutation({
    mutationFn: async () =>
      (
        await api.post<CollectionEscalationRule>(
          "/collection-escalation-rules/",
          {
            min_days_overdue: Number(ruleDays),
            target_stage: ruleStage,
            label: ruleLabel,
            is_active: true,
          },
        )
      ).data,
    onSuccess: () => {
      setRuleLabel("");
      qc.invalidateQueries({ queryKey: ["collection-escalation-rules"] });
    },
  });

  const toggleRule = useMutation({
    mutationFn: async (rule: CollectionEscalationRule) =>
      api.patch(`/collection-escalation-rules/${rule.id}/`, {
        is_active: !rule.is_active,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["collection-escalation-rules"] }),
  });

  function submitRule(e: FormEvent) {
    e.preventDefault();
    if (!ruleDays || Number(ruleDays) < 1) return;
    addRule.mutate();
  }

  function applyKpiFilter(
    kind: "mine" | "followups" | "broken" | "unassigned",
  ) {
    setPage(1);
    setFollowupDue(kind === "followups");
    setBrokenPromises(kind === "broken");
    setUnassigned(kind === "unassigned");
    if (kind === "mine") {
      setMine(true);
      setUnassigned(false);
    } else if (kind === "unassigned") {
      setMine(false);
    } else if (dashScope === "team") {
      setMine(false);
    }
  }

  async function exportCsv() {
    const res = await api.get("/collection-cases/export/", {
      params: {
        ...(parClass ? { par_class: parClass } : {}),
        ...(stage ? { stage } : {}),
        ...(openOnly ? { open: 1 } : {}),
        ...(mine ? { mine: 1 } : {}),
        ...(unassigned ? { unassigned: 1 } : {}),
        ...(followupDue ? { followup_due: 1 } : {}),
        ...(brokenPromises ? { broken_promises: 1 } : {}),
        ...(search.trim() ? { search: search.trim() } : {}),
        ordering: followupDue ? "next_action_date" : "-days_overdue",
      },
      responseType: "blob",
    });
    const url = URL.createObjectURL(res.data as Blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "recouvrement.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  const dash = dashboard.data;

  return (
    <div className="page-shell">
      <PageHeader
        icon={CircleDollarSign}
        title="Recouvrement"
        subtitle="Dossiers en retard, encaissements et suivi terrain"
        actions={
          <div className="row-actions" style={{ gap: 8 }}>
            {canManageCase && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={refreshOverdue.isPending}
                onClick={() => refreshOverdue.mutate()}
              >
                {refreshOverdue.isPending
                  ? "Lancement…"
                  : "Recalculer les retards"}
              </button>
            )}
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={exportCsv}
            >
              <Download size={14} /> Export CSV
            </button>
          </div>
        }
      />

      {refreshNotice && (
        <p
          className={
            refreshNotice.includes("Échec") ||
            refreshNotice.includes("Impossible") ||
            refreshNotice.includes("Délai")
              ? "form-error"
              : "muted"
          }
          style={{ marginBottom: 10 }}
        >
          {refreshNotice}
        </p>
      )}

      {canManageCase && (
        <div className="row-actions" style={{ marginBottom: 10, gap: 8 }}>
          <button
            type="button"
            className={`btn btn-sm ${dashScope === "mine" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setDashScope("mine")}
          >
            Mes indicateurs
          </button>
          <button
            type="button"
            className={`btn btn-sm ${dashScope === "team" ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setDashScope("team")}
          >
            Équipe / filiale
          </button>
        </div>
      )}

      {dash && (
        <div className="mini-kpis" style={{ marginBottom: 16 }}>
          <button
            type="button"
            className="mini-kpi"
            onClick={() => {
              setPage(1);
              setFollowupDue(false);
              setBrokenPromises(false);
              setUnassigned(false);
              setMine(dashScope === "mine");
            }}
            title="Filtrer le portefeuille"
          >
            <span className="mk-value">{dash.assigned_open}</span>
            <span className="mk-label">
              {dashScope === "team" ? "Dossiers ouverts" : "Mon portefeuille"}
            </span>
          </button>
          {dashScope === "team" && (
            <button
              type="button"
              className="mini-kpi"
              onClick={() => applyKpiFilter("unassigned")}
            >
              <span className="mk-value">{dash.unassigned_open ?? 0}</span>
              <span className="mk-label">Non affectés</span>
            </button>
          )}
          <button
            type="button"
            className="mini-kpi"
            onClick={() => applyKpiFilter("followups")}
          >
            <span className="mk-value">{dash.followups_due}</span>
            <span className="mk-label">Actions dues</span>
          </button>
          <div className="mini-kpi">
            <span className="mk-value">{dash.pending_promises}</span>
            <span className="mk-label">Promesses en cours</span>
          </div>
          <button
            type="button"
            className="mini-kpi"
            onClick={() => applyKpiFilter("broken")}
          >
            <span className="mk-value">{dash.broken_promises_30d}</span>
            <span className="mk-label">Promesses rompues (30 j)</span>
          </button>
          <div className="mini-kpi">
            <span className="mk-value">
              {formatMoney(dash.repayments_this_month_amount)}
            </span>
            <span className="mk-label">
              Encaissé ce mois ({dash.repayments_this_month_count})
            </span>
          </div>
        </div>
      )}

      {!!hearings.data?.length && (
        <div className="card" style={{ marginBottom: 16, padding: 14 }}>
          <strong style={{ display: "block", marginBottom: 8 }}>
            Agenda audiences (30 j)
          </strong>
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Client</th>
                <th>Juridiction</th>
                <th>Cabinet</th>
              </tr>
            </thead>
            <tbody>
              {hearings.data.map((h) => (
                <tr
                  key={h.id}
                  className="row-clickable"
                  onClick={() =>
                    navigate(`/recouvrement/${h.case_id}/contentieux/${h.id}`)
                  }
                >
                  <td>
                    {h.hearing_date}
                    {h.hearing_time
                      ? ` ${String(h.hearing_time).slice(0, 5)}`
                      : ""}
                  </td>
                  <td>{h.client_name}</td>
                  <td className="small">{h.court_name || "—"}</td>
                  <td className="small">{h.law_firm_name || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dash && dash.due_followups.length > 0 && (
        <div className="card" style={{ marginBottom: 16, padding: 14 }}>
          <strong style={{ display: "block", marginBottom: 8 }}>
            Prochaines actions
          </strong>
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Dossier</th>
                <th>Client</th>
                <th>Type</th>
                <th className="num">Impayé</th>
              </tr>
            </thead>
            <tbody>
              {dash.due_followups.map((f) => (
                <tr
                  key={f.id}
                  className="row-clickable"
                  onClick={() => navigate(`/recouvrement/${f.id}`)}
                >
                  <td>{f.next_action_date || "—"}</td>
                  <td>{f.application_reference || f.id.slice(0, 8)}</td>
                  <td>{f.client_name}</td>
                  <td className="small">
                    {f.next_action_type || "—"}
                    {f.next_action_note ? ` · ${f.next_action_note}` : ""}
                  </td>
                  <td className="num">{formatMoney(f.overdue_amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="filters-bar card">
        <input
          type="search"
          placeholder="Référence, client, CBS…"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
        <select
          value={parClass}
          onChange={(e) => {
            setPage(1);
            setParClass(e.target.value);
          }}
        >
          {PAR_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={stage}
          onChange={(e) => {
            setPage(1);
            setStage(e.target.value);
          }}
        >
          {STAGE_OPTIONS.map((o) => (
            <option key={o.value || "all-stage"} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={openOnly}
            onChange={(e) => {
              setPage(1);
              setOpenOnly(e.target.checked);
            }}
          />
          <span>Ouverts seulement</span>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={mine}
            onChange={(e) => {
              setPage(1);
              setMine(e.target.checked);
              if (e.target.checked) setUnassigned(false);
            }}
          />
          <span>Mon portefeuille</span>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={unassigned}
            onChange={(e) => {
              setPage(1);
              setUnassigned(e.target.checked);
              if (e.target.checked) setMine(false);
            }}
          />
          <span>Non affectés</span>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={followupDue}
            onChange={(e) => {
              setPage(1);
              setFollowupDue(e.target.checked);
            }}
          />
          <span>Actions dues</span>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={brokenPromises}
            onChange={(e) => {
              setPage(1);
              setBrokenPromises(e.target.checked);
            }}
          />
          <span>Promesses rompues</span>
        </label>
        {canManageRules && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setShowRules((v) => !v)}
          >
            {showRules ? "Masquer règles" : "Règles d'escalade"}
          </button>
        )}
      </div>

      {showRules && canManageRules && (
        <div className="card" style={{ marginBottom: 16, padding: 14 }}>
          <strong style={{ display: "block", marginBottom: 8 }}>
            Escalade automatique (PAR / DPD)
          </strong>
          <p className="muted small" style={{ marginBottom: 12 }}>
            Dès que le retard atteint le seuil, le dossier passe au stade cible
            (uniquement vers le haut).
          </p>
          <form
            className="inline-form"
            style={{ boxShadow: "none", border: 0, padding: 0, marginBottom: 12 }}
            onSubmit={submitRule}
          >
            <div className="form-grid">
              <label className="field">
                <span>Seuil (jours)</span>
                <input
                  type="number"
                  min={1}
                  value={ruleDays}
                  onChange={(e) => setRuleDays(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Stade cible</span>
                <select
                  value={ruleStage}
                  onChange={(e) =>
                    setRuleStage(
                      e.target.value as Exclude<CollectionStage, "CLOSED">,
                    )
                  }
                >
                  {ESCALATION_STAGES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Libellé</span>
                <input
                  value={ruleLabel}
                  onChange={(e) => setRuleLabel(e.target.value)}
                  placeholder="optionnel"
                />
              </label>
            </div>
            <button
              className="btn btn-primary btn-sm"
              disabled={addRule.isPending}
            >
              Ajouter la règle
            </button>
          </form>
          {!rules.data?.results.length ? (
            <p className="muted small">Aucune règle (les défauts seront créés).</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Seuil</th>
                  <th>Stade</th>
                  <th>Libellé</th>
                  <th>Active</th>
                </tr>
              </thead>
              <tbody>
                {rules.data.results.map((r) => (
                  <tr key={r.id}>
                    <td>≥ {r.min_days_overdue} j</td>
                    <td>{r.target_stage_display}</td>
                    <td className="small">{r.label || "—"}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => toggleRule.mutate(r)}
                      >
                        {r.is_active ? "Oui" : "Non"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      <QueryStatus
        isLoading={isLoading}
        isError={isError}
        isEmpty={!data?.results.length}
        emptyMessage="Aucun dossier de recouvrement."
        onRetry={() => refetch()}
      >
        <>
          <table className="table card">
            <thead>
              <tr>
                <th>Dossier</th>
                <th>Client</th>
                <th>Produit</th>
                <th>PAR</th>
                <th>Stade</th>
                <th className="num">Jours</th>
                <th className="num">Impayé</th>
                <th>Prochaine action</th>
                <th>Agent</th>
              </tr>
            </thead>
            <tbody>
              {(data?.results ?? []).map((c) => (
                <tr
                  key={c.id}
                  className="row-clickable"
                  onClick={() => navigate(`/recouvrement/${c.id}`)}
                >
                  <td>{c.application_reference || c.loan.slice(0, 8)}</td>
                  <td>{c.client_name}</td>
                  <td className="small">{c.product_name || "—"}</td>
                  <td>
                    <Badge value={c.par_class_display} />
                  </td>
                  <td>
                    <Badge value={c.stage_display} />
                  </td>
                  <td className="num">{c.days_overdue}</td>
                  <td className="num">{formatMoney(c.overdue_amount)}</td>
                  <td className="small">
                    {c.next_action_date
                      ? `${c.next_action_date}${
                          c.next_action_type_display
                            ? ` · ${c.next_action_type_display}`
                            : ""
                        }`
                      : "—"}
                  </td>
                  <td className="small">{c.assigned_to_name || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <PaginationBar
            page={page}
            count={data?.count ?? 0}
            onPageChange={setPage}
          />
        </>
      </QueryStatus>
    </div>
  );
}

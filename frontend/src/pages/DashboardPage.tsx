import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  Banknote,
  Boxes,
  Calculator,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  FilePlus2,
  FileSignature,
  FileText,
  Filter,
  Layers,
  RotateCcw,
  ServerCrash,
  ShieldCheck,
  UserRound,
  UsersRound,
  Wallet,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type {
  AdminUser,
  Agency,
  CreditProduct,
  DashboardData,
  Paginated,
} from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import {
  EmptyState,
  Spinner,
  StatCard,
  formatMoney,
} from "@/components/ui";
import { useTenantBranding } from "@/hooks/useTenantBranding";

const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Brouillon",
  SUBMITTED: "Soumis",
  IN_APPROVAL: "En approbation",
  APPROVED: "Approuvé",
  REJECTED: "Rejeté",
  RETURNED: "Retourné",
  CONTRACT_GENERATED: "Contrat généré",
  DISBURSEMENT_PENDING: "Décaissement en attente",
  DISBURSED: "Décaissé",
  CLOSED: "Clôturé",
  CANCELLED: "Annulé",
};

const STATUS_TONE: Record<string, string> = {
  APPROVED: "success",
  DISBURSED: "success",
  CONTRACT_GENERATED: "success",
  DISBURSEMENT_PENDING: "warning",
  REJECTED: "danger",
  RETURNED: "warning",
  IN_APPROVAL: "info",
  SUBMITTED: "info",
  DRAFT: "muted",
  CANCELLED: "muted",
  CLOSED: "muted",
};

const CLIENT_TYPE_LABELS: Record<string, string> = {
  INDIVIDUAL: "Particuliers",
  PROFESSIONAL: "Professionnels",
  CORPORATE: "Entreprises",
};

const PAR_LABELS: Record<string, string> = {
  PAR0: "Sain (PAR 0)",
  PAR1_30: "PAR 1-30 j",
  PAR31_90: "PAR 31-90 j",
  PAR91_180: "PAR 91-180 j",
  PAR180_PLUS: "PAR > 180 j",
};

const STAGE_LABELS: Record<string, string> = {
  AMICABLE: "Amiable",
  PRECONTENTIOUS: "Précontentieux",
  LITIGATION: "Contentieux",
  CLOSED: "Clôturé",
};

type DashFilters = {
  date_from: string;
  date_to: string;
  agency: string;
  owner: string;
  status: string;
  product: string;
  client_type: string;
};

const EMPTY_FILTERS: DashFilters = {
  date_from: "",
  date_to: "",
  agency: "",
  owner: "",
  status: "",
  product: "",
  client_type: "",
};

function num(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  return typeof value === "string" ? Number(value) || 0 : value;
}

function compactMoney(value: string | number | null | undefined): string {
  const n = num(value);
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)} Md`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)} M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)} k`;
  return n.toLocaleString("fr-FR");
}

function monthLabel(ym: string): string {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m - 1, 1)
    .toLocaleDateString("fr-FR", { month: "short" })
    .replace(".", "");
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function presetRange(key: string): Pick<DashFilters, "date_from" | "date_to"> {
  const today = new Date();
  const to = isoDate(today);
  if (key === "7d") {
    const from = new Date(today);
    from.setDate(from.getDate() - 6);
    return { date_from: isoDate(from), date_to: to };
  }
  if (key === "30d") {
    const from = new Date(today);
    from.setDate(from.getDate() - 29);
    return { date_from: isoDate(from), date_to: to };
  }
  if (key === "month") {
    return {
      date_from: isoDate(new Date(today.getFullYear(), today.getMonth(), 1)),
      date_to: to,
    };
  }
  if (key === "year") {
    return {
      date_from: isoDate(new Date(today.getFullYear(), 0, 1)),
      date_to: to,
    };
  }
  return { date_from: "", date_to: "" };
}

function TrendChart({
  data,
}: {
  data: DashboardData["credits"]["monthly"];
}) {
  const max = Math.max(1, ...data.map((d) => num(d.amount)));
  const totalCount = data.reduce((s, d) => s + d.count, 0);
  if (totalCount === 0)
    return <EmptyState message="Aucune activité sur la période." />;

  return (
    <div className="trend-chart">
      {data.map((d) => {
        const h = Math.round((num(d.amount) / max) * 100);
        return (
          <div className="trend-col" key={d.month}>
            <span className="trend-count">{d.count}</span>
            <div className="trend-bar-track">
              <div
                className="trend-bar"
                style={{ height: `${Math.max(h, 3)}%` }}
                title={`${monthLabel(d.month)} · ${d.count} dossier(s) · ${formatMoney(
                  d.amount,
                )}`}
              />
            </div>
            <span className="trend-label">{monthLabel(d.month)}</span>
          </div>
        );
      })}
    </div>
  );
}

function DistBars({
  rows,
  emptyMessage,
}: {
  rows: {
    label: string;
    count: number;
    amount?: string | number | null;
    tone?: string;
  }[];
  emptyMessage: string;
}) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  if (rows.length === 0) return <EmptyState message={emptyMessage} />;
  return (
    <ul className="dist-bars">
      {rows.map((r) => (
        <li key={r.label}>
          <div className="dist-row">
            <span className="dist-label">{r.label}</span>
            <span className="dist-meta">
              {r.count}
              {r.amount != null ? ` · ${compactMoney(r.amount)}` : ""}
            </span>
          </div>
          <div className="dist-track">
            <div
              className={`dist-fill tone-${r.tone ?? "info"}`}
              style={{ width: `${(r.count / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function ClientDonut({
  rows,
  total,
}: {
  rows: { client_type: string; count: number }[];
  total: number;
}) {
  if (total === 0) return <EmptyState message="Aucun client." />;
  const colors = [
    "var(--brand)",
    "var(--brand-dark)",
    "var(--accent)",
  ];
  return (
    <ul className="client-donut-list">
      {rows.map((r, i) => {
        const pct = total ? Math.round((r.count / total) * 100) : 0;
        return (
          <li key={r.client_type}>
            <span
              className="cd-dot"
              style={{ background: colors[i % colors.length] }}
            />
            <span className="cd-label">
              {CLIENT_TYPE_LABELS[r.client_type] ?? r.client_type}
            </span>
            <span className="cd-value">
              {r.count} ({pct} %)
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function QuickAction({
  to,
  icon: Icon,
  label,
}: {
  to: string;
  icon: LucideIcon;
  label: string;
}) {
  return (
    <Link to={to} className="quick-action">
      <span className="qa-icon">
        <Icon size={18} />
      </span>
      <span className="qa-label">{label}</span>
      <ArrowUpRight size={15} className="qa-arrow" />
    </Link>
  );
}

function KpiSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="kpi-section">
      <h3 className="kpi-section-title">{title}</h3>
      <div className="stat-grid dash-kpi-grid">{children}</div>
    </section>
  );
}

function isPresetActive(
  filters: DashFilters,
  key: string,
): boolean {
  const range = presetRange(key);
  return (
    filters.date_from === range.date_from && filters.date_to === range.date_to
  );
}

export function DashboardPage() {
  const { activeTenant, user } = useAuth();
  const { tenantName, tenantCode } = useTenantBranding();
  const [filters, setFilters] = useState<DashFilters>(EMPTY_FILTERS);

  const scope = user?.data_scope ?? "AGENCY";
  const isGroup = !!user?.is_group_level;
  const canPickAgency = scope !== "OWN" || isGroup;
  const canPickOwner = scope === "TENANT" || isGroup || !!user?.is_superuser;
  const showAgencyFilter = canPickAgency;
  const showOwnerFilter = canPickOwner;

  const agencyOptions = useMemo(() => {
    if (scope === "AGENCY" && !isGroup) {
      return user?.agencies_detail ?? [];
    }
    return null; // charger via API
  }, [scope, isGroup, user?.agencies_detail]);

  const { data: agenciesPage } = useQuery({
    queryKey: ["dash-agencies", activeTenant],
    queryFn: async () =>
      (
        await api.get<Paginated<Agency>>("/agencies/", {
          params: {
            page_size: 200,
            is_active: true,
            ...(activeTenant ? { tenant: activeTenant } : {}),
          },
        })
      ).data,
    enabled: showAgencyFilter && agencyOptions === null && (!!activeTenant || !isGroup),
  });

  const agencies =
    agencyOptions ??
    agenciesPage?.results ??
    [];

  const { data: ownersPage } = useQuery({
    queryKey: ["dash-owners", activeTenant, filters.agency],
    queryFn: async () =>
      (
        await api.get<Paginated<AdminUser>>("/users/", {
          params: {
            page_size: 200,
            is_active: true,
            is_group_level: false,
            ...(activeTenant ? { tenant: activeTenant } : {}),
            ...(filters.agency ? { agency: filters.agency } : {}),
          },
        })
      ).data,
    enabled: showOwnerFilter && (!!activeTenant || !isGroup),
  });

  const { data: productsPage } = useQuery({
    queryKey: ["dash-products", activeTenant],
    queryFn: async () =>
      (
        await api.get<Paginated<CreditProduct>>("/credit-products/", {
          params: {
            page_size: 200,
            is_active: true,
            ...(activeTenant ? { tenant: activeTenant } : {}),
          },
        })
      ).data,
    enabled: !!activeTenant || !isGroup,
  });

  const queryParams = useMemo(() => {
    const p: Record<string, string> = { live: "1" };
    if (activeTenant) p.tenant = activeTenant;
    (Object.keys(filters) as (keyof DashFilters)[]).forEach((k) => {
      if (filters[k]) p[k === "owner" ? "owner" : k] = filters[k];
    });
    if (scope === "OWN" && user?.id && !filters.owner) {
      p.owner = user.id;
    }
    return p;
  }, [activeTenant, filters, scope, user?.id]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["dashboard", queryParams],
    queryFn: async () =>
      (
        await api.get<DashboardData>("/reporting/dashboard/", {
          params: queryParams,
        })
      ).data,
  });

  const setFilter = <K extends keyof DashFilters>(key: K, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => setFilters(EMPTY_FILTERS);

  const hasActiveFilters = Object.values(filters).some(Boolean);

  const outstanding = num(data?.portfolio.outstanding);
  const overdue = num(data?.risk.total_overdue);
  const parRatio =
    outstanding + overdue > 0
      ? (overdue / (outstanding + overdue)) * 100
      : null;
  const s = data?.credits.summary;

  return (
    <div className="dashboard-page">
      <header className="dash-hero">
        <div className="dash-hero-glow" aria-hidden />
        <div className="dash-hero-copy">
          <p className="dash-hero-kicker">
            {tenantCode
              ? `${tenantCode} · ${tenantName}`
              : tenantName || "Fin Flow"}
          </p>
          <h1 className="dash-hero-title">
            {`${greeting()}, ${user?.first_name || user?.username || ""}`.trim()}
          </h1>
          <p className="dash-hero-sub">
            {isGroup && !activeTenant
              ? "Vue consolidée Groupe — synthèse multi-filiales"
              : "Pilotage opérationnel filtré selon votre périmètre"}
          </p>
        </div>
        <div className="dash-hero-actions">
          {hasPerm(user, "credits.add_creditapplication") && (
            <QuickAction
              to="/dossiers/nouveau"
              icon={FilePlus2}
              label="Nouveau dossier"
            />
          )}
          <QuickAction to="/clients" icon={UserRound} label="Clients" />
          <QuickAction
            to="/taches"
            icon={ClipboardCheck}
            label="Mes validations"
          />
          <QuickAction
            to="/simulateur"
            icon={Calculator}
            label="Simulateur"
          />
        </div>
      </header>

      <section className="dash-toolbar" aria-label="Filtres du tableau de bord">
        <div className="dash-toolbar-top">
          <div className="dash-toolbar-label">
            <Filter size={16} />
            <span>Filtres</span>
            {isFetching && <span className="dash-live">Mise à jour…</span>}
          </div>
          <div className="dash-presets">
            {[
              ["7d", "7 jours"],
              ["30d", "30 jours"],
              ["month", "Mois en cours"],
              ["year", "Année"],
            ].map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={`dash-chip${isPresetActive(filters, key) ? " is-active" : ""}`}
                onClick={() =>
                  setFilters((prev) => ({ ...prev, ...presetRange(key) }))
                }
              >
                {label}
              </button>
            ))}
          </div>
          {hasActiveFilters && (
            <button
              type="button"
              className="dash-reset"
              onClick={resetFilters}
            >
              <RotateCcw size={14} />
              Réinitialiser
            </button>
          )}
        </div>
        <div className="dash-filter-grid">
            <label className="field">
              <span>Du</span>
              <input
                type="date"
                value={filters.date_from}
                onChange={(e) => setFilter("date_from", e.target.value)}
              />
            </label>
            <label className="field">
              <span>Au</span>
              <input
                type="date"
                value={filters.date_to}
                onChange={(e) => setFilter("date_to", e.target.value)}
              />
            </label>
            {showAgencyFilter && (
              <label className="field">
                <span>Agence</span>
                <select
                  value={filters.agency}
                  onChange={(e) => setFilter("agency", e.target.value)}
                >
                  <option value="">Toutes</option>
                  {agencies.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.code} — {a.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {showOwnerFilter && (
              <label className="field">
                <span>Propriétaire du dossier</span>
                <select
                  value={filters.owner}
                  onChange={(e) => setFilter("owner", e.target.value)}
                >
                  <option value="">Tous</option>
                  {(ownersPage?.results ?? []).map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.first_name || u.last_name
                        ? `${u.first_name} ${u.last_name}`.trim()
                        : u.username}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="field">
              <span>Statut</span>
              <select
                value={filters.status}
                onChange={(e) => setFilter("status", e.target.value)}
              >
                <option value="">Tous</option>
                {Object.entries(STATUS_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Produit</span>
              <select
                value={filters.product}
                onChange={(e) => setFilter("product", e.target.value)}
              >
                <option value="">Tous</option>
                {(productsPage?.results ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Type de client</span>
              <select
                value={filters.client_type}
                onChange={(e) => setFilter("client_type", e.target.value)}
              >
                <option value="">Tous</option>
                {Object.entries(CLIENT_TYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {scope === "OWN" && (
            <p className="dash-scope-note">
              Périmètre « mes dossiers » : les indicateurs portent sur vos
              dossiers uniquement.
            </p>
          )}
      </section>

      {isLoading || !data ? (
        <Spinner />
      ) : (
        <>
          <KpiSection title="Pipeline crédit">
            <StatCard
              icon={FileText}
              label="Dossiers"
              value={s?.total ?? 0}
              hint={`${s?.pending_count ?? 0} en instruction`}
            />
            <StatCard
              icon={Clock}
              label="En approbation"
              value={s?.in_approval_count ?? 0}
              tone="warning"
              hint={`${data.workflow?.my_pending_tasks ?? 0} pour moi`}
            />
            <StatCard
              icon={RotateCcw}
              label="Retournés"
              value={s?.returned_count ?? 0}
              tone="warning"
            />
            <StatCard
              icon={CheckCircle2}
              label="Approuvés"
              value={s?.approved_count ?? 0}
              tone="success"
              hint={formatMoney(s?.amount_approved ?? null)}
            />
            <StatCard
              icon={XCircle}
              label="Rejetés"
              value={s?.rejected_count ?? 0}
              tone="danger"
            />
            <StatCard
              icon={ClipboardCheck}
              label="Tâches en attente"
              value={data.workflow?.pending_tasks ?? 0}
              hint={`${data.workflow?.conditions_pending ?? 0} réserve(s)`}
            />
          </KpiSection>

          <KpiSection title="Production & décaissement">
            <StatCard
              icon={FileSignature}
              label="Contrats générés"
              value={
                (s?.contract_generated_count ?? 0) ||
                (data.contracts?.generated ?? 0)
              }
              hint={
                data.contracts
                  ? `${data.contracts.signed} signé(s)`
                  : undefined
              }
            />
            <StatCard
              icon={Clock}
              label="Décaissement à valider"
              value={s?.disbursement_pending_count ?? 0}
              tone="warning"
              hint={formatMoney(s?.disbursement_pending_amount ?? null)}
            />
            <StatCard
              icon={Wallet}
              label="Décaissés"
              value={s?.disbursed_count ?? 0}
              hint={formatMoney(s?.disbursed_amount ?? null)}
            />
            <StatCard
              icon={Banknote}
              label="Encours portefeuille"
              value={compactMoney(data.portfolio.outstanding)}
              hint={`${data.portfolio.active_loans} prêt(s) actif(s)`}
            />
            <StatCard
              icon={Layers}
              label="Prêts"
              value={data.portfolio.total_loans}
              hint={formatMoney(data.portfolio.disbursed_total ?? null)}
            />
            <StatCard
              icon={AlertTriangle}
              label="Échéances en retard"
              value={data.portfolio.overdue_installments}
              tone={
                data.portfolio.overdue_installments > 0 ? "danger" : "default"
              }
            />
          </KpiSection>

          <KpiSection title="Risque, recouvrement & garanties">
            <StatCard
              icon={AlertTriangle}
              label="Portefeuille à risque"
              value={parRatio !== null ? `${parRatio.toFixed(1)} %` : "—"}
              tone={parRatio !== null && parRatio > 5 ? "danger" : "warning"}
              hint={formatMoney(overdue)}
            />
            <StatCard
              icon={ClipboardCheck}
              label="Dossiers recouvrement"
              value={data.risk.open_cases ?? 0}
              hint="Hors clôturés"
            />
            <StatCard
              icon={ShieldCheck}
              label="Garanties actives"
              value={data.guarantees.active_count ?? data.guarantees.count}
              hint={compactMoney(
                data.guarantees.active_value ??
                  data.guarantees.total_current_value,
              )}
            />
            <StatCard
              icon={UsersRound}
              label="Clients"
              value={data.clients.total}
              hint={
                data.clients.new_period_label === "period"
                  ? `+${data.clients.new_this_month} sur la période`
                  : `+${data.clients.new_this_month} ce mois-ci`
              }
            />
            {data.cbs && (
              <StatCard
                icon={ServerCrash}
                label="Échecs CBS"
                value={data.cbs.failed}
                tone={data.cbs.failed > 0 ? "danger" : "default"}
                hint={`${data.cbs.pending} en attente · ${data.cbs.retry} à rejouer`}
              />
            )}
          </KpiSection>

          <div className="dash-grid">
            <div className="dash-main">
              <section className="card">
                <div className="card-title">
                  <Layers size={18} />
                  Évolution des dossiers
                </div>
                <div className="card-body">
                  <TrendChart data={data.credits.monthly} />
                </div>
              </section>

              <section className="card">
                <div className="card-title">
                  <Clock size={18} />
                  Activité récente
                  <Link to="/dossiers" className="card-title-link">
                    Voir tout <ArrowUpRight size={14} />
                  </Link>
                </div>
                <div className="card-body no-pad">
                  {data.credits.recent.length === 0 ? (
                    <div className="pad">
                      <EmptyState message="Aucun dossier récent." />
                    </div>
                  ) : (
                    <ul className="activity-list">
                      {data.credits.recent.map((r) => (
                        <li key={r.id}>
                          <Link
                            to={`/dossiers/${r.id}`}
                            className="activity-row"
                          >
                            <span className="activity-avatar">
                              {(r.client || "?").slice(0, 1).toUpperCase()}
                            </span>
                            <span className="activity-info">
                              <span className="activity-client">{r.client}</span>
                              <span className="activity-meta">
                                {r.reference || "—"} · {r.product}
                                {r.owner ? ` · ${r.owner}` : ""}
                              </span>
                            </span>
                            <span className="activity-amount">
                              {formatMoney(r.amount)}
                            </span>
                            <span
                              className={`badge badge-${
                                STATUS_TONE[r.status] ?? "muted"
                              }`}
                            >
                              {STATUS_LABELS[r.status] ?? r.status}
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </section>

              <section className="card">
                <div className="card-title">
                  <FileText size={18} />
                  Dossiers par statut
                </div>
                <div className="card-body">
                  <DistBars
                    emptyMessage="Aucun dossier."
                    rows={data.credits.by_status.map((row) => ({
                      label: STATUS_LABELS[row.status] ?? row.status,
                      count: row.count,
                      amount: row.amount,
                      tone: STATUS_TONE[row.status],
                    }))}
                  />
                </div>
              </section>
            </div>

            <aside className="dash-side">
              <section className="card">
                <div className="card-title">
                  <UsersRound size={18} />
                  Répartition clientèle
                </div>
                <div className="card-body">
                  <ClientDonut
                    rows={data.clients.by_type}
                    total={data.clients.total}
                  />
                </div>
              </section>

              <section className="card">
                <div className="card-title">
                  <AlertTriangle size={18} />
                  Portefeuille à risque
                </div>
                <div className="card-body">
                  <div className="risk-summary">
                    <div>
                      <span className="rs-label">Encours en retard</span>
                      <span className="rs-value danger">
                        {formatMoney(overdue)}
                      </span>
                    </div>
                    <div>
                      <span className="rs-label">Cas ouverts</span>
                      <span className="rs-value">
                        {data.risk.open_cases ?? 0}
                      </span>
                    </div>
                  </div>
                  <DistBars
                    emptyMessage="Aucun encours à risque."
                    rows={data.risk.by_par_class.map((r) => ({
                      label: PAR_LABELS[r.par_class] ?? r.par_class,
                      count: r.count,
                      amount: r.amount,
                      tone: r.par_class === "PAR0" ? "success" : "danger",
                    }))}
                  />
                  {(data.risk.by_stage?.length ?? 0) > 0 && (
                    <>
                      <p className="muted small" style={{ marginTop: 14 }}>
                        Par stade de recouvrement
                      </p>
                      <DistBars
                        emptyMessage=""
                        rows={(data.risk.by_stage ?? []).map((r) => ({
                          label: STAGE_LABELS[r.stage] ?? r.stage,
                          count: r.count,
                          amount: r.amount,
                          tone: "warning",
                        }))}
                      />
                    </>
                  )}
                </div>
              </section>

              <section className="card">
                <div className="card-title">
                  <Boxes size={18} />
                  Top produits
                </div>
                <div className="card-body">
                  <DistBars
                    emptyMessage="Aucun produit utilisé."
                    rows={data.credits.by_product.map((p) => ({
                      label: p.product,
                      count: p.count,
                      amount: p.amount,
                    }))}
                  />
                </div>
              </section>

              {(data.credits.by_agency?.length ?? 0) > 0 && (
                <section className="card">
                  <div className="card-title">
                    <Layers size={18} />
                    Par agence
                  </div>
                  <div className="card-body">
                    <DistBars
                      emptyMessage="Aucune agence."
                      rows={(data.credits.by_agency ?? []).map((a) => ({
                        label: a.agency,
                        count: a.count,
                        amount: a.amount,
                      }))}
                    />
                  </div>
                </section>
              )}

              <section className="card">
                <div className="card-title">
                  <ShieldCheck size={18} />
                  Garanties & contrats
                </div>
                <div className="card-body">
                  <div className="mini-kpis">
                    <div className="mini-kpi">
                      <span className="mk-value">
                        {data.guarantees.active_count ?? data.guarantees.count}
                      </span>
                      <span className="mk-label">Garanties actives</span>
                    </div>
                    <div className="mini-kpi">
                      <span className="mk-value">
                        {compactMoney(
                          data.guarantees.active_value ??
                            data.guarantees.total_current_value,
                        )}
                      </span>
                      <span className="mk-label">Valeur</span>
                    </div>
                    {data.contracts && (
                      <>
                        <div className="mini-kpi">
                          <span className="mk-value">
                            {data.contracts.generated}
                          </span>
                          <span className="mk-label">Contrats générés</span>
                        </div>
                        <div className="mini-kpi">
                          <span className="mk-value">
                            {data.contracts.signed}
                          </span>
                          <span className="mk-label">Signés</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </section>
            </aside>
          </div>
        </>
      )}
    </div>
  );
}


function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Bonjour";
  if (h < 18) return "Bon après-midi";
  return "Bonsoir";
}

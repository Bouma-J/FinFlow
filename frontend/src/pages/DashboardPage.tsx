import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  Banknote,
  Building2,
  ClipboardCheck,
  Clock,
  FilePlus2,
  FileText,
  LayoutDashboard,
  RotateCcw,
  ServerCrash,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { DashboardData } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasAnyPerm, hasPerm } from "@/auth/permissions";
import { PERM_CREDITS, PERM_TASKS } from "@/auth/routePerms";
import { PermLink } from "@/components/PermLink";
import {
  AgencyFilter,
  CREDIT_STATUS_OPTIONS,
  FilterField,
  FilterSelect,
  ListFilters,
  OfficerFilter,
  ProductFilter,
  countActive,
} from "@/components/ListFilters";
import {
  EmptyState,
  ErrorState,
  PageHeader,
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
  PROFESSIONAL: "Groupements",
  CORPORATE: "Entreprises",
};

const PAR_LABELS: Record<string, string> = {
  PAR0: "Sain (PAR 0)",
  PAR1_30: "PAR 1-30 j",
  PAR31_90: "PAR 31-90 j",
  PAR91_180: "PAR 91-180 j",
  PAR180_PLUS: "PAR > 180 j",
};

type DashFilters = {
  date_from: string;
  date_to: string;
  agency: string;
  gestionnaire: string;
  status: string;
  product: string;
  client_type: string;
};

const EMPTY_FILTERS: DashFilters = {
  date_from: "",
  date_to: "",
  agency: "",
  gestionnaire: "",
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

function isPresetActive(filters: DashFilters, key: string): boolean {
  const range = presetRange(key);
  return (
    filters.date_from === range.date_from && filters.date_to === range.date_to
  );
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Bonjour";
  if (h < 18) return "Bon après-midi";
  return "Bonsoir";
}

function TrendChart({ data }: { data: DashboardData["credits"]["monthly"] }) {
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

export function DashboardPage() {
  const { activeTenant, user } = useAuth();
  const { tenantName, tenantCode } = useTenantBranding();
  const [filters, setFilters] = useState<DashFilters>(EMPTY_FILTERS);

  const scope = user?.data_scope ?? "AGENCY";
  const isGroup = !!user?.is_group_level;
  const showOrgFilters = scope !== "OWN" || isGroup || !!user?.is_superuser;

  const queryParams = useMemo(() => {
    const p: Record<string, string> = { live: "1" };
    if (activeTenant) p.tenant = activeTenant;
    (Object.keys(filters) as (keyof DashFilters)[]).forEach((k) => {
      if (filters[k]) p[k] = filters[k];
    });
    return p;
  }, [activeTenant, filters]);

  const { data, isLoading, isFetching, isError, refetch } = useQuery({
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
  const activeFilterCount = countActive(
    filters.date_from,
    filters.date_to,
    filters.agency,
    filters.gestionnaire,
    filters.status,
    filters.product,
    filters.client_type,
  );

  const outstanding = num(data?.portfolio.outstanding);
  const overdue = num(data?.risk.total_overdue);
  const parRatio =
    outstanding + overdue > 0
      ? (overdue / (outstanding + overdue)) * 100
      : null;
  const s = data?.credits.summary;
  const scopeLabel = isGroup && !activeTenant
    ? "Vue consolidée Groupe"
    : tenantCode
      ? `${tenantCode} · ${tenantName}`
      : tenantName || "Fin Flow";

  return (
    <div className="page-shell dashboard-page">
      <PageHeader
        icon={LayoutDashboard}
        title={`${greeting()}, ${user?.first_name || user?.username || ""}`.trim()}
        subtitle={
          isGroup && !activeTenant
            ? `${scopeLabel} — synthèse multi-filiales`
            : `${scopeLabel} — pipeline, décaissements et risque de votre périmètre`
        }
        actions={
          <div className="dash-header-actions">
            {hasPerm(user, "credits.add_creditapplication") && (
              <QuickAction
                to="/dossiers/nouveau"
                icon={FilePlus2}
                label="Nouveau dossier"
              />
            )}
            {hasAnyPerm(user, PERM_TASKS) && (
              <QuickAction
                to="/taches"
                icon={ClipboardCheck}
                label="Mes validations"
              />
            )}
          </div>
        }
      />

      <div className="dash-presets" aria-label="Périodes">
        {(
          [
            ["7d", "7 jours"],
            ["30d", "30 jours"],
            ["month", "Mois en cours"],
            ["year", "Année"],
          ] as const
        ).map(([key, label]) => (
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
        {isFetching && <span className="dash-live">Mise à jour…</span>}
      </div>

      <ListFilters
        extra={
          scope === "OWN" && !isGroup ? (
            <p className="dash-scope-note">
              Périmètre « mes dossiers » : les indicateurs portent sur les
              dossiers que vous avez créés. L’agence d’un dossier est celle du
              gestionnaire au moment de la création.
            </p>
          ) : undefined
        }
        activeCount={activeFilterCount}
        onReset={resetFilters}
      >
        <FilterField label="Du" active={!!filters.date_from}>
          <input
            type="date"
            value={filters.date_from}
            onChange={(e) => setFilter("date_from", e.target.value)}
          />
        </FilterField>
        <FilterField label="Au" active={!!filters.date_to}>
          <input
            type="date"
            value={filters.date_to}
            onChange={(e) => setFilter("date_to", e.target.value)}
          />
        </FilterField>
        {showOrgFilters && (
          <AgencyFilter
            value={filters.agency}
            onChange={(v) => setFilter("agency", v)}
          />
        )}
        {showOrgFilters && (
          <OfficerFilter
            value={filters.gestionnaire}
            onChange={(v) => setFilter("gestionnaire", v)}
          />
        )}
        <FilterField label="Statut" active={!!filters.status}>
          <FilterSelect
            value={filters.status}
            onChange={(v) => setFilter("status", v)}
          >
            {CREDIT_STATUS_OPTIONS.map(([value, label]) => (
              <option key={value || "all"} value={value}>
                {label}
              </option>
            ))}
          </FilterSelect>
        </FilterField>
        <ProductFilter
          value={filters.product}
          onChange={(v) => setFilter("product", v)}
        />
        <FilterField label="Type de client" active={!!filters.client_type}>
          <FilterSelect
            value={filters.client_type}
            onChange={(v) => setFilter("client_type", v)}
          >
            <option value="">Tous les types</option>
            {Object.entries(CLIENT_TYPE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </FilterSelect>
        </FilterField>
      </ListFilters>

      {showOrgFilters && (
        <p className="dash-scope-note dash-agency-hint">
          L’agence d’un dossier est celle du gestionnaire qui le crée — pas une
          agence choisie à la main.
        </p>
      )}

      {isLoading ? (
        <Spinner />
      ) : isError || !data ? (
        <ErrorState
          message="Impossible de charger le tableau de bord."
          onRetry={() => refetch()}
        />
      ) : (
        <>
          {data.cbs && data.cbs.failed > 0 && (
            <div className="dash-cbs-banner" role="status">
              <ServerCrash size={16} />
              {data.cbs.failed} échec{data.cbs.failed > 1 ? "s" : ""} CBS
              <span className="muted">
                {data.cbs.pending} en attente · {data.cbs.retry} à rejouer
              </span>
            </div>
          )}

          <KpiSection title="À traiter">
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
              tone={(s?.returned_count ?? 0) > 0 ? "warning" : "default"}
            />
            <StatCard
              icon={ClipboardCheck}
              label="À décaisser"
              value={s?.disbursement_pending_count ?? 0}
              tone={
                (s?.disbursement_pending_count ?? 0) > 0 ? "warning" : "default"
              }
              hint={formatMoney(s?.disbursement_pending_amount ?? null)}
            />
          </KpiSection>

          <KpiSection title="Portefeuille">
            <StatCard
              icon={Wallet}
              label="Décaissés"
              value={s?.disbursed_count ?? 0}
              hint={formatMoney(s?.disbursed_amount ?? null)}
            />
            <StatCard
              icon={Banknote}
              label="Encours"
              value={compactMoney(data.portfolio.outstanding)}
              hint={`${data.portfolio.active_loans} prêt(s) actif(s)`}
            />
            <StatCard
              icon={AlertTriangle}
              label="Échéances en retard"
              value={data.portfolio.overdue_installments}
              tone={
                data.portfolio.overdue_installments > 0 ? "danger" : "default"
              }
              hint={
                parRatio !== null
                  ? `PAR ${parRatio.toFixed(1)} % · ${formatMoney(overdue)}`
                  : undefined
              }
            />
            <StatCard
              icon={ClipboardCheck}
              label="Recouvrement"
              value={data.risk.open_cases ?? 0}
              hint="Dossiers ouverts"
            />
          </KpiSection>

          <div className="dash-grid">
            <div className="dash-main">
              <section className="card">
                <div className="card-title">
                  <Clock size={18} />
                  Activité récente
                  <PermLink
                    user={user}
                    anyOf={PERM_CREDITS}
                    to="/dossiers"
                    className="card-title-link"
                    fallback={null}
                  >
                    Voir tout <ArrowUpRight size={14} />
                  </PermLink>
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
                          <PermLink
                            user={user}
                            anyOf={PERM_CREDITS}
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
                                {r.agency && r.agency !== "—"
                                  ? ` · ${r.agency}`
                                  : ""}
                                {r.owner && r.owner !== "—"
                                  ? ` · ${r.owner}`
                                  : ""}
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
                          </PermLink>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </section>

              <section className="card">
                <div className="card-title">
                  <FileText size={18} />
                  Évolution des dossiers
                </div>
                <div className="card-body">
                  <TrendChart data={data.credits.monthly} />
                </div>
              </section>
            </div>

            <aside className="dash-side">
              <section className="card">
                <div className="card-title">
                  <Building2 size={18} />
                  Par agence
                </div>
                <div className="card-body">
                  <DistBars
                    emptyMessage="Aucun dossier rattaché à une agence."
                    rows={(data.credits.by_agency ?? []).map((a) => ({
                      label: a.agency,
                      count: a.count,
                      amount: a.amount,
                    }))}
                  />
                </div>
              </section>

              <section className="card">
                <div className="card-title">
                  <FileText size={18} />
                  Par statut
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

              <section className="card">
                <div className="card-title">
                  <AlertTriangle size={18} />
                  Portefeuille à risque
                </div>
                <div className="card-body">
                  <DistBars
                    emptyMessage="Aucun encours à risque."
                    rows={data.risk.by_par_class.map((r) => ({
                      label: PAR_LABELS[r.par_class] ?? r.par_class,
                      count: r.count,
                      amount: r.amount,
                      tone: r.par_class === "PAR0" ? "success" : "danger",
                    }))}
                  />
                </div>
              </section>
            </aside>
          </div>
        </>
      )}
    </div>
  );
}

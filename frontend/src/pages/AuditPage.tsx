import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, ScrollText } from "lucide-react";
import { Fragment, useState } from "react";

import { api } from "@/api/client";
import type { AuditLog, Paginated } from "@/api/types";
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
  StatCard,
  formatDate,
} from "@/components/ui";

const PAGE_SIZE = Math.max(15, DEFAULT_PAGE_SIZE);

const ACTIONS = [
  ["", "Toutes"],
  ["CREATE", "Création"],
  ["UPDATE", "Modification"],
  ["DELETE", "Suppression"],
  ["WORKFLOW", "Circuit"],
  ["LOGIN", "Connexion"],
  ["LOGOUT", "Déconnexion"],
  ["INTEGRATION", "Core Banking"],
] as const;

const ACTION_TONE: Record<string, "success" | "warning" | "danger" | "info" | "muted"> = {
  CREATE: "success",
  UPDATE: "info",
  DELETE: "danger",
  WORKFLOW: "warning",
  LOGIN: "info",
  LOGOUT: "muted",
  INTEGRATION: "info",
};

const ENTITY_LABELS: Record<string, string> = {
  "credits.CreditApplication": "Dossier de crédit",
  "credits.Loan": "Prêt",
  "credits.FinancialAnalysis": "Analyse financière",
  "clients.Client": "Client",
  "documents.Document": "Document",
  "guarantees.Guarantee": "Garantie",
  "sureties.Surety": "Caution",
  "workflow.ApprovalTask": "Validation",
  "collections.CollectionCase": "Recouvrement",
  "corebanking.IntegrationLog": "Journal CBS",
};

const HIDDEN_FIELDS = new Set([
  "id",
  "tenant",
  "tenant_id",
  "created_by",
  "updated_by",
  "password",
]);

type Summary = { total: number; by_action: Record<string, number> };

function actionLabel(action: string) {
  return ACTIONS.find((item) => item[0] === action)?.[1] ?? action;
}

function entityLabel(label: string) {
  if (ENTITY_LABELS[label]) return ENTITY_LABELS[label];
  const tail = label.split(".").pop() || label;
  return tail.replace(/([a-z])([A-Z])/g, "$1 $2");
}

function changeEntries(changes: Record<string, unknown> | undefined) {
  return Object.entries(changes ?? {}).filter(
    ([key, value]) => !HIDDEN_FIELDS.has(key) && value !== null && value !== "",
  );
}

export function AuditPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [entity, setEntity] = useState("");
  const [userQ, setUserQ] = useState("");
  const [ip, setIp] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);

  function setFilter(setter: (value: string) => void) {
    return (value: string) => {
      setter(value);
      setPage(1);
      setOpenId(null);
    };
  }

  const filters = {
    ...(search.trim() ? { search: search.trim() } : {}),
    ...(action ? { action } : {}),
    ...(entity.trim() ? { model_label: entity.trim() } : {}),
    ...(userQ.trim() ? { user_q: userQ.trim() } : {}),
    ...(ip.trim() ? { ip: ip.trim() } : {}),
    ...(from ? { timestamp_after: from } : {}),
    ...(to ? { timestamp_before: to } : {}),
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["audit-logs", page, filters],
    queryFn: async () =>
      (
        await api.get<Paginated<AuditLog>>("/audit-logs/", {
          params: { ...filters, page, page_size: PAGE_SIZE, ordering: "-timestamp" },
        })
      ).data,
  });

  const summary = useQuery({
    queryKey: ["audit-logs-summary", filters],
    queryFn: async () =>
      (await api.get<Summary>("/audit-logs/summary/", { params: filters })).data,
  });

  const counts = summary.data?.by_action ?? {};

  return (
    <div className="page-shell page-shell--list">
      <div className="list-page-chrome">
        <PageHeader
          icon={ScrollText}
          title="Piste d'audit"
          subtitle={
            summary.data
              ? `${summary.data.total.toLocaleString("fr-FR")} opération${summary.data.total > 1 ? "s" : ""} sur le filtre`
              : "Traçabilité des opérations"
          }
        />
        <div className="stat-grid tight">
          <StatCard label="Total" value={summary.data?.total ?? "—"} />
          <StatCard label="Créations" value={counts.CREATE ?? 0} tone="success" />
          <StatCard label="Modifications" value={counts.UPDATE ?? 0} tone="default" />
          <StatCard label="Suppressions" value={counts.DELETE ?? 0} tone="danger" />
          <StatCard label="Circuit" value={counts.WORKFLOW ?? 0} tone="warning" />
        </div>
        <ListFilters
          search={
            <SearchInput
              value={search}
              onChange={setFilter(setSearch)}
              placeholder="Objet, référence, entité…"
            />
          }
          activeCount={countActive(search, action, entity, userQ, ip, from, to)}
          onReset={() => {
            setSearch("");
            setAction("");
            setEntity("");
            setUserQ("");
            setIp("");
            setFrom("");
            setTo("");
            setPage(1);
            setOpenId(null);
          }}
        >
          <FilterField label="Action" active={!!action}>
            <FilterSelect value={action} onChange={setFilter(setAction)}>
              {ACTIONS.map(([value, label]) => (
                <option key={value || "all"} value={value}>
                  {label}
                </option>
              ))}
            </FilterSelect>
          </FilterField>
          <FilterField label="Entité" active={!!entity.trim()}>
            <input
              value={entity}
              placeholder="Client, dossier, prêt…"
              onChange={(event) => setFilter(setEntity)(event.target.value)}
            />
          </FilterField>
          <FilterField label="Utilisateur" active={!!userQ.trim()}>
            <input
              value={userQ}
              placeholder="Nom ou identifiant"
              onChange={(event) => setFilter(setUserQ)(event.target.value)}
            />
          </FilterField>
          <FilterField label="Du" active={!!from}>
            <input
              type="date"
              value={from}
              onChange={(event) => setFilter(setFrom)(event.target.value)}
            />
          </FilterField>
          <FilterField label="Au" active={!!to}>
            <input
              type="date"
              value={to}
              onChange={(event) => setFilter(setTo)(event.target.value)}
            />
          </FilterField>
          <FilterField label="Adresse IP" active={!!ip.trim()}>
            <input
              value={ip}
              placeholder="127.0.0.1"
              onChange={(event) => setFilter(setIp)(event.target.value)}
            />
          </FilterField>
        </ListFilters>
      </div>
      <div className="list-table-region">
        <QueryStatus
          isLoading={isLoading}
          isError={isError}
          isEmpty={!data?.results.length}
          emptyMessage="Aucune opération ne correspond à ces critères."
          onRetry={() => refetch()}
        >
          <>
            <div className="table-scroll table-scroll--fill">
              <table className="table card">
                <thead>
                  <tr>
                    <th style={{ width: 36 }} />
                    <th>Date</th>
                    <th>Action</th>
                    <th>Entité</th>
                    <th>Objet</th>
                    <th>Utilisateur</th>
                    <th>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.results ?? []).map((log) => {
                    const open = openId === log.id;
                    const entries = changeEntries(log.changes);
                    return (
                      <Fragment key={log.id}>
                        <tr
                          className={`audit-row${open ? " is-open" : ""}`}
                          onClick={() => setOpenId(open ? null : log.id)}
                        >
                          <td>
                            {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                          </td>
                          <td>{formatDate(log.timestamp)}</td>
                          <td>
                            <Badge
                              value={log.action}
                              label={actionLabel(log.action)}
                              tone={ACTION_TONE[log.action] ?? "muted"}
                            />
                          </td>
                          <td className="muted small" title={log.model_label}>
                            {entityLabel(log.model_label)}
                          </td>
                          <td>
                            <div>{log.object_repr || "—"}</div>
                            {log.object_id ? (
                              <div className="muted small">{log.object_id}</div>
                            ) : null}
                          </td>
                          <td>{log.user_display || "—"}</td>
                          <td className="muted small">{log.ip_address || "—"}</td>
                        </tr>
                        {open ? (
                          <tr className="audit-detail">
                            <td colSpan={7}>
                              {entries.length === 0 ? (
                                <p className="muted small">Aucun détail de champ.</p>
                              ) : (
                                <dl className="audit-detail-grid">
                                  {entries.map(([key, value]) => (
                                    <span key={key} style={{ display: "contents" }}>
                                      <dt>{key}</dt>
                                      <dd>{String(value)}</dd>
                                    </span>
                                  ))}
                                </dl>
                              )}
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <PaginationBar
              page={page}
              count={data?.count ?? 0}
              pageSize={PAGE_SIZE}
              onPageChange={setPage}
            />
          </>
        </QueryStatus>
      </div>
    </div>
  );
}

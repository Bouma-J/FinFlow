import { useQuery } from "@tanstack/react-query";
import { Banknote } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  Badge,
  PageHeader,
  PaginationBar,
  QueryStatus,
  TenantScopeNotice,
  formatDate,
  formatMoney,
} from "@/components/ui";

type LoanRow = {
  id: string;
  application: string;
  application_reference: string;
  client_display: string;
  currency: string;
  principal: string;
  interest_rate: string;
  duration_months: number;
  disbursed_at: string;
  first_due_date: string;
  status: string;
  core_banking_reference: string;
  cbs_contract_number: string;
  cbs_disbursement_status: string;
};

const STATUS_LABELS: Record<string, string> = {
  ACTIVE: "En cours",
  CLOSED: "Soldé",
  DEFAULTED: "Défaut",
};

export function LoansPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");

  const list = useQuery({
    queryKey: ["loans", activeTenant, page, status, search],
    queryFn: async () =>
      (
        await api.get<Paginated<LoanRow>>("/loans/", {
          params: {
            page,
            ...(status ? { status } : {}),
            ...(search.trim() ? { search: search.trim() } : {}),
          },
        })
      ).data,
    enabled: !needsTenant,
  });

  return (
    <div className="page-shell">
      <PageHeader
        icon={Banknote}
        title="Prêts"
        subtitle="Prêts décaissés et références CBS"
      />
      {needsTenant && <TenantScopeNotice />}

      <div className="filters-bar" style={{ marginBottom: 12 }}>
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">Tous statuts</option>
          <option value="ACTIVE">En cours</option>
          <option value="CLOSED">Soldé</option>
          <option value="DEFAULTED">Défaut</option>
        </select>
        <input
          type="search"
          placeholder="Réf. dossier, client, CBS…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
      </div>

      <QueryStatus
        isLoading={list.isLoading}
        isError={list.isError}
        isEmpty={!list.data?.results.length}
        emptyMessage="Aucun prêt pour cette filiale."
        onRetry={() => list.refetch()}
      >
        <table className="table card">
          <thead>
            <tr>
              <th>Dossier</th>
              <th>Client</th>
              <th>Capital</th>
              <th>Durée</th>
              <th>Décaissé</th>
              <th>Statut</th>
              <th>CBS</th>
            </tr>
          </thead>
          <tbody>
            {(list.data?.results ?? []).map((loan) => (
              <tr key={loan.id}>
                <td>
                  <Link to={`/dossiers/${loan.application}`}>
                    {loan.application_reference || loan.application.slice(0, 8)}
                  </Link>
                </td>
                <td>{loan.client_display || "—"}</td>
                <td className="num">
                  {formatMoney(loan.principal, loan.currency)}
                </td>
                <td>{loan.duration_months} mois</td>
                <td>{formatDate(loan.disbursed_at)}</td>
                <td>
                  <Badge
                    value={loan.status}
                    label={STATUS_LABELS[loan.status] ?? loan.status}
                  />
                </td>
                <td className="muted small">
                  {loan.cbs_contract_number ||
                    loan.core_banking_reference ||
                    loan.cbs_disbursement_status ||
                    "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <PaginationBar
          page={page}
          count={list.data?.count ?? 0}
          pageSize={25}
          onPageChange={setPage}
        />
      </QueryStatus>
    </div>
  );
}

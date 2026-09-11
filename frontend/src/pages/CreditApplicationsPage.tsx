import { useQuery } from "@tanstack/react-query";
import { ArrowRight, FileText, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { CreditApplication, Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import {
  AgencyFilter,
  CREDIT_STATUS_OPTIONS,
  ClientFilterBanner,
  FilterField,
  FilterSelect,
  ListFilters,
  OfficerFilter,
  ProductFilter,
  SearchInput,
  countActive,
  useClientSearchParam,
} from "@/components/ListFilters";
import {
  Badge,
  PageHeader,
  PaginationBar,
  QueryStatus,
  TenantScopeNotice,
  formatMoney,
} from "@/components/ui";

export function CreditApplicationsPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const { clientFilter, clearClientFilter } = useClientSearchParam();
  const canCreate = hasPerm(user, "credits.add_creditapplication");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [product, setProduct] = useState("");
  const [agency, setAgency] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [gestionnaire, setGestionnaire] = useState("");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: [
      "credit-applications",
      activeTenant,
      page,
      search,
      status,
      product,
      agency,
      riskLevel,
      gestionnaire,
      clientFilter,
    ],
    queryFn: async () =>
      (
        await api.get<Paginated<CreditApplication>>("/credit-applications/", {
          params: {
            page,
            ...(search.trim() ? { search: search.trim() } : {}),
            ...(status ? { status } : {}),
            ...(product ? { product } : {}),
            ...(agency ? { agency } : {}),
            ...(riskLevel ? { risk_level: riskLevel } : {}),
            ...(gestionnaire ? { gestionnaire } : {}),
            ...(clientFilter ? { client: clientFilter } : {}),
          },
        })
      ).data,
    enabled: !needsTenant,
  });

  function setFilter<T>(setter: (v: T) => void) {
    return (value: T) => {
      setter(value);
      setPage(1);
    };
  }

  return (
    <div className="page-shell">
      <PageHeader
        icon={FileText}
        title="Dossiers de crédit"
        subtitle="Instruction, approbation et décaissement"
        actions={
          canCreate ? (
            <Link className="btn btn-primary" to="/dossiers/nouveau">
              <Plus />
              Nouveau dossier
            </Link>
          ) : undefined
        }
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
        activeCount={countActive(
          search,
          gestionnaire,
          status,
          product,
          agency,
          riskLevel,
          clientFilter,
        )}
        onReset={() => {
          setSearch("");
          setGestionnaire("");
          setStatus("");
          setProduct("");
          setAgency("");
          setRiskLevel("");
          setPage(1);
          if (clientFilter) clearClientFilter();
        }}
      >
        <OfficerFilter
          value={gestionnaire}
          onChange={setFilter(setGestionnaire)}
        />
        <FilterField label="Statut" active={!!status}>
          <FilterSelect value={status} onChange={setFilter(setStatus)}>
            {CREDIT_STATUS_OPTIONS.map(([value, label]) => (
              <option key={value || "all"} value={value}>
                {label}
              </option>
            ))}
          </FilterSelect>
        </FilterField>
        <ProductFilter value={product} onChange={setFilter(setProduct)} />
        <AgencyFilter value={agency} onChange={setFilter(setAgency)} />
        <FilterField label="Risque" active={!!riskLevel}>
          <FilterSelect value={riskLevel} onChange={setFilter(setRiskLevel)}>
            <option value="">Tous risques</option>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={String(n)}>
                Risque {n}
              </option>
            ))}
          </FilterSelect>
        </FilterField>
      </ListFilters>
      <ClientFilterBanner
        clientId={clientFilter}
        onClear={() => {
          clearClientFilter();
          setPage(1);
        }}
      />

      <QueryStatus
        isLoading={isLoading}
        isError={isError}
        isEmpty={!data?.results.length}
        emptyMessage="Aucun dossier ne correspond à ces critères."
        onRetry={() => refetch()}
      >
        <>
          <table className="table card">
            <thead>
              <tr>
                <th>Référence</th>
                <th>Client</th>
                <th>Produit</th>
                <th className="num">Montant</th>
                <th>Statut</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(data?.results ?? []).map((a) => (
                <tr key={a.id}>
                  <td>
                    <code>{a.reference || a.id.slice(0, 8)}</code>
                  </td>
                  <td>{a.client_display}</td>
                  <td>{a.product_label}</td>
                  <td className="num">
                    {formatMoney(a.amount_requested, a.currency)}
                  </td>
                  <td>
                    <Badge value={a.status} label={a.status_display} />
                  </td>
                  <td>
                    <Link className="btn btn-ghost btn-sm" to={`/dossiers/${a.id}`}>
                      Ouvrir
                      <ArrowRight />
                    </Link>
                  </td>
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

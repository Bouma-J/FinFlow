import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Plus,
  TriangleAlert,
  UserRound,
  X,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { Client, Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import { ClientCbsImportForm } from "@/components/ClientCbsImportForm";
import {
  AgencyFilter,
  FilterField,
  FilterSelect,
  ListFilters,
  SearchInput,
  countActive,
} from "@/components/ListFilters";
import {
  Badge,
  PageHeader,
  PaginationBar,
  QueryStatus,
  TenantScopeNotice,
} from "@/components/ui";

function typeLabel(t: string) {
  return t === "CORPORATE"
    ? "Personne morale"
    : t === "PROFESSIONAL"
      ? "Groupement"
      : "Personne physique";
}

export function ClientsPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const canCreateClient = hasPerm(user, "clients.add_client");
  const [showForm, setShowForm] = useState(false);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [clientType, setClientType] = useState("");
  const [kycStatus, setKycStatus] = useState("");
  const [agency, setAgency] = useState("");
  const [isActive, setIsActive] = useState("");
  const [importNotice, setImportNotice] = useState<string | null>(null);

  function setFilter<T>(setter: (v: T) => void) {
    return (value: T) => {
      setter(value);
      setPage(1);
    };
  }

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: [
      "clients",
      activeTenant,
      page,
      search,
      clientType,
      kycStatus,
      agency,
      isActive,
    ],
    queryFn: async () =>
      (
        await api.get<Paginated<Client>>("/clients/", {
          params: {
            page,
            ...(search.trim() ? { search: search.trim() } : {}),
            ...(clientType ? { client_type: clientType } : {}),
            ...(kycStatus ? { kyc_status: kycStatus } : {}),
            ...(agency ? { agency } : {}),
            ...(isActive ? { is_active: isActive } : {}),
          },
        })
      ).data,
    enabled: !needsTenant,
  });

  function closeForm() {
    setShowForm(false);
  }

  return (
    <div className="page-shell">
      <PageHeader
        icon={UserRound}
        title="Clients"
        subtitle="Personnes physiques, morales et groupements"
        actions={
          canCreateClient ? (
            <button
              className="btn btn-primary"
              onClick={() => {
                setImportNotice(null);
                setShowForm((s) => !s);
              }}
            >
              {showForm ? <X /> : <Plus />}
              {showForm ? "Fermer" : "Nouveau client"}
            </button>
          ) : undefined
        }
      />
      {needsTenant && <TenantScopeNotice />}

      {importNotice && (
        <div className="notice-warning">
          <TriangleAlert size={18} />
          <span>{importNotice}</span>
        </div>
      )}

      {showForm && needsTenant && (
        <div className="notice-warning">
          <TriangleAlert size={18} />
          <span>
            Vous êtes connecté au niveau Groupe. Sélectionnez d&apos;abord une
            filiale dans la barre supérieure pour enregistrer un client.
          </span>
        </div>
      )}

      {showForm && !needsTenant ? (
        <ClientCbsImportForm
          onSuccess={(client) => {
            closeForm();
            if ((client as Client & { kyc_alert?: boolean }).kyc_alert) {
              setImportNotice(
                `Client « ${client.display_name} » créé. Alerte KYC : le compte CBS n'était pas valide — à vérifier.`,
              );
            } else {
              setImportNotice(null);
            }
          }}
          onCancel={closeForm}
        />
      ) : (
        <>
        <ListFilters
          search={
            <SearchInput
              value={search}
              onChange={setFilter(setSearch)}
              placeholder="Nom, référence, téléphone, pièce, CBS…"
            />
          }
          activeCount={countActive(search, clientType, kycStatus, agency, isActive)}
          onReset={() => {
            setSearch("");
            setClientType("");
            setKycStatus("");
            setAgency("");
            setIsActive("");
            setPage(1);
          }}
        >
          <FilterField label="Type" active={!!clientType}>
            <FilterSelect value={clientType} onChange={setFilter(setClientType)}>
              <option value="">Tous types</option>
              <option value="INDIVIDUAL">Personne physique</option>
              <option value="PROFESSIONAL">Groupement</option>
              <option value="CORPORATE">Personne morale</option>
            </FilterSelect>
          </FilterField>
          <FilterField label="KYC" active={!!kycStatus}>
            <FilterSelect value={kycStatus} onChange={setFilter(setKycStatus)}>
              <option value="">Tous KYC</option>
              <option value="PENDING">En attente</option>
              <option value="VALIDATED">Validé</option>
              <option value="REJECTED">Rejeté</option>
              <option value="EXPIRED">Expiré</option>
            </FilterSelect>
          </FilterField>
          <AgencyFilter value={agency} onChange={setFilter(setAgency)} />
          <FilterField label="Statut" active={!!isActive}>
            <FilterSelect value={isActive} onChange={setFilter(setIsActive)}>
              <option value="">Actifs et inactifs</option>
              <option value="true">Actifs</option>
              <option value="false">Inactifs</option>
            </FilterSelect>
          </FilterField>
        </ListFilters>
        <QueryStatus
          isLoading={isLoading}
          isError={isError}
          isEmpty={!data?.results.length}
          emptyMessage="Aucun client ne correspond à ces critères."
          onRetry={() => refetch()}
        >
        <>
          <table className="table card">
            <thead>
              <tr>
                <th>Matricule</th>
                <th>Nom / Raison sociale</th>
                <th>Type</th>
                <th>Téléphone</th>
                <th>KYC</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(data?.results ?? []).map((c) => (
                <tr key={c.id}>
                  <td>
                    <code>{c.reference || "—"}</code>
                  </td>
                  <td>{c.display_name}</td>
                  <td>
                    <Badge value={c.client_type} label={typeLabel(c.client_type)} />
                  </td>
                  <td>{c.phone || "—"}</td>
                  <td>
                    <Badge value={c.kyc_status} />
                  </td>
                  <td>
                    <Link className="btn btn-ghost btn-sm" to={`/clients/${c.id}`}>
                      Ouvrir <ArrowRight size={14} />
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
        </>
      )}
    </div>
  );
}

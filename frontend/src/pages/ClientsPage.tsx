import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Database,
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
import { ClientForm } from "@/components/ClientForm";
import {
  Badge,
  EmptyState,
  PageHeader,
  PaginationBar,
  Spinner,
} from "@/components/ui";

function typeLabel(t: string) {
  return t === "CORPORATE"
    ? "Personne morale"
    : t === "PROFESSIONAL"
      ? "Groupement"
      : "Personne physique";
}

type CreateMode = "manual" | "cbs";

export function ClientsPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const canCreateClient = hasPerm(user, "clients.add_client");
  const [showForm, setShowForm] = useState(false);
  const [createMode, setCreateMode] = useState<CreateMode>("manual");
  const [page, setPage] = useState(1);
  const [importNotice, setImportNotice] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["clients", page],
    queryFn: async () =>
      (await api.get<Paginated<Client>>("/clients/", { params: { page } })).data,
  });

  function closeForm() {
    setShowForm(false);
    setCreateMode("manual");
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

      {showForm && !needsTenant && (
        <div className="type-toggle" style={{ marginBottom: "1rem" }}>
          <button
            type="button"
            className={`type-choice${createMode === "manual" ? " active" : ""}`}
            onClick={() => setCreateMode("manual")}
          >
            <UserRound size={18} />
            Saisie manuelle
          </button>
          <button
            type="button"
            className={`type-choice${createMode === "cbs" ? " active" : ""}`}
            onClick={() => setCreateMode("cbs")}
          >
            <Database size={18} />
            Import CBS
          </button>
        </div>
      )}

      {showForm ? (
        createMode === "cbs" ? (
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
          <ClientForm onSuccess={closeForm} onCancel={closeForm} />
        )
      ) : isLoading || !data ? (
        <Spinner />
      ) : data.results.length === 0 ? (
        <EmptyState message="Aucun client enregistré." />
      ) : (
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
              {data.results.map((c) => (
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
            count={data.count}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Plus, TriangleAlert, UserRound, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { Client, Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
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
    ? "Entreprise"
    : t === "PROFESSIONAL"
      ? "Professionnel"
      : "Particulier";
}

export function ClientsPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const canCreateClient = hasPerm(user, "clients.add_client");
  const [showForm, setShowForm] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["clients", page],
    queryFn: async () =>
      (await api.get<Paginated<Client>>("/clients/", { params: { page } })).data,
  });

  return (
    <div>
      <PageHeader
        icon={UserRound}
        title="Clients"
        subtitle="Particuliers, professionnels et entreprises"
        actions={
          canCreateClient ? (
            <button
              className="btn btn-primary"
              onClick={() => setShowForm((s) => !s)}
            >
              {showForm ? <X /> : <Plus />}
              {showForm ? "Fermer" : "Nouveau client"}
            </button>
          ) : undefined
        }
      />

      {showForm && needsTenant && (
        <div className="notice-warning">
          <TriangleAlert size={18} />
          <span>
            Vous êtes connecté au niveau Groupe. Sélectionnez d'abord une
            filiale dans la barre supérieure pour enregistrer un client.
          </span>
        </div>
      )}

      {showForm ? (
        <ClientForm
          onSuccess={() => setShowForm(false)}
          onCancel={() => setShowForm(false)}
        />
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
                      Ouvrir
                      <ArrowRight />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <PaginationBar page={page} count={data.count} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}

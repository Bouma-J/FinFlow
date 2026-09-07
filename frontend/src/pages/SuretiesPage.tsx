import { useQuery } from "@tanstack/react-query";
import { ArrowRight, HandCoins, Plus, TriangleAlert, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { Paginated, Surety } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import { SuretyForm } from "@/components/SuretyForm";
import {
  Badge,
  PageHeader,
  PaginationBar,
  QueryStatus,
} from "@/components/ui";

export function SuretiesPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const canCreate = hasPerm(user, "sureties.add_surety");
  const [showForm, setShowForm] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["sureties", page],
    queryFn: async () =>
      (await api.get<Paginated<Surety>>("/sureties/", { params: { page } })).data,
  });

  return (
    <div className="page-shell">
      <PageHeader
        icon={HandCoins}
        title="Cautions"
        subtitle="Personnes s'engageant en garantie d'un emprunteur"
        actions={
          canCreate ? (
            <button
              className="btn btn-primary"
              onClick={() => setShowForm((s) => !s)}
            >
              {showForm ? <X /> : <Plus />}
              {showForm ? "Fermer" : "Nouvelle caution"}
            </button>
          ) : undefined
        }
      />

      {showForm && needsTenant && (
        <div className="notice-warning">
          <TriangleAlert size={18} />
          <span>
            Vous êtes connecté au niveau Groupe. Sélectionnez d'abord une
            filiale dans la barre supérieure pour enregistrer une caution.
          </span>
        </div>
      )}

      {showForm ? (
        <SuretyForm
          onSuccess={() => setShowForm(false)}
          onCancel={() => setShowForm(false)}
        />
      ) : (
        <QueryStatus
          isLoading={isLoading}
          isError={isError}
          isEmpty={!data?.results.length}
          emptyMessage="Aucune caution enregistrée."
          onRetry={() => refetch()}
        >
          <>
            <table className="table card">
              <thead>
                <tr>
                  <th>Nom & prénom</th>
                  <th>Activité</th>
                  <th>Téléphone</th>
                  <th>Statut</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {(data?.results ?? []).map((s) => (
                  <tr key={s.id}>
                    <td>{s.display_name}</td>
                    <td>{s.activity || "—"}</td>
                    <td>{s.phone || "—"}</td>
                    <td>
                      <Badge
                        value={s.is_active ? "ACTIVE" : "DRAFT"}
                        label={s.is_active ? "Active" : "Inactive"}
                      />
                    </td>
                    <td>
                      <Link className="btn btn-ghost btn-sm" to={`/cautions/${s.id}`}>
                        Ouvrir
                        <ArrowRight />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <PaginationBar page={page} count={data?.count ?? 0} onPageChange={setPage} />
          </>
        </QueryStatus>
      )}
    </div>
  );
}

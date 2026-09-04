import { useQuery } from "@tanstack/react-query";
import { ArrowRight, FileText, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { CreditApplication, Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import {
  Badge,
  EmptyState,
  PageHeader,
  PaginationBar,
  Spinner,
  formatMoney,
} from "@/components/ui";

export function CreditApplicationsPage() {
  const { user } = useAuth();
  const canCreate = hasPerm(user, "credits.add_creditapplication");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["credit-applications", page],
    queryFn: async () =>
      (
        await api.get<Paginated<CreditApplication>>("/credit-applications/", {
          params: { page },
        })
      ).data,
  });

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

      {isLoading || !data ? (
        <Spinner />
      ) : data.results.length === 0 ? (
        <EmptyState message="Aucun dossier de crédit." />
      ) : (
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
              {data.results.map((a) => (
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
          <PaginationBar page={page} count={data.count} onPageChange={setPage} />
        </>
      )}
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import type { Guarantee, Paginated } from "@/api/types";
import {
  Badge,
  EmptyState,
  PageHeader,
  PaginationBar,
  Spinner,
  formatMoney,
} from "@/components/ui";

export function GuaranteesPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["guarantees", page],
    queryFn: async () =>
      (await api.get<Paginated<Guarantee>>("/guarantees/", { params: { page } }))
        .data,
  });

  return (
    <div className="page-shell">
      <PageHeader
        icon={ShieldCheck}
        title="Garanties"
        subtitle="Sûretés adossées aux crédits"
      />
      {isLoading || !data ? (
        <Spinner />
      ) : data.results.length === 0 ? (
        <EmptyState message="Aucune garantie enregistrée." />
      ) : (
        <>
          <table className="table card">
            <thead>
              <tr>
                <th>Référence</th>
                <th>Type</th>
                <th className="num">Valeur actualisée</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((g) => (
                <tr
                  key={g.id}
                  className="row-clickable"
                  onClick={() => navigate(`/garanties/${g.id}`)}
                >
                  <td>{g.reference || g.id.slice(0, 8)}</td>
                  <td>{g.type_display}</td>
                  <td className="num">{formatMoney(g.current_value)}</td>
                  <td>
                    <Badge value={g.status} />
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

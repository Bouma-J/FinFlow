import { useQuery } from "@tanstack/react-query";
import { CircleDollarSign } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import type { CollectionCase, Paginated, ParClass } from "@/api/types";
import {
  Badge,
  EmptyState,
  PageHeader,
  PaginationBar,
  Spinner,
  formatMoney,
} from "@/components/ui";

const PAR_OPTIONS: { value: "" | ParClass; label: string }[] = [
  { value: "", label: "Toutes classes PAR" },
  { value: "PAR0", label: "Sain" },
  { value: "PAR1_30", label: "PAR 1-30" },
  { value: "PAR31_90", label: "PAR 31-90" },
  { value: "PAR91_180", label: "PAR 91-180" },
  { value: "PAR180_PLUS", label: "PAR > 180" },
];

const STAGE_OPTIONS = [
  { value: "", label: "Tous stades" },
  { value: "AMICABLE", label: "Amiable" },
  { value: "PRECONTENTIOUS", label: "Précontentieux" },
  { value: "LITIGATION", label: "Contentieux" },
  { value: "CLOSED", label: "Clôturé" },
];

export function CollectionsPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [parClass, setParClass] = useState("");
  const [stage, setStage] = useState("");
  const [openOnly, setOpenOnly] = useState(true);
  const [mine, setMine] = useState(false);
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["collection-cases", page, parClass, stage, openOnly, mine, search],
    queryFn: async () =>
      (
        await api.get<Paginated<CollectionCase>>("/collection-cases/", {
          params: {
            page,
            ...(parClass ? { par_class: parClass } : {}),
            ...(stage ? { stage } : {}),
            ...(openOnly ? { open: 1 } : {}),
            ...(mine ? { mine: 1 } : {}),
            ...(search.trim() ? { search: search.trim() } : {}),
            ordering: "-days_overdue",
          },
        })
      ).data,
  });

  return (
    <div>
      <PageHeader
        icon={CircleDollarSign}
        title="Recouvrement"
        subtitle="Dossiers en retard, encaissements et suivi terrain"
      />

      <div className="filters-bar card">
        <input
          type="search"
          placeholder="Référence, client, CBS…"
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
        />
        <select
          value={parClass}
          onChange={(e) => {
            setPage(1);
            setParClass(e.target.value);
          }}
        >
          {PAR_OPTIONS.map((o) => (
            <option key={o.value || "all"} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <select
          value={stage}
          onChange={(e) => {
            setPage(1);
            setStage(e.target.value);
          }}
        >
          {STAGE_OPTIONS.map((o) => (
            <option key={o.value || "all-stage"} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={openOnly}
            onChange={(e) => {
              setPage(1);
              setOpenOnly(e.target.checked);
            }}
          />
          <span>Ouverts seulement</span>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={mine}
            onChange={(e) => {
              setPage(1);
              setMine(e.target.checked);
            }}
          />
          <span>Mon portefeuille</span>
        </label>
      </div>

      {isLoading || !data ? (
        <Spinner />
      ) : data.results.length === 0 ? (
        <EmptyState message="Aucun dossier de recouvrement." />
      ) : (
        <>
          <table className="table card">
            <thead>
              <tr>
                <th>Dossier</th>
                <th>Client</th>
                <th>Agence</th>
                <th>PAR</th>
                <th>Stade</th>
                <th className="num">Jours</th>
                <th className="num">Impayé</th>
                <th>Agent</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((c) => (
                <tr
                  key={c.id}
                  className="row-clickable"
                  onClick={() => navigate(`/recouvrement/${c.id}`)}
                >
                  <td>{c.application_reference || c.loan.slice(0, 8)}</td>
                  <td>{c.client_name}</td>
                  <td className="small">{c.agency_name}</td>
                  <td>
                    <Badge value={c.par_class_display} />
                  </td>
                  <td>
                    <Badge value={c.stage_display} />
                  </td>
                  <td className="num">{c.days_overdue}</td>
                  <td className="num">{formatMoney(c.overdue_amount)}</td>
                  <td className="small">{c.assigned_to_name || "—"}</td>
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

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Scale } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { LegalParty, LegalPartyType, Paginated } from "@/api/types";
import {
  Badge,
  EmptyState,
  PageHeader,
  Spinner,
} from "@/components/ui";

const TYPES: { value: LegalPartyType; label: string }[] = [
  { value: "LAW_FIRM", label: "Cabinet d'avocats" },
  { value: "LAWYER", label: "Avocat" },
  { value: "BAILIFF", label: "Huissier" },
  { value: "NOTARY", label: "Notaire" },
  { value: "EXPERT", label: "Expert" },
  { value: "OTHER", label: "Autre" },
];

export function LegalPartiesPage() {
  const qc = useQueryClient();
  const [typeFilter, setTypeFilter] = useState("");
  const [name, setName] = useState("");
  const [partyType, setPartyType] = useState<LegalPartyType>("LAW_FIRM");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [contact, setContact] = useState("");
  const [reg, setReg] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["legal-parties", typeFilter],
    queryFn: async () =>
      (
        await api.get<Paginated<LegalParty>>("/legal-parties/", {
          params: {
            ...(typeFilter ? { party_type: typeFilter } : {}),
            is_active: true,
            ordering: "name",
          },
        })
      ).data,
  });

  const create = useMutation({
    mutationFn: async () =>
      (
        await api.post<LegalParty>("/legal-parties/", {
          party_type: partyType,
          name,
          phone,
          email,
          contact_name: contact,
          registration_no: reg,
          is_active: true,
        })
      ).data,
    onSuccess: () => {
      setName("");
      setPhone("");
      setEmail("");
      setContact("");
      setReg("");
      setError(null);
      qc.invalidateQueries({ queryKey: ["legal-parties"] });
    },
    onError: () => setError("Impossible d'enregistrer l'intervenant."),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Le nom est obligatoire.");
      return;
    }
    create.mutate();
  }

  return (
    <div>
      <PageHeader
        icon={Scale}
        title="Intervenants juridiques"
        subtitle="Cabinets, avocats, huissiers et autres conseils"
      />

      <div className="card" style={{ padding: 14, marginBottom: 16 }}>
        <form onSubmit={submit}>
          <div className="form-grid">
            <label className="field">
              <span>Type</span>
              <select
                value={partyType}
                onChange={(e) => setPartyType(e.target.value as LegalPartyType)}
              >
                {TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Nom / raison sociale *</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label className="field">
              <span>Contact</span>
              <input
                value={contact}
                onChange={(e) => setContact(e.target.value)}
              />
            </label>
            <label className="field">
              <span>N° barreau / agrément</span>
              <input value={reg} onChange={(e) => setReg(e.target.value)} />
            </label>
            <label className="field">
              <span>Téléphone</span>
              <input value={phone} onChange={(e) => setPhone(e.target.value)} />
            </label>
            <label className="field">
              <span>E-mail</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
          </div>
          {error && <div className="form-error">{error}</div>}
          <button className="btn btn-primary btn-sm" disabled={create.isPending}>
            Ajouter
          </button>
        </form>
      </div>

      <div className="filters-bar card">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="">Tous les types</option>
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {isLoading || !data ? (
        <Spinner />
      ) : data.results.length === 0 ? (
        <EmptyState message="Aucun intervenant." />
      ) : (
        <table className="table card">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Type</th>
              <th>Contact</th>
              <th>Téléphone</th>
              <th>E-mail</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((p) => (
              <tr key={p.id}>
                <td>
                  <strong>{p.name}</strong>
                  {p.registration_no && (
                    <div className="muted small">{p.registration_no}</div>
                  )}
                </td>
                <td>
                  <Badge value={p.party_type_display} />
                </td>
                <td>{p.contact_name || "—"}</td>
                <td>{p.phone || "—"}</td>
                <td>{p.email || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

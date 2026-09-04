import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, Search, TriangleAlert, Users } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { Client } from "@/api/types";
import { Card } from "@/components/ui";

type ClientType = "INDIVIDUAL" | "PROFESSIONAL" | "CORPORATE";

export type CbsPreview = {
  full_name: string;
  code_adherent: string;
  num_manuel: string;
  num_piece_identite: string;
  identification_nationale: string;
  phone: string;
  email: string;
  boite_postale: string;
  city: string;
  address: string;
  date_inscription: string;
  limit_credit: string | null;
  est_valide: boolean;
  id_point_service: string;
  nom_point_service: string;
  kyc_alert: boolean;
  message?: string;
};

const TYPE_OPTIONS: { value: ClientType; label: string }[] = [
  { value: "INDIVIDUAL", label: "Personne physique" },
  { value: "CORPORATE", label: "Personne morale" },
  { value: "PROFESSIONAL", label: "Groupement" },
];

function apiError(err: unknown): string {
  const data = (err as { response?: { data?: Record<string, unknown> } })
    ?.response?.data;
  if (!data) return "Échec de l'appel CBS.";
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(String).join(" ");
  for (const v of Object.values(data)) {
    if (typeof v === "string") return v;
    if (Array.isArray(v)) return v.map(String).join(" ");
  }
  return "Échec de l'appel CBS.";
}

export function ClientCbsImportForm({
  onSuccess,
  onCancel,
}: {
  onSuccess: (client: Client) => void;
  onCancel: () => void;
}) {
  const qc = useQueryClient();
  const [codeAdherent, setCodeAdherent] = useState("");
  const [numManuel, setNumManuel] = useState("");
  const [numPiece, setNumPiece] = useState("");
  const [preview, setPreview] = useState<CbsPreview | null>(null);
  const [clientType, setClientType] = useState<ClientType | "">("");
  const [error, setError] = useState<string | null>(null);

  const lookup = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<CbsPreview>("/clients/cbs-preview/", {
        code_adherent: codeAdherent.trim(),
        num_manuel: numManuel.trim(),
        num_piece_identite: numPiece.trim(),
      });
      return data;
    },
    onSuccess: (data) => {
      setPreview(data);
      setError(null);
      setClientType("");
    },
    onError: (err) => {
      setPreview(null);
      setError(apiError(err));
    },
  });

  const save = useMutation({
    mutationFn: async () => {
      if (!clientType) throw new Error("Type requis");
      const { data } = await api.post<Client & { kyc_alert?: boolean }>(
        "/clients/cbs-import/",
        {
          client_type: clientType,
          code_adherent: codeAdherent.trim() || preview?.code_adherent,
          num_manuel: numManuel.trim() || preview?.num_manuel,
          num_piece_identite: numPiece.trim() || preview?.num_piece_identite,
        },
      );
      return data;
    },
    onSuccess: (client) => {
      qc.invalidateQueries({ queryKey: ["clients"] });
      onSuccess(client);
    },
    onError: (err) => setError(apiError(err)),
  });

  function onLookup(e: FormEvent) {
    e.preventDefault();
    if (!codeAdherent.trim() && !numManuel.trim() && !numPiece.trim()) {
      setError(
        "Indiquez au moins un identifiant : code adhérent, n° manuel ou n° de pièce.",
      );
      return;
    }
    lookup.mutate();
  }

  return (
    <Card
      title={
        <>
          <Search size={17} /> Importer depuis le Core Banking
        </>
      }
    >
      <p className="muted" style={{ marginTop: 0 }}>
        Recherchez l&apos;adhérent au CBS, vérifiez les données, choisissez le
        type de client, puis enregistrez. Les informations issues du CBS ne
        sont pas modifiables ici.
      </p>

      <form className="form-grid" onSubmit={onLookup}>
        <label className="field">
          <span>Code adhérent</span>
          <input
            value={codeAdherent}
            onChange={(e) => setCodeAdherent(e.target.value)}
            placeholder="A0012345"
            disabled={Boolean(preview)}
          />
        </label>
        <label className="field">
          <span>N° dossier manuel</span>
          <input
            value={numManuel}
            onChange={(e) => setNumManuel(e.target.value)}
            placeholder="M00987"
            disabled={Boolean(preview)}
          />
        </label>
        <label className="field">
          <span>N° pièce d&apos;identité</span>
          <input
            value={numPiece}
            onChange={(e) => setNumPiece(e.target.value)}
            disabled={Boolean(preview)}
          />
        </label>
        {!preview && (
          <div className="credit-form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={lookup.isPending}
            >
              <Search size={16} />
              {lookup.isPending ? "Recherche…" : "Rechercher au CBS"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={onCancel}>
              Annuler
            </button>
          </div>
        )}
      </form>

      {error && (
        <div className="notice-warning">
          <TriangleAlert size={18} />
          <span>{error}</span>
        </div>
      )}

      {preview && (
        <>
          {preview.kyc_alert && (
            <div className="notice-warning">
              <TriangleAlert size={18} />
              <span>
                Compte CBS signalé comme non valide. L&apos;enregistrement reste
                possible : le KYC sera placé en alerte (à vérifier).
              </span>
            </div>
          )}

          <h4 className="form-section-title">
            <Users size={16} /> Prévisualisation (lecture seule)
          </h4>
          <div className="form-grid">
            {(
              [
                ["Nom complet", preview.full_name],
                ["Code adhérent", preview.code_adherent],
                ["N° manuel", preview.num_manuel],
                ["Pièce d'identité", preview.num_piece_identite],
                ["Identification nationale", preview.identification_nationale],
                ["Téléphone", preview.phone],
                ["E-mail", preview.email],
                ["Ville", preview.city],
                ["Adresse", preview.address],
                ["Boîte postale", preview.boite_postale],
                ["Date d'inscription", preview.date_inscription],
                ["Limite de crédit", preview.limit_credit],
                ["Compte valide", preview.est_valide ? "Oui" : "Non"],
                [
                  "Point de service",
                  preview.nom_point_service
                    ? `${preview.nom_point_service}${
                        preview.id_point_service
                          ? ` (${preview.id_point_service})`
                          : ""
                      }`
                    : "",
                ],
              ] as const
            ).map(([label, value]) => (
              <label className="field" key={label}>
                <span>{label}</span>
                <input value={value || "—"} readOnly disabled />
              </label>
            ))}
          </div>

          <label className="field" style={{ marginTop: "1rem" }}>
            <span>
              <Building2 size={14} /> Type de client (obligatoire)
            </span>
            <select
              value={clientType}
              onChange={(e) =>
                setClientType(e.target.value as ClientType | "")
              }
              required
            >
              <option value="">— Choisir —</option>
              {TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>

          <div className="credit-form-actions">
            <button
              type="button"
              className="btn btn-primary"
              disabled={!clientType || save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Enregistrement…" : "Enregistrer le client"}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setPreview(null);
                setClientType("");
                setError(null);
              }}
            >
              Nouvelle recherche
            </button>
            <button type="button" className="btn btn-ghost" onClick={onCancel}>
              Annuler
            </button>
          </div>
        </>
      )}
    </Card>
  );
}

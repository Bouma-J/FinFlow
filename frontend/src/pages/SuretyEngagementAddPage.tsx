import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, HandCoins, Plus, Search, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type { CreditApplication } from "@/api/types";
import { SuretyAutocomplete } from "@/components/SuretyAutocomplete";
import { SuretyForm } from "@/components/SuretyForm";
import { Card, PageHeader, Spinner } from "@/components/ui";

export function SuretyEngagementAddPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [surety, setSurety] = useState("");
  const [suretyLabel, setSuretyLabel] = useState("");
  const [creating, setCreating] = useState(false);
  const [amount, setAmount] = useState("");
  const [signedDate, setSignedDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: app, isLoading } = useQuery({
    queryKey: ["credit-application", id],
    queryFn: async () =>
      (await api.get<CreditApplication>(`/credit-applications/${id}/`)).data,
    enabled: !!id,
  });

  const mutation = useMutation({
    mutationFn: async () =>
      (
        await api.post("/surety-engagements/", {
          surety,
          application: id,
          amount,
          signed_date: signedDate || null,
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["surety-engagements", id] });
      navigate(`/dossiers/${id}`);
    },
    onError: (e: unknown) => {
      const data = (e as { response?: { data?: unknown } })?.response?.data;
      setError(
        typeof data === "string"
          ? data
          : "Enregistrement impossible. Vérifiez les champs.",
      );
    },
  });

  if (isLoading || !app) return <Spinner />;

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!surety) {
      setError("Veuillez sélectionner ou créer une caution.");
      return;
    }
    if (!amount) {
      setError("Veuillez renseigner le montant engagé.");
      return;
    }
    mutation.mutate();
  }

  return (
    <div>
      <PageHeader
        icon={HandCoins}
        title="Ajouter une caution"
        subtitle={`Dossier ${app.reference} — ${app.client_display}`}
        actions={
          <Link className="btn btn-ghost" to={`/dossiers/${id}`}>
            <ArrowLeft />
            Retour au dossier
          </Link>
        }
      />

      {creating ? (
        <>
          <div className="notice-info">
            <Plus size={16} />
            <span>
              Renseignez la nouvelle caution. Elle sera automatiquement
              sélectionnée pour l'engagement.
            </span>
          </div>
          <SuretyForm
            onSuccess={(s) => {
              setSurety(s.id);
              setSuretyLabel(s.display_name);
              setCreating(false);
            }}
            onCancel={() => setCreating(false)}
          />
        </>
      ) : (
        <form className="stack" onSubmit={submit}>
          <Card
            title={
              <>
                <HandCoins size={17} /> Caution
              </>
            }
          >
            {surety ? (
              <div className="picked-row">
                <span className="picked-chip">
                  <Check size={15} />
                  {suretyLabel || "Caution sélectionnée"}
                </span>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    setSurety("");
                    setSuretyLabel("");
                  }}
                >
                  <X size={14} />
                  Changer
                </button>
              </div>
            ) : (
              <>
                <label className="field">
                  <span>
                    <Search size={13} style={{ verticalAlign: "-2px", marginRight: 4 }} />
                    Caution existante
                  </span>
                  <SuretyAutocomplete
                    value={surety}
                    onChange={(sid, label) => {
                      setSurety(sid);
                      setSuretyLabel(label);
                    }}
                  />
                </label>
                <div className="or-divider">
                  <span>ou</span>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setCreating(true)}
                >
                  <Plus size={15} />
                  Créer une nouvelle caution
                </button>
              </>
            )}
          </Card>

          {surety && (
            <Card
              title={
                <>
                  <HandCoins size={17} /> Engagement
                </>
              }
            >
              <div className="form-grid two-col">
                <label className="field">
                  <span>
                    Montant engagé (XOF) <em className="req"> *</em>
                  </span>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                  />
                </label>
                <label className="field">
                  <span>Date de signature</span>
                  <input
                    type="date"
                    value={signedDate}
                    onChange={(e) => setSignedDate(e.target.value)}
                  />
                </label>
              </div>
            </Card>
          )}

          {error && <div className="form-error">{error}</div>}
          <div className="page-actions">
            <Link className="btn btn-ghost" to={`/dossiers/${id}`}>
              Annuler
            </Link>
            <button
              className="btn btn-primary"
              disabled={mutation.isPending || !surety}
            >
              {mutation.isPending ? "Enregistrement…" : "Rattacher la caution"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

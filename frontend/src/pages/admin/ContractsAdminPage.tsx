import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  FileSignature,
  Plus,
  Power,
  Trash2,
  X,
} from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type {
  ContractExtraField,
  ContractTemplate,
  CreditProduct,
  Paginated,
  VariableCatalog,
} from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  Badge,
  Card,
  EmptyState,
  PageHeader,
  Spinner,
  TenantScopeNotice,
} from "@/components/ui";

const CATEGORIES: [string, string][] = [
  ["NOTIFICATION", "Notification de crédit"],
  ["LOAN", "Contrat de prêt"],
  ["SURETY", "Cautionnement"],
  ["PLEDGE_VEHICLE", "Gage véhicule"],
  ["PLEDGE_JEWELRY", "Gage bijoux"],
  ["PLEDGE_SHARES", "Nantissement d'actions"],
  ["SALARY_ASSIGNMENT", "Cession sur salaire"],
  ["PROMISSORY_NOTE", "Billet à ordre"],
  ["FIDUCIARY_TRANSFER", "Transfert fiduciaire"],
  ["OTHER", "Autre"],
];

const APPLIES_TO: [string, string][] = [
  ["ANY", "Tous les clients"],
  ["INDIVIDUAL", "Particuliers uniquement"],
  ["CORPORATE", "Entreprises uniquement"],
];

const emptyForm = {
  name: "",
  category: "OTHER",
  applies_to: "ANY",
  product: "",
  amount_min: "",
  amount_max: "",
  is_required: false,
  description: "",
};

export function AdminContractsPage() {
  const { user, activeTenant } = useAuth();
  const qc = useQueryClient();
  const needsTenant = user?.is_group_level && !activeTenant;

  const [form, setForm] = useState({ ...emptyForm });
  const [file, setFile] = useState<File | null>(null);
  const [extras, setExtras] = useState<ContractExtraField[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showVars, setShowVars] = useState(false);

  const templates = useQuery({
    queryKey: ["contract-templates", activeTenant],
    queryFn: async () =>
      (await api.get<Paginated<ContractTemplate>>("/contract-templates/")).data,
    enabled: !needsTenant,
  });

  const products = useQuery({
    queryKey: ["credit-products", activeTenant],
    queryFn: async () =>
      (await api.get<Paginated<CreditProduct>>("/credit-products/")).data,
    enabled: !needsTenant,
  });

  const variables = useQuery({
    queryKey: ["contract-variables"],
    queryFn: async () =>
      (await api.get<VariableCatalog>("/contract-templates/variables/")).data,
    enabled: !needsTenant,
  });

  const create = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      fd.append("name", form.name);
      fd.append("category", form.category);
      fd.append("applies_to", form.applies_to);
      if (form.product) fd.append("product", form.product);
      if (form.amount_min) fd.append("amount_min", form.amount_min);
      if (form.amount_max) fd.append("amount_max", form.amount_max);
      fd.append("is_required", String(form.is_required));
      fd.append("description", form.description);
      fd.append("extra_fields", JSON.stringify(extras));
      if (file) fd.append("file", file);
      return (
        await api.post("/contract-templates/", fd, {
          headers: { "Content-Type": "multipart/form-data" },
        })
      ).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contract-templates"] });
      setForm({ ...emptyForm });
      setFile(null);
      setExtras([]);
      setError(null);
    },
    onError: (e) => {
      const data = (e as { response?: { data?: unknown } })?.response?.data;
      setError(
        typeof data === "object"
          ? JSON.stringify(data)
          : "Création impossible. Vérifiez les champs et le fichier (.docx/.xlsx).",
      );
    },
  });

  const toggleActive = useMutation({
    mutationFn: async (t: ContractTemplate) =>
      (
        await api.patch(`/contract-templates/${t.id}/`, {
          is_active: !t.is_active,
        })
      ).data,
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["contract-templates"] }),
  });

  const remove = useMutation({
    mutationFn: async (id: string) =>
      api.delete(`/contract-templates/${id}/`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["contract-templates"] }),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Veuillez joindre le modèle (.docx ou .xlsx).");
      return;
    }
    if (!form.name.trim()) {
      setError("L'intitulé du contrat est obligatoire.");
      return;
    }
    create.mutate();
  }

  if (needsTenant) {
    return (
    <div className="page-shell">
        <PageHeader
          icon={FileSignature}
          title="Modèles de contrats"
          subtitle="Catalogue par filiale"
        />
        <TenantScopeNotice />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        icon={FileSignature}
        title="Modèles de contrats"
        subtitle="Chaque filiale gère librement ses contrats et leurs variables."
      />

      <div className="detail-grid">
        <Card title="Nouveau modèle">
          <form className="stack" onSubmit={submit}>
            <label className="field">
              <span>
                Intitulé du contrat <em className="req"> *</em>
              </span>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Ex. Contrat de cautionnement solidaire"
                required
              />
            </label>
            <div className="form-grid">
              <label className="field">
                <span>Catégorie</span>
                <select
                  value={form.category}
                  onChange={(e) =>
                    setForm({ ...form, category: e.target.value })
                  }
                >
                  {CATEGORIES.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>S'applique à</span>
                <select
                  value={form.applies_to}
                  onChange={(e) =>
                    setForm({ ...form, applies_to: e.target.value })
                  }
                >
                  {APPLIES_TO.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Produit (optionnel)</span>
                <select
                  value={form.product}
                  onChange={(e) =>
                    setForm({ ...form, product: e.target.value })
                  }
                >
                  <option value="">— tous les produits —</option>
                  {products.data?.results.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Montant min (optionnel)</span>
                <input
                  type="number"
                  value={form.amount_min}
                  onChange={(e) =>
                    setForm({ ...form, amount_min: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Montant max (optionnel)</span>
                <input
                  type="number"
                  value={form.amount_max}
                  onChange={(e) =>
                    setForm({ ...form, amount_max: e.target.value })
                  }
                />
              </label>
            </div>

            <label className="field">
              <span>
                Fichier modèle (.docx / .xlsx) <em className="req"> *</em>
              </span>
              <input
                type="file"
                accept=".docx,.xlsx"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <small className="muted">
                Remplacez les zones à remplir par des balises, ex.{" "}
                <code>{"{{ client_nom }}"}</code>. Voir le catalogue des
                variables ci-contre.
              </small>
            </label>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={form.is_required}
                onChange={(e) =>
                  setForm({ ...form, is_required: e.target.checked })
                }
              />
              <span>Obligatoire avant décaissement</span>
            </label>

            <div className="field">
              <span>Variables saisies manuellement (optionnel)</span>
              {extras.map((f, idx) => (
                <div key={idx} className="extra-field-row">
                  <input
                    placeholder="clé (ex. temoin_nom)"
                    value={f.key}
                    onChange={(e) =>
                      setExtras((arr) =>
                        arr.map((x, i) =>
                          i === idx ? { ...x, key: e.target.value } : x,
                        ),
                      )
                    }
                  />
                  <input
                    placeholder="libellé"
                    value={f.label}
                    onChange={(e) =>
                      setExtras((arr) =>
                        arr.map((x, i) =>
                          i === idx ? { ...x, label: e.target.value } : x,
                        ),
                      )
                    }
                  />
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() =>
                      setExtras((arr) => arr.filter((_, i) => i !== idx))
                    }
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() =>
                  setExtras((arr) => [...arr, { key: "", label: "", type: "text" }])
                }
              >
                <Plus size={14} />
                Ajouter une variable manuelle
              </button>
            </div>

            {error && <div className="form-error">{error}</div>}
            <button className="btn btn-primary" disabled={create.isPending}>
              <Plus size={15} />
              Ajouter le modèle
            </button>
          </form>
        </Card>

        <Card title="Catalogue des variables">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setShowVars((v) => !v)}
            style={{ marginBottom: 8 }}
          >
            <BookOpen size={14} />
            {showVars ? "Masquer les variables" : "Afficher les variables"}
          </button>
          <p className="muted small">
            Insérez ces balises dans vos modèles Word/Excel (ex.{" "}
            <code>{"{{ montant_accorde }}"}</code>). Survolez une balise pour
            voir sa description.
          </p>
          {variables.data?.loop_help && (
            <div className="callout callout-info" style={{ marginBottom: 8 }}>
              <strong>Tableaux & listes : </strong>
              {variables.data.loop_help}
            </div>
          )}
          {showVars &&
            variables.data?.groups.map((grp) => (
              <div key={grp.group} style={{ marginTop: 10 }}>
                <strong className="small">{grp.group}</strong>
                <div className="var-catalog">
                  {grp.items.map(([key, label]) => (
                    <span key={key} className="chip chip-muted" title={label}>
                      <code>{`{{ ${key} }}`}</code>
                    </span>
                  ))}
                </div>
              </div>
            ))}
        </Card>
      </div>

      {templates.isLoading || !templates.data ? (
        <Spinner />
      ) : templates.data.results.length === 0 ? (
        <EmptyState message="Aucun modèle de contrat. Ajoutez-en un ci-dessus." />
      ) : (
        <table className="table card" style={{ marginTop: 20 }}>
          <thead>
            <tr>
              <th>Intitulé</th>
              <th>Catégorie</th>
              <th>Cible</th>
              <th>Obligatoire</th>
              <th>Actif</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {templates.data.results.map((t) => (
              <tr key={t.id}>
                <td>{t.name}</td>
                <td>{t.category_display}</td>
                <td>{t.applies_to_display}</td>
                <td>
                  {t.is_required ? (
                    <Badge value="WARN" label="Oui" />
                  ) : (
                    <span className="muted small">Non</span>
                  )}
                </td>
                <td>
                  <Badge
                    value={t.is_active ? "ACTIVE" : "DRAFT"}
                    label={t.is_active ? "Oui" : "Non"}
                  />
                </td>
                <td>
                  <div className="row-actions">
                    <a
                      className="btn btn-ghost btn-sm"
                      href={t.file}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Modèle
                    </a>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => toggleActive.mutate(t)}
                      disabled={toggleActive.isPending}
                    >
                      <Power size={14} />
                      {t.is_active ? "Désactiver" : "Activer"}
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => {
                        if (
                          window.confirm(
                            `Supprimer le modèle « ${t.name} » ? Les contrats déjà générés sont conservés.`,
                          )
                        )
                          remove.mutate(t.id);
                      }}
                      disabled={remove.isPending}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

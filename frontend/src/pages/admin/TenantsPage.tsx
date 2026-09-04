import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Plus, Save, Trash2, X } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { Agency, Paginated, Tenant, TenantOfficer } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  Badge,
  Card,
  EmptyState,
  PageHeader,
  Spinner,
} from "@/components/ui";

type OfficerDraft = {
  title: string;
  last_name: string;
  first_name: string;
  phone: string;
};

const EMPTY_OFFICER: OfficerDraft = {
  title: "",
  last_name: "",
  first_name: "",
  phone: "",
};

const EMPTY_TENANT = {
  code: "",
  name: "",
  country: "",
  zone: "",
  currency: "XOF",
  timezone: "UTC",
  address: "",
  phone: "",
  email: "",
  is_active: true,
  brand_primary: "#0f9488",
  brand_secondary: "#0d7a72",
  brand_accent: "#d4a017",
};

const EMPTY_AGENCY = {
  code: "",
  name: "",
  region: "",
  address: "",
  manager_last_name: "",
  manager_first_name: "",
  manager_phone: "",
};

function fromOfficers(items?: TenantOfficer[]): OfficerDraft[] {
  if (!items?.length) return [];
  return items.map((o) => ({
    title: o.title ?? "",
    last_name: o.last_name ?? "",
    first_name: o.first_name ?? "",
    phone: o.phone ?? "",
  }));
}

function cleanOfficers(items: OfficerDraft[]) {
  return items
    .map((o) => ({
      title: o.title.trim(),
      last_name: o.last_name.trim(),
      first_name: o.first_name.trim(),
      phone: o.phone.trim(),
    }))
    .filter((o) => o.title || o.last_name || o.first_name || o.phone);
}

export function AdminTenantsPage() {
  const qc = useQueryClient();
  const { user, setActiveTenant } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_TENANT });
  const [officers, setOfficers] = useState<OfficerDraft[]>([]);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [agencyForm, setAgencyForm] = useState({ ...EMPTY_AGENCY });
  const [error, setError] = useState<string | null>(null);

  const tenants = useQuery({
    queryKey: ["tenants"],
    queryFn: async () =>
      (await api.get<Paginated<Tenant>>("/tenants/")).data,
    enabled: !!user?.is_group_level,
  });

  const selected = tenants.data?.results.find((t) => t.id === selectedId);

  const agencies = useQuery({
    queryKey: ["agencies", selectedId],
    queryFn: async () =>
      (
        await api.get<Paginated<Agency>>("/agencies/", {
          params: { tenant: selectedId },
          headers: { "X-Tenant-Id": selectedId! },
        })
      ).data,
    enabled: !!selectedId,
  });

  const createTenant = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => {
        if (typeof v === "boolean") fd.append(k, v ? "true" : "false");
        else if (v !== "") fd.append(k, String(v));
      });
      if (logoFile) fd.append("logo", logoFile);
      fd.append("officers", JSON.stringify(cleanOfficers(officers)));
      return (await api.post("/tenants/", fd)).data;
    },
    onSuccess: (created: Tenant) => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
      setShowForm(false);
      setForm({ ...EMPTY_TENANT });
      setOfficers([]);
      setLogoFile(null);
      setError(null);
      setSelectedId(created.id);
      setActiveTenant(created.id);
    },
    onError: () =>
      setError(
        "Création impossible. Vérifiez le code (unique) et les champs requis.",
      ),
  });

  const updateTenant = useMutation({
    mutationFn: async ({
      id,
      data,
      logo,
      officerList,
    }: {
      id: string;
      data: typeof form;
      logo: File | null;
      officerList: OfficerDraft[];
    }) => {
      const fd = new FormData();
      Object.entries(data).forEach(([k, v]) => {
        if (typeof v === "boolean") fd.append(k, v ? "true" : "false");
        else if (v !== "") fd.append(k, String(v));
      });
      if (logo) fd.append("logo", logo);
      fd.append("officers", JSON.stringify(cleanOfficers(officerList)));
      return (await api.patch(`/tenants/${id}/`, fd)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tenants"] });
      qc.invalidateQueries({ queryKey: ["tenant-branding"] });
      setError(null);
    },
    onError: () => setError("Mise à jour impossible."),
  });

  const createAgency = useMutation({
    mutationFn: async () =>
      (
        await api.post(
          "/agencies/",
          { ...agencyForm, tenant: selectedId },
          { headers: { "X-Tenant-Id": selectedId! } },
        )
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agencies", selectedId] });
      setAgencyForm({ ...EMPTY_AGENCY });
    },
  });

  if (!user?.is_group_level) {
    return (
      <div>
        <PageHeader
          icon={Building2}
          title="Filiales"
          subtitle="Réservé aux administrateurs Groupe"
        />
        <p className="muted">Vous n&apos;avez pas accès à la gestion des filiales.</p>
      </div>
    );
  }

  function openEdit(t: Tenant) {
    setSelectedId(t.id);
    setForm({
      code: t.code,
      name: t.name,
      country: t.country,
      zone: t.zone,
      currency: t.currency,
      timezone: t.timezone,
      address: t.address,
      phone: t.phone,
      email: t.email,
      is_active: t.is_active,
      brand_primary: t.brand_primary,
      brand_secondary: t.brand_secondary,
      brand_accent: t.brand_accent,
    });
    setOfficers(fromOfficers(t.officers));
    setLogoFile(null);
  }

  return (
    <div>
      <PageHeader
        icon={Building2}
        title="Filiales"
        subtitle="Création, configuration, logo, couleurs, responsables et agences"
        actions={
          <button
            className="btn btn-primary"
            onClick={() => {
              setShowForm((s) => !s);
              if (!showForm) {
                setForm({ ...EMPTY_TENANT });
                setOfficers([]);
                setLogoFile(null);
              }
            }}
          >
            {showForm ? <X /> : <Plus />}
            {showForm ? "Fermer" : "Nouvelle filiale"}
          </button>
        }
      />

      {showForm && (
        <form
          className="inline-form"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            createTenant.mutate();
          }}
        >
          <TenantFields
            form={form}
            setForm={setForm}
            logoFile={logoFile}
            setLogoFile={setLogoFile}
          />
          <OfficersEditor officers={officers} setOfficers={setOfficers} />
          {error && <div className="form-error">{error}</div>}
          <button className="btn btn-primary" disabled={createTenant.isPending}>
            Créer la filiale
          </button>
        </form>
      )}

      <div className="detail-grid stacked">
        <Card title="Filiales">
          {tenants.isLoading || !tenants.data ? (
            <Spinner />
          ) : tenants.data.results.length === 0 ? (
            <EmptyState message="Aucune filiale." />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Raison sociale</th>
                  <th>Pays</th>
                  <th>Devise</th>
                  <th>Statut</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {tenants.data.results.map((t) => (
                  <tr key={t.id}>
                    <td>{t.code}</td>
                    <td>{t.name}</td>
                    <td>{t.country}</td>
                    <td>{t.currency}</td>
                    <td>
                      <Badge
                        value={t.is_active ? "success" : "muted"}
                        label={t.is_active ? "Active" : "Inactive"}
                      />
                    </td>
                    <td>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => openEdit(t)}
                      >
                        Configurer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card
          title={
            selected ? `Configuration — ${selected.code}` : "Configuration"
          }
        >
          {!selected ? (
            <p className="muted">Sélectionnez une filiale à configurer.</p>
          ) : (
            <>
              {selected.logo_url && (
                <div className="tenant-logo-preview">
                  <img src={selected.logo_url} alt="Logo filiale" />
                </div>
              )}
              <form
                className="stack"
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  updateTenant.mutate({
                    id: selected.id,
                    data: form,
                    logo: logoFile,
                    officerList: officers,
                  });
                }}
              >
                <TenantFields
                  form={form}
                  setForm={setForm}
                  logoFile={logoFile}
                  setLogoFile={setLogoFile}
                  codeReadOnly
                />
                <OfficersEditor officers={officers} setOfficers={setOfficers} />
                {error && <div className="form-error">{error}</div>}
                <button
                  className="btn btn-primary btn-sm"
                  disabled={updateTenant.isPending}
                >
                  <Save />
                  Enregistrer
                </button>
              </form>

              <hr
                style={{
                  margin: "20px 0",
                  border: "none",
                  borderTop: "1px solid var(--border)",
                }}
              />

              <h4 className="card-subtitle">Agences</h4>
              {agencies.isLoading ? (
                <Spinner />
              ) : (
                <ul className="workflow-steps">
                  {(agencies.data?.results ?? []).map((a) => (
                    <li key={a.id}>
                      {a.code} — {a.name}
                      {a.region && (
                        <span className="muted small"> ({a.region})</span>
                      )}
                      {(a.manager_last_name || a.manager_first_name) && (
                        <span className="muted small">
                          {" "}
                          — Chef :{" "}
                          {`${a.manager_first_name} ${a.manager_last_name}`.trim()}
                          {a.manager_phone ? ` (${a.manager_phone})` : ""}
                        </span>
                      )}
                    </li>
                  ))}
                  {(agencies.data?.results.length ?? 0) === 0 && (
                    <li className="muted">Aucune agence.</li>
                  )}
                </ul>
              )}
              <form
                className="stack"
                style={{ marginTop: 12 }}
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  createAgency.mutate();
                }}
              >
                <div className="form-grid two-col">
                  <label className="field">
                    <span>Code agence *</span>
                    <input
                      value={agencyForm.code}
                      onChange={(e) =>
                        setAgencyForm({ ...agencyForm, code: e.target.value })
                      }
                      required
                    />
                  </label>
                  <label className="field">
                    <span>Nom agence *</span>
                    <input
                      value={agencyForm.name}
                      onChange={(e) =>
                        setAgencyForm({ ...agencyForm, name: e.target.value })
                      }
                      required
                    />
                  </label>
                  <label className="field">
                    <span>Région</span>
                    <input
                      value={agencyForm.region}
                      onChange={(e) =>
                        setAgencyForm({
                          ...agencyForm,
                          region: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label className="field">
                    <span>Nom du chef d&apos;agence</span>
                    <input
                      value={agencyForm.manager_last_name}
                      onChange={(e) =>
                        setAgencyForm({
                          ...agencyForm,
                          manager_last_name: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label className="field">
                    <span>Prénom du chef d&apos;agence</span>
                    <input
                      value={agencyForm.manager_first_name}
                      onChange={(e) =>
                        setAgencyForm({
                          ...agencyForm,
                          manager_first_name: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label className="field">
                    <span>Téléphone du chef d&apos;agence</span>
                    <input
                      value={agencyForm.manager_phone}
                      onChange={(e) =>
                        setAgencyForm({
                          ...agencyForm,
                          manager_phone: e.target.value,
                        })
                      }
                    />
                  </label>
                </div>
                <button
                  className="btn btn-primary btn-sm"
                  disabled={createAgency.isPending}
                >
                  <Plus />
                  Ajouter l&apos;agence
                </button>
              </form>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}

function OfficersEditor({
  officers,
  setOfficers,
}: {
  officers: OfficerDraft[];
  setOfficers: (
    items: OfficerDraft[] | ((prev: OfficerDraft[]) => OfficerDraft[]),
  ) => void;
}) {
  const update = (idx: number, patch: Partial<OfficerDraft>) =>
    setOfficers((arr) =>
      arr.map((item, i) => (i === idx ? { ...item, ...patch } : item)),
    );

  return (
    <div className="field" style={{ gridColumn: "1 / -1", marginTop: 8 }}>
      <span>Responsables de la filiale</span>
      <p className="muted small" style={{ margin: "4px 0 10px" }}>
        Ajoutez au besoin les responsables (DG, Directeur d&apos;exploitation,
        etc.).
      </p>
      {officers.map((o, idx) => (
        <div key={idx} className="officer-row">
          <input
            placeholder="Intitulé du poste *"
            value={o.title}
            onChange={(e) => update(idx, { title: e.target.value })}
          />
          <input
            placeholder="Nom *"
            value={o.last_name}
            onChange={(e) => update(idx, { last_name: e.target.value })}
          />
          <input
            placeholder="Prénom"
            value={o.first_name}
            onChange={(e) => update(idx, { first_name: e.target.value })}
          />
          <input
            placeholder="Téléphone"
            value={o.phone}
            onChange={(e) => update(idx, { phone: e.target.value })}
          />
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() =>
              setOfficers((arr) => arr.filter((_, i) => i !== idx))
            }
            title="Retirer"
            aria-label="Retirer"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        onClick={() => setOfficers((arr) => [...arr, { ...EMPTY_OFFICER }])}
      >
        <Plus size={14} />
        Ajouter un responsable
      </button>
    </div>
  );
}

function TenantFields({
  form,
  setForm,
  logoFile,
  setLogoFile,
  codeReadOnly,
}: {
  form: typeof EMPTY_TENANT;
  setForm: (f: typeof EMPTY_TENANT) => void;
  logoFile: File | null;
  setLogoFile: (f: File | null) => void;
  codeReadOnly?: boolean;
}) {
  return (
    <div className="page-shell form-grid two-col">
      <label className="field">
        <span>Code filiale *</span>
        <input
          value={form.code}
          onChange={(e) => setForm({ ...form, code: e.target.value })}
          required
          readOnly={codeReadOnly}
        />
      </label>
      <label className="field">
        <span>Raison sociale *</span>
        <input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
      </label>
      <label className="field">
        <span>Pays *</span>
        <input
          value={form.country}
          onChange={(e) => setForm({ ...form, country: e.target.value })}
          required
        />
      </label>
      <label className="field">
        <span>Zone / région</span>
        <input
          value={form.zone}
          onChange={(e) => setForm({ ...form, zone: e.target.value })}
        />
      </label>
      <label className="field">
        <span>Devise</span>
        <input
          value={form.currency}
          onChange={(e) => setForm({ ...form, currency: e.target.value })}
        />
      </label>
      <label className="field">
        <span>Fuseau horaire</span>
        <input
          value={form.timezone}
          onChange={(e) => setForm({ ...form, timezone: e.target.value })}
        />
      </label>
      <label className="field">
        <span>Adresse</span>
        <input
          value={form.address}
          onChange={(e) => setForm({ ...form, address: e.target.value })}
        />
      </label>
      <label className="field">
        <span>Téléphone</span>
        <input
          value={form.phone}
          onChange={(e) => setForm({ ...form, phone: e.target.value })}
        />
      </label>
      <label className="field">
        <span>Email</span>
        <input
          type="email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
      </label>
      <label className="field">
        <span>Logo</span>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)}
        />
        {logoFile && <span className="muted small">{logoFile.name}</span>}
      </label>
      <label className="field color-field">
        <span>Couleur principale</span>
        <input
          type="color"
          value={form.brand_primary}
          onChange={(e) => setForm({ ...form, brand_primary: e.target.value })}
        />
        <input value={form.brand_primary} readOnly className="color-hex" />
      </label>
      <label className="field color-field">
        <span>Couleur secondaire</span>
        <input
          type="color"
          value={form.brand_secondary}
          onChange={(e) =>
            setForm({ ...form, brand_secondary: e.target.value })
          }
        />
        <input value={form.brand_secondary} readOnly className="color-hex" />
      </label>
      <label className="field color-field">
        <span>Couleur d&apos;accent</span>
        <input
          type="color"
          value={form.brand_accent}
          onChange={(e) => setForm({ ...form, brand_accent: e.target.value })}
        />
        <input value={form.brand_accent} readOnly className="color-hex" />
      </label>
      <label className="field checkbox">
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
        />
        <span>Filiale active</span>
      </label>
    </div>
  );
}

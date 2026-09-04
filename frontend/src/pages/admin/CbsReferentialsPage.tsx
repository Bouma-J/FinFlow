import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookMarked } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { CbsCatalogItem, Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  Card,
  EmptyState,
  PageHeader,
  Spinner,
  TenantScopeNotice,
} from "@/components/ui";

type TabKey = "periodicities" | "repayment_methods" | "currencies";

const TABS: { key: TabKey; label: string; endpoint: string }[] = [
  {
    key: "periodicities",
    label: "Périodicités",
    endpoint: "/loan-periodicities/",
  },
  {
    key: "repayment_methods",
    label: "Méthodes de remboursement",
    endpoint: "/repayment-methods/",
  },
  { key: "currencies", label: "Devises", endpoint: "/currencies/" },
];

const EMPTY = {
  code: "",
  label: "",
  cbs_code: "",
  periods_per_year: 12,
  sort_order: 0,
  is_active: true,
};

export function AdminCbsReferentialsPage() {
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabKey>("periodicities");
  const [form, setForm] = useState({ ...EMPTY });
  const [error, setError] = useState<string | null>(null);

  const current = TABS.find((t) => t.key === tab)!;

  const items = useQuery({
    queryKey: ["cbs-catalog", tab, activeTenant],
    queryFn: async () =>
      (
        await api.get<Paginated<CbsCatalogItem>>(current.endpoint, {
          params: { page_size: 200 },
        })
      ).data,
    enabled: !needsTenant,
  });

  const create = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        code: form.code.trim().toUpperCase(),
        label: form.label.trim(),
        cbs_code: form.cbs_code.trim(),
        sort_order: form.sort_order,
        is_active: form.is_active,
      };
      if (tab === "periodicities") {
        payload.periods_per_year = form.periods_per_year;
      }
      return (await api.post(current.endpoint, payload)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cbs-catalog", tab] });
      setForm({ ...EMPTY });
      setError(null);
    },
    onError: () =>
      setError("Création impossible. Vérifiez le code (unique) et les champs."),
  });

  const patch = useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: Partial<CbsCatalogItem>;
    }) => (await api.patch(`${current.endpoint}${id}/`, data)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cbs-catalog", tab] }),
  });

  if (needsTenant) {
    return (
      <div className="page-shell">
        <PageHeader
          icon={BookMarked}
          title="Référentiels CBS"
          subtitle="Périodicités, remboursements, devises"
        />
        <TenantScopeNotice />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        icon={BookMarked}
        title="Référentiels CBS"
        subtitle="Codes métier FIN_FLOW et identifiants Perfect pour le mapping décaissement"
      />

      <div className="tabs" style={{ marginBottom: 16, display: "flex", gap: 8 }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={`btn btn-sm ${tab === t.key ? "btn-primary" : "btn-ghost"}`}
            onClick={() => {
              setTab(t.key);
              setForm({ ...EMPTY });
              setError(null);
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <Card title={`Ajouter — ${current.label}`}>
        <form
          className="inline-form"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <div className="form-grid">
            <label className="field">
              <span>Code FIN_FLOW *</span>
              <input
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
                placeholder={tab === "currencies" ? "XOF" : "MONTHLY"}
                required
              />
            </label>
            <label className="field">
              <span>Libellé *</span>
              <input
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
                required
              />
            </label>
            <label className="field">
              <span>Identifiant CBS *</span>
              <input
                value={form.cbs_code}
                onChange={(e) => setForm({ ...form, cbs_code: e.target.value })}
                placeholder={
                  tab === "periodicities"
                    ? "MENSUEL"
                    : tab === "currencies"
                      ? "XOF"
                      : "COMPTE-COURANT"
                }
                required
              />
            </label>
            {tab === "periodicities" && (
              <label className="field">
                <span>Périodes / an</span>
                <input
                  type="number"
                  min={1}
                  value={form.periods_per_year}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      periods_per_year: Number(e.target.value),
                    })
                  }
                />
              </label>
            )}
            <label className="field">
              <span>Ordre</span>
              <input
                type="number"
                value={form.sort_order}
                onChange={(e) =>
                  setForm({ ...form, sort_order: Number(e.target.value) })
                }
              />
            </label>
          </div>
          {error && <div className="form-error">{error}</div>}
          <button className="btn btn-primary btn-sm" disabled={create.isPending}>
            Enregistrer
          </button>
        </form>
      </Card>

      {items.isLoading || !items.data ? (
        <Spinner />
      ) : items.data.results.length === 0 ? (
        <EmptyState message="Aucun élément. Créez-en ou relancez le bootstrap filiale." />
      ) : (
        <table className="table card" style={{ marginTop: 20 }}>
          <thead>
            <tr>
              <th>Code</th>
              <th>Libellé</th>
              <th>ID CBS</th>
              {tab === "periodicities" && <th className="num">/ an</th>}
              <th>Actif</th>
            </tr>
          </thead>
          <tbody>
            {items.data.results.map((row) => (
              <tr key={row.id}>
                <td>{row.code}</td>
                <td>{row.label}</td>
                <td>
                  <input
                    className="input-inline"
                    defaultValue={row.cbs_code || ""}
                    onBlur={(e) => {
                      const next = e.target.value.trim();
                      if (next !== (row.cbs_code || "")) {
                        patch.mutate({ id: row.id, data: { cbs_code: next } });
                      }
                    }}
                    placeholder="—"
                  />
                </td>
                {tab === "periodicities" && (
                  <td className="num">{row.periods_per_year ?? "—"}</td>
                )}
                <td>
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={row.is_active}
                      onChange={(e) =>
                        patch.mutate({
                          id: row.id,
                          data: { is_active: e.target.checked },
                        })
                      }
                    />
                    <span>{row.is_active ? "Oui" : "Non"}</span>
                  </label>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Package } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { CreditProduct, Paginated, ProductCategory } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  Badge,
  Card,
  EmptyState,
  PageHeader,
  Spinner,
  TenantScopeNotice,
  formatMoney,
} from "@/components/ui";

export function AdminProductsPage() {
  const { user, activeTenant } = useAuth();
  const qc = useQueryClient();
  const needsTenant = user?.is_group_level && !activeTenant;

  const [cat, setCat] = useState({ code: "", label: "" });
  const [prod, setProd] = useState({
    code: "",
    label: "",
    category: "",
    currency: "XOF",
    amount_min: "100000",
    amount_max: "50000000",
    duration_min_months: 3,
    duration_max_months: 36,
    interest_rate: "12.5",
  });
  const [error, setError] = useState<string | null>(null);

  const categories = useQuery({
    queryKey: ["product-categories", activeTenant],
    queryFn: async () =>
      (await api.get<Paginated<ProductCategory>>("/product-categories/")).data,
    enabled: !needsTenant,
  });
  const products = useQuery({
    queryKey: ["credit-products", activeTenant],
    queryFn: async () =>
      (await api.get<Paginated<CreditProduct>>("/credit-products/")).data,
    enabled: !needsTenant,
  });
  const tenants = useQuery({
    queryKey: ["tenants"],
    queryFn: async () =>
      (await api.get<Paginated<{ id: string; code: string; name: string }>>("/tenants/")).data,
    enabled: !!user?.is_group_level,
  });

  const scopeLabel = user?.is_group_level
    ? tenants.data?.results.find((t) => t.id === activeTenant)?.name ?? "filiale sélectionnée"
    : "votre filiale";

  const createCat = useMutation({
    mutationFn: async () => (await api.post("/product-categories/", cat)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["product-categories"] });
      setCat({ code: "", label: "" });
    },
  });
  const createProd = useMutation({
    mutationFn: async () => (await api.post("/credit-products/", prod)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["credit-products"] });
      setError(null);
      setProd({ ...prod, code: "", label: "" });
    },
    onError: () => setError("Création impossible. Vérifiez les champs."),
  });

  if (needsTenant) {
    return (
      <div>
        <PageHeader
          icon={Package}
          title="Produits de crédit"
          subtitle="Catalogue par filiale"
        />
        <TenantScopeNotice />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        icon={Package}
        title="Produits de crédit"
        subtitle={`Familles et produits — ${scopeLabel}`}
      />

      <div className="detail-grid">
        <Card title="Familles de produits">
          <form
            className="stack"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createCat.mutate();
            }}
          >
            <div className="form-grid">
              <label className="field">
                <span>Code</span>
                <input
                  value={cat.code}
                  onChange={(e) => setCat({ ...cat, code: e.target.value })}
                  required
                />
              </label>
              <label className="field">
                <span>Libellé</span>
                <input
                  value={cat.label}
                  onChange={(e) => setCat({ ...cat, label: e.target.value })}
                  required
                />
              </label>
            </div>
            <button className="btn btn-primary btn-sm" disabled={createCat.isPending}>
              Ajouter la famille
            </button>
          </form>
          <div style={{ marginTop: 12 }}>
            {categories.data?.results.map((c) => (
              <span key={c.id} className="badge badge-muted">
                {c.code} · {c.label}
              </span>
            ))}
          </div>
        </Card>

        <Card title="Nouveau produit">
          <form
            className="stack"
            onSubmit={(e: FormEvent) => {
              e.preventDefault();
              createProd.mutate();
            }}
          >
            <div className="form-grid">
              <label className="field">
                <span>Code</span>
                <input
                  value={prod.code}
                  onChange={(e) => setProd({ ...prod, code: e.target.value })}
                  required
                />
              </label>
              <label className="field">
                <span>Libellé</span>
                <input
                  value={prod.label}
                  onChange={(e) => setProd({ ...prod, label: e.target.value })}
                  required
                />
              </label>
              <label className="field">
                <span>Famille</span>
                <select
                  value={prod.category}
                  onChange={(e) =>
                    setProd({ ...prod, category: e.target.value })
                  }
                  required
                >
                  <option value="">— choisir —</option>
                  {categories.data?.results.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Devise</span>
                <input
                  value={prod.currency}
                  onChange={(e) =>
                    setProd({ ...prod, currency: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Montant min</span>
                <input
                  type="number"
                  value={prod.amount_min}
                  onChange={(e) =>
                    setProd({ ...prod, amount_min: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Montant max</span>
                <input
                  type="number"
                  value={prod.amount_max}
                  onChange={(e) =>
                    setProd({ ...prod, amount_max: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Taux annuel (%)</span>
                <input
                  type="number"
                  step="0.001"
                  value={prod.interest_rate}
                  onChange={(e) =>
                    setProd({ ...prod, interest_rate: e.target.value })
                  }
                />
              </label>
              <label className="field">
                <span>Durée min (mois)</span>
                <input
                  type="number"
                  value={prod.duration_min_months}
                  onChange={(e) =>
                    setProd({
                      ...prod,
                      duration_min_months: Number(e.target.value),
                    })
                  }
                />
              </label>
              <label className="field">
                <span>Durée max (mois)</span>
                <input
                  type="number"
                  value={prod.duration_max_months}
                  onChange={(e) =>
                    setProd({
                      ...prod,
                      duration_max_months: Number(e.target.value),
                    })
                  }
                />
              </label>
            </div>
            {error && <div className="form-error">{error}</div>}
            <button className="btn btn-primary btn-sm" disabled={createProd.isPending}>
              Créer le produit
            </button>
          </form>
        </Card>
      </div>

      {products.isLoading || !products.data ? (
        <Spinner />
      ) : products.data.results.length === 0 ? (
        <EmptyState message="Aucun produit." />
      ) : (
        <table className="table card" style={{ marginTop: 20 }}>
          <thead>
            <tr>
              <th>Code</th>
              <th>Libellé</th>
              <th className="num">Min</th>
              <th className="num">Max</th>
              <th className="num">Taux</th>
              <th>Actif</th>
            </tr>
          </thead>
          <tbody>
            {products.data.results.map((p) => (
              <tr key={p.id}>
                <td>{p.code}</td>
                <td>{p.label}</td>
                <td className="num">{formatMoney(p.amount_min, p.currency)}</td>
                <td className="num">{formatMoney(p.amount_max, p.currency)}</td>
                <td className="num">{p.interest_rate} %</td>
                <td>
                  <Badge
                    value={p.is_active ? "ACTIVE" : "DRAFT"}
                    label={p.is_active ? "Oui" : "Non"}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

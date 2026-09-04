import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cable } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { CbsConnector, Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  Badge,
  EmptyState,
  PageHeader,
  Spinner,
  TenantScopeNotice,
} from "@/components/ui";

const PROTOCOLS = ["REST", "SOAP", "SFTP", "BATCH"];

export function AdminConnectorsPage() {
  const { user, activeTenant } = useAuth();
  const qc = useQueryClient();
  const needsTenant = user?.is_group_level && !activeTenant;

  const [form, setForm] = useState({
    name: "",
    protocol: "REST",
    base_url: "",
    timeout_seconds: 30,
    max_retries: 3,
    auth_username: "",
    auth_password: "",
    auth_token: "",
    auth_token_url: "",
    adh_situation_path: "gateway-perfect/adh/situation",
    sim_loan_settled: true,
    sim_client_outstanding: "1000000",
  });
  const [error, setError] = useState<string | null>(null);

  const connectors = useQuery({
    queryKey: ["cbs-connectors", activeTenant],
    queryFn: async () =>
      (await api.get<Paginated<CbsConnector>>("/cbs-connectors/")).data,
    enabled: !needsTenant,
  });

  const create = useMutation({
    mutationFn: async () => {
      const auth_config: Record<string, string> = {};
      if (form.auth_username) auth_config.username = form.auth_username;
      if (form.auth_password) auth_config.password = form.auth_password;
      if (form.auth_token) auth_config.access_token = form.auth_token;
      if (form.auth_token_url) auth_config.token_url = form.auth_token_url;
      const mapping_rules = {
        endpoints: {
          adh_situation:
            form.adh_situation_path.trim() ||
            "gateway-perfect/adh/situation",
        },
        simulate: {
          loan_settled_default: form.sim_loan_settled,
          client_outstanding_default: form.sim_client_outstanding,
        },
      };
      return (
        await api.post("/cbs-connectors/", {
          name: form.name,
          protocol: form.protocol,
          base_url: form.base_url,
          timeout_seconds: form.timeout_seconds,
          max_retries: form.max_retries,
          auth_config,
          mapping_rules,
          is_active: true,
        })
      ).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cbs-connectors"] });
      setForm({
        ...form,
        name: "",
        base_url: "",
        auth_username: "",
        auth_password: "",
        auth_token: "",
        auth_token_url: "",
      });
      setError(null);
    },
    onError: () => setError("Création impossible. Vérifiez les champs."),
  });

  if (needsTenant) {
    return (
    <div className="page-shell">
        <PageHeader
          icon={Cable}
          title="Connecteurs Core Banking"
          subtitle="Par filiale"
        />
        <TenantScopeNotice />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        icon={Cable}
        title="Connecteurs Core Banking"
        subtitle="Chaque filiale configure son CBS (auth, mapping, simulation)"
      />

      <form
        className="inline-form"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <div className="form-grid">
          <label className="field">
            <span>Nom</span>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </label>
          <label className="field">
            <span>Protocole</span>
            <select
              value={form.protocol}
              onChange={(e) => setForm({ ...form, protocol: e.target.value })}
            >
              {PROTOCOLS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>URL de base</span>
            <input
              value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              placeholder="https://cbs.filiale.local/api"
            />
          </label>
          <label className="field">
            <span>Timeout (s)</span>
            <input
              type="number"
              value={form.timeout_seconds}
              onChange={(e) =>
                setForm({ ...form, timeout_seconds: Number(e.target.value) })
              }
            />
          </label>
          <label className="field">
            <span>Tentatives max</span>
            <input
              type="number"
              value={form.max_retries}
              onChange={(e) =>
                setForm({ ...form, max_retries: Number(e.target.value) })
              }
            />
          </label>
          <label className="field">
            <span>Auth — utilisateur</span>
            <input
              value={form.auth_username}
              onChange={(e) =>
                setForm({ ...form, auth_username: e.target.value })
              }
              autoComplete="off"
            />
          </label>
          <label className="field">
            <span>Auth — mot de passe</span>
            <input
              type="password"
              value={form.auth_password}
              onChange={(e) =>
                setForm({ ...form, auth_password: e.target.value })
              }
              autoComplete="new-password"
            />
          </label>
          <label className="field">
            <span>Auth — access token (Bearer)</span>
            <input
              type="password"
              value={form.auth_token}
              onChange={(e) =>
                setForm({ ...form, auth_token: e.target.value })
              }
              placeholder="Optionnel si token_url renseigné"
              autoComplete="off"
            />
          </label>
          <label className="field">
            <span>Auth — URL token OAuth</span>
            <input
              value={form.auth_token_url}
              onChange={(e) =>
                setForm({ ...form, auth_token_url: e.target.value })
              }
              placeholder="https://…/oauth/token"
            />
          </label>
          <label className="field">
            <span>Endpoint situation adhérent</span>
            <input
              value={form.adh_situation_path}
              onChange={(e) =>
                setForm({ ...form, adh_situation_path: e.target.value })
              }
              placeholder="gateway-perfect/adh/situation"
            />
          </label>
          <label className="field">
            <span>Simulation — prêt soldé par défaut</span>
            <select
              value={form.sim_loan_settled ? "1" : "0"}
              onChange={(e) =>
                setForm({
                  ...form,
                  sim_loan_settled: e.target.value === "1",
                })
              }
            >
              <option value="1">Oui (main levée possible)</option>
              <option value="0">Non (blocage main levée)</option>
            </select>
          </label>
          <label className="field">
            <span>Simulation — encours client défaut</span>
            <input
              value={form.sim_client_outstanding}
              onChange={(e) =>
                setForm({ ...form, sim_client_outstanding: e.target.value })
              }
            />
          </label>
        </div>
        {error && <div className="form-error">{error}</div>}
        <button className="btn btn-primary btn-sm" disabled={create.isPending}>
          Ajouter le connecteur
        </button>
      </form>

      {connectors.isLoading || !connectors.data ? (
        <Spinner />
      ) : connectors.data.results.length === 0 ? (
        <EmptyState message="Aucun connecteur configuré." />
      ) : (
        <table className="table card">
          <thead>
            <tr>
              <th>Nom</th>
              <th>Protocole</th>
              <th>URL</th>
              <th className="num">Timeout</th>
              <th className="num">Retries</th>
              <th>Actif</th>
            </tr>
          </thead>
          <tbody>
            {connectors.data.results.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.protocol}</td>
                <td className="muted small">{c.base_url}</td>
                <td className="num">{c.timeout_seconds}s</td>
                <td className="num">{c.max_retries}</td>
                <td>
                  <Badge
                    value={c.is_active ? "ACTIVE" : "DRAFT"}
                    label={c.is_active ? "Oui" : "Non"}
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

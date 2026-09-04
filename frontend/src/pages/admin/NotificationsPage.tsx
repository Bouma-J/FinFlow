import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Bell, Building2, Mail, Send } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type {
  NotificationSettings,
  Paginated,
  NotificationLog,
  Tenant,
} from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  Badge,
  EmptyState,
  PageHeader,
  Spinner,
  formatDate,
} from "@/components/ui";

const EMPTY: NotificationSettings = {
  id: "",
  enabled: true,
  notify_on_step: true,
  notify_on_completion: true,
  notify_on_rejection: true,
  notify_on_return: true,
  notify_collection_email: false,
  notify_collection_sms: false,
  from_email: "",
  reply_to: "",
  cc_tenant_email: false,
  smtp_host: "",
  smtp_port: 587,
  smtp_use_tls: true,
  smtp_use_ssl: false,
  smtp_username: "",
  smtp_password: "",
  smtp_password_configured: false,
  smtp_configured: false,
  effective_from_email: "",
  updated_at: "",
};

export function AdminNotificationsPage() {
  const { user, activeTenant, setActiveTenant } = useAuth();
  const qc = useQueryClient();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);
  const [form, setForm] = useState<NotificationSettings>(EMPTY);
  const [smtpPassword, setSmtpPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [testTo, setTestTo] = useState(user?.email ?? "");
  const [testMsg, setTestMsg] = useState<string | null>(null);

  const tenants = useQuery({
    queryKey: ["tenants"],
    queryFn: async () => (await api.get<Paginated<Tenant>>("/tenants/")).data,
    enabled: Boolean(user?.is_group_level),
  });

  const activeTenantLabel = (() => {
    if (!user?.is_group_level) {
      return user?.tenant_branding?.name || "Filiale connectée";
    }
    const match = tenants.data?.results.find((t) => t.id === activeTenant);
    return match ? `${match.code} — ${match.name}` : null;
  })();

  const settings = useQuery({
    queryKey: ["notification-settings", activeTenant],
    queryFn: async () =>
      (await api.get<NotificationSettings>("/notification-settings/current/"))
        .data,
    enabled: !needsTenant,
  });

  const logs = useQuery({
    queryKey: ["notification-logs", activeTenant],
    queryFn: async () =>
      (await api.get<Paginated<NotificationLog>>("/notification-logs/")).data,
    enabled: !needsTenant,
  });

  useEffect(() => {
    if (settings.data) {
      setForm(settings.data);
      setSmtpPassword("");
      if (!testTo && settings.data.from_email) {
        setTestTo(user?.email || settings.data.from_email);
      }
    }
  }, [settings.data, user?.email, testTo]);

  const save = useMutation({
    mutationFn: async () => {
      const payload: Record<string, unknown> = {
        enabled: form.enabled,
        notify_on_step: form.notify_on_step,
        notify_on_completion: form.notify_on_completion,
        notify_on_rejection: form.notify_on_rejection,
        notify_on_return: form.notify_on_return,
        notify_collection_email: form.notify_collection_email,
        notify_collection_sms: form.notify_collection_sms,
        from_email: form.from_email,
        reply_to: form.reply_to,
        cc_tenant_email: form.cc_tenant_email,
        smtp_host: form.smtp_host,
        smtp_port: form.smtp_port,
        smtp_use_tls: form.smtp_use_tls,
        smtp_use_ssl: form.smtp_use_ssl,
        smtp_username: form.smtp_username,
      };
      if (smtpPassword.trim()) {
        payload.smtp_password = smtpPassword.trim();
      }
      return (
        await api.patch<NotificationSettings>(
          "/notification-settings/current/",
          payload,
        )
      ).data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["notification-settings"] });
      setForm(data);
      setSmtpPassword("");
      setError(null);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
    onError: (err: unknown) => {
      const data =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: Record<string, unknown> } }).response
              ?.data
          : undefined;
      const parts: string[] = [];
      if (data) {
        for (const [key, val] of Object.entries(data)) {
          if (key === "detail") {
            parts.push(String(val));
            continue;
          }
          if (Array.isArray(val)) parts.push(`${key}: ${val.join(" ")}`);
          else if (typeof val === "string") parts.push(`${key}: ${val}`);
        }
      }
      setError(
        parts.length
          ? parts.join(" — ")
          : "Enregistrement impossible. Vérifiez les champs et vos droits.",
      );
    },
  });

  const testMail = useMutation({
    mutationFn: async () =>
      (
        await api.post<{ detail: string; from_email?: string }>(
          "/notification-settings/current/test/",
          { to: testTo },
          { timeout: 45000 },
        )
      ).data,
    onSuccess: (data) => {
      setTestMsg(data.detail);
      setError(null);
      qc.invalidateQueries({ queryKey: ["notification-logs"] });
    },
    onError: (err: unknown) => {
      setTestMsg(null);
      if (axios.isAxiosError(err)) {
        const data = err.response?.data as
          | { detail?: string; error?: string; hint?: string }
          | string
          | undefined;
        if (data && typeof data === "object") {
          const msg = [data.detail, data.error, data.hint]
            .filter(Boolean)
            .join(" — ");
          if (msg) {
            setError(msg);
            return;
          }
        }
        if (err.code === "ECONNABORTED") {
          setError(
            "Délai dépassé : le serveur SMTP ne répond pas. " +
              "Désactivez Avast/Norton Mail Shield, puis réessayez.",
          );
          return;
        }
        if (err.response?.status === 502 || err.response?.status === 504) {
          setError(
            "Passerelle saturée (timeout). Le SMTP est probablement bloqué " +
              "par l'antivirus ou le pare-feu Windows.",
          );
          return;
        }
        setError(
          err.message ||
            `Échec de l'e-mail de test (HTTP ${err.response?.status ?? "?"}).`,
        );
        return;
      }
      setError("Échec de l'e-mail de test.");
    },
  });

  if (needsTenant) {
    return (
    <div className="page-shell">
        <PageHeader
          icon={Bell}
          title="Alertes e-mail"
          subtitle="Par filiale"
        />
        <div className="card form-card">
          <h3 className="section-subtitle">
            <Building2 size={16} /> Choisir la filiale
          </h3>
          <p className="muted small" style={{ marginBottom: 12 }}>
            Les alertes e-mail et le SMTP sont propres à chaque filiale.
            Sélectionnez celle à paramétrer :
          </p>
          <label className="field">
            <span>Filiale</span>
            <select
              value={activeTenant ?? ""}
              onChange={(e) => setActiveTenant(e.target.value || null)}
            >
              <option value="">— Sélectionner —</option>
              {tenants.data?.results.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.code} — {t.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        icon={Bell}
        title="Alertes e-mail"
        subtitle={
          activeTenantLabel
            ? `SMTP et notifications — ${activeTenantLabel}`
            : "SMTP et notifications de circuit pour la filiale active"
        }
      />

      {settings.isLoading ? (
        <Spinner />
      ) : (
        <form
          className="card form-card"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <h3 className="section-subtitle">
            <Mail size={16} /> Serveur SMTP de la filiale
          </h3>
          <p className="muted small" style={{ marginBottom: 12 }}>
            Configurez ici le compte mail utilisé pour envoyer les identifiants
            utilisateurs et les alertes de circuit de <strong>cette filiale</strong>.
            Si le serveur SMTP est vide, FIN_FLOW utilise la configuration globale
            du serveur (variables d&apos;environnement).
          </p>
          {form.smtp_configured ? (
            <p className="form-success" style={{ marginBottom: 12 }}>
              SMTP filiale actif — expéditeur effectif :{" "}
              <code>{form.effective_from_email || "—"}</code>
            </p>
          ) : (
            <p className="muted small" style={{ marginBottom: 12 }}>
              Aucun SMTP filiale configuré (repli sur la config globale).
            </p>
          )}
          <div className="form-grid">
            <label className="field">
              <span>Serveur SMTP *</span>
              <input
                value={form.smtp_host}
                onChange={(e) =>
                  setForm({ ...form, smtp_host: e.target.value })
                }
                placeholder="smtp.gmail.com"
              />
            </label>
            <label className="field">
              <span>Port</span>
              <input
                type="number"
                value={form.smtp_port}
                onChange={(e) => {
                  const port = Number(e.target.value) || 587;
                  // 587 = STARTTLS, 465 = SSL implicite
                  setForm({
                    ...form,
                    smtp_port: port,
                    smtp_use_tls: port !== 465,
                    smtp_use_ssl: port === 465,
                  });
                }}
              />
            </label>
            <label className="field">
              <span>Identifiant SMTP (compte)</span>
              <input
                value={form.smtp_username}
                onChange={(e) =>
                  setForm({ ...form, smtp_username: e.target.value })
                }
                placeholder="noreply@filiale.com"
                autoComplete="off"
              />
            </label>
            <label className="field">
              <span>
                Mot de passe SMTP
                {form.smtp_password_configured
                  ? " (laisser vide pour conserver)"
                  : ""}
              </span>
              <input
                type="password"
                value={smtpPassword}
                onChange={(e) => setSmtpPassword(e.target.value)}
                placeholder={
                  form.smtp_password_configured
                    ? "•••••••• (déjà enregistré)"
                    : "App Password / mot de passe"
                }
                autoComplete="new-password"
              />
            </label>
            <label className="field">
              <span>Adresse expéditeur (optionnel)</span>
              <input
                value={form.from_email}
                onChange={(e) =>
                  setForm({ ...form, from_email: e.target.value })
                }
                placeholder="laisser vide = identifiant SMTP"
              />
              <span className="muted small">
                Affichage automatique :{" "}
                <code>
                  {form.effective_from_email ||
                    "NOREPLY Nom filiale &lt;adresse&gt;"}
                </code>
              </span>
            </label>
            <label className="field">
              <span>Répondre à (optionnel)</span>
              <input
                type="email"
                value={form.reply_to}
                onChange={(e) => setForm({ ...form, reply_to: e.target.value })}
              />
            </label>
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.smtp_use_tls}
                onChange={(e) =>
                  setForm({
                    ...form,
                    smtp_use_tls: e.target.checked,
                    smtp_use_ssl: false,
                    smtp_port: e.target.checked ? 587 : form.smtp_port,
                  })
                }
              />
              <span>TLS / STARTTLS (port 587 — Gmail, Outlook…)</span>
            </label>
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.smtp_use_ssl}
                onChange={(e) =>
                  setForm({
                    ...form,
                    smtp_use_ssl: e.target.checked,
                    smtp_use_tls: false,
                    smtp_port: e.target.checked ? 465 : form.smtp_port,
                  })
                }
              />
              <span>SSL (port 465)</span>
            </label>
          </div>

          <h3 className="section-subtitle" style={{ marginTop: 24 }}>
            Activation des alertes de circuit
          </h3>
          <div className="form-grid">
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(e) =>
                  setForm({ ...form, enabled: e.target.checked })
                }
              />
              <span>Notifications actives pour cette filiale</span>
            </label>
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.notify_on_step}
                onChange={(e) =>
                  setForm({ ...form, notify_on_step: e.target.checked })
                }
                disabled={!form.enabled}
              />
              <span>
                Alerter les utilisateurs de l’étape suivante (action à faire)
              </span>
            </label>
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.notify_on_completion}
                onChange={(e) =>
                  setForm({ ...form, notify_on_completion: e.target.checked })
                }
                disabled={!form.enabled}
              />
              <span>
                Informer l’initiateur (et les intervenants) quand le dossier est
                validé — rappel de générer les contrats
              </span>
            </label>
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.notify_on_rejection}
                onChange={(e) =>
                  setForm({ ...form, notify_on_rejection: e.target.checked })
                }
                disabled={!form.enabled}
              />
              <span>
                Informer l’initiateur (et les intervenants) en cas de rejet
              </span>
            </label>
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.notify_on_return}
                onChange={(e) =>
                  setForm({ ...form, notify_on_return: e.target.checked })
                }
                disabled={!form.enabled}
              />
              <span>
                Informer l’initiateur (et les intervenants) en cas de renvoi
                pour correction
              </span>
            </label>
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.notify_collection_email}
                onChange={(e) =>
                  setForm({
                    ...form,
                    notify_collection_email: e.target.checked,
                  })
                }
                disabled={!form.enabled}
              />
              <span>
                Relances recouvrement automatiques par e-mail (actions dues)
              </span>
            </label>
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.notify_collection_sms}
                onChange={(e) =>
                  setForm({
                    ...form,
                    notify_collection_sms: e.target.checked,
                  })
                }
                disabled={!form.enabled}
              />
              <span>
                Relances recouvrement SMS (stub — journalisé, non envoyé)
              </span>
            </label>
            <label className="field checkbox-field">
              <input
                type="checkbox"
                checked={form.cc_tenant_email}
                onChange={(e) =>
                  setForm({ ...form, cc_tenant_email: e.target.checked })
                }
                disabled={!form.enabled}
              />
              <span>Mettre l’e-mail de la filiale en copie</span>
            </label>
          </div>

          {error && <div className="form-error">{error}</div>}
          {saved && (
            <div className="form-success" style={{ marginBottom: 12 }}>
              Paramètres enregistrés.
            </div>
          )}
          <button className="btn btn-primary" disabled={save.isPending}>
            Enregistrer
          </button>
        </form>
      )}

      <div className="card form-card" style={{ marginTop: 20 }}>
        <h3 className="section-subtitle">
          <Send size={16} /> Tester l&apos;envoi
        </h3>
        <div className="form-grid">
          <label className="field">
            <span>Destinataire du test</span>
            <input
              type="email"
              value={testTo}
              onChange={(e) => setTestTo(e.target.value)}
              placeholder="vous@exemple.com"
            />
          </label>
        </div>
        {testMsg && (
          <div className="form-success" style={{ marginBottom: 12 }}>
            {testMsg}
          </div>
        )}
        <button
          type="button"
          className="btn btn-ghost"
          disabled={testMail.isPending || !testTo.trim()}
          onClick={() => {
            setError(null);
            setTestMsg(null);
            testMail.mutate();
          }}
        >
          Envoyer un e-mail de test
        </button>
      </div>

      <h3 className="section-subtitle" style={{ marginTop: 28 }}>
        Journal des envois récents
      </h3>
      {logs.isLoading || !logs.data ? (
        <Spinner />
      ) : logs.data.results.length === 0 ? (
        <EmptyState message="Aucun e-mail journalisé pour le moment." />
      ) : (
        <table className="table card">
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Sujet</th>
              <th>Destinataires</th>
              <th>Statut</th>
            </tr>
          </thead>
          <tbody>
            {logs.data.results.map((l) => (
              <tr key={l.id}>
                <td className="muted small">{formatDate(l.created_at)}</td>
                <td>{l.kind_display || l.kind}</td>
                <td>{l.subject}</td>
                <td className="muted small">
                  {(l.recipients || []).join(", ") || "—"}
                </td>
                <td>
                  <Badge value={l.status} label={l.status_display || l.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

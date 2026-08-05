import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Banknote,
  Gavel,
  HandCoins,
  Landmark,
  MessageSquareText,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type {
  ApprovalTask,
  Client,
  DationRequest,
  Guarantee,
  Paginated,
} from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { ClientAutocomplete } from "@/components/ClientAutocomplete";
import { DecisionPanel } from "@/components/DecisionPanel";
import {
  Badge,
  Card,
  EmptyState,
  PageHeader,
  PaginationBar,
  Spinner,
  formatDate,
  formatMoney,
} from "@/components/ui";

function hasPerm(
  user: { permissions?: string[]; is_superuser?: boolean } | null,
  perm: string,
) {
  if (!user) return false;
  if (user.is_superuser) return true;
  return (user.permissions ?? []).includes(perm);
}

type ExtraAsset = { key: string; description: string; value: string };

type CbsPreview = {
  cbs_client_id: string;
  total_outstanding: string;
  currency: string;
  breakdown: unknown[];
};

export function DationsPage() {
  const { user } = useAuth();
  const canInitiate = hasPerm(user, "guarantees.initiate_dationrequest");
  const [page, setPage] = useState(1);

  const list = useQuery({
    queryKey: ["dation-requests", page],
    queryFn: async () =>
      (
        await api.get<Paginated<DationRequest>>("/dation-requests/", {
          params: { page },
        })
      ).data,
  });

  return (
    <div>
      <PageHeader
        icon={HandCoins}
        title="Dations en paiement"
        subtitle="Processus dédié avec contrôle CBS (créance client) et circuit paramétrable"
        actions={
          canInitiate ? (
            <Link className="btn btn-primary" to="/dations/nouvelle">
              <Plus />
              Nouvelle dation
            </Link>
          ) : undefined
        }
      />

      {list.isLoading || !list.data ? (
        <Spinner />
      ) : list.data.results.length === 0 ? (
        <EmptyState message="Aucune demande de dation en paiement." />
      ) : (
        <>
        <table className="table card">
          <thead>
            <tr>
              <th>Référence</th>
              <th>Client</th>
              <th>Créance CBS</th>
              <th>Valeur biens</th>
              <th>Couverture</th>
              <th>Statut</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {list.data.results.map((r) => (
              <tr key={r.id}>
                <td>
                  <code>{r.reference || "—"}</code>
                </td>
                <td>{r.client_display}</td>
                <td className="num">
                  {formatMoney(r.cbs_total_outstanding, r.cbs_currency || "XAF")}
                </td>
                <td className="num">
                  {formatMoney(
                    r.assets_total_value ?? r.asset_value,
                    r.cbs_currency || "XAF",
                  )}
                </td>
                <td>
                  {r.covers_claim == null ? (
                    "—"
                  ) : r.covers_claim ? (
                    <Badge value="OK" label="Couvre" />
                  ) : (
                    <Badge value="WARN" label="Insuffisant" />
                  )}
                </td>
                <td>
                  <Badge value={r.status} label={r.status_display} />
                </td>
                <td>
                  <Link className="btn btn-ghost btn-sm" to={`/dations/${r.id}`}>
                    Ouvrir
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <PaginationBar
          page={page}
          count={list.data.count}
          onPageChange={setPage}
        />
        </>
      )}
    </div>
  );
}

export function DationNewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [clientId, setClientId] = useState("");
  const [cbsClientId, setCbsClientId] = useState("");
  const [selectedGuaranteeIds, setSelectedGuaranteeIds] = useState<string[]>(
    [],
  );
  const [extraAssets, setExtraAssets] = useState<ExtraAsset[]>([]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const guarantees = useQuery({
    queryKey: ["guarantees", "for-dation", clientId],
    queryFn: async () =>
      (
        await api.get<Paginated<Guarantee>>("/guarantees/", {
          params: { client: clientId, status: "ACTIVE", page_size: 200 },
        })
      ).data,
    enabled: !!clientId,
  });

  const cbsPreview = useQuery({
    queryKey: ["dation-cbs-preview", cbsClientId],
    queryFn: async () =>
      (
        await api.get<CbsPreview>("/dation-requests/preview-cbs/", {
          params: { cbs_client_id: cbsClientId },
        })
      ).data,
    enabled: !!cbsClientId.trim(),
    retry: false,
  });

  const currency = cbsPreview.data?.currency || "XAF";
  const claim = Number(cbsPreview.data?.total_outstanding || 0);

  const selectedTotal = useMemo(() => {
    const fromGuarantees = (guarantees.data?.results ?? [])
      .filter((g) => selectedGuaranteeIds.includes(g.id))
      .reduce(
        (sum, g) =>
          sum +
          Number(
            g.current_value || g.value_to_consider || g.expertise_value || 0,
          ),
        0,
      );
    const fromExtra = extraAssets.reduce(
      (sum, a) => sum + Number(a.value || 0),
      0,
    );
    return fromGuarantees + fromExtra;
  }, [guarantees.data, selectedGuaranteeIds, extraAssets]);

  const covers =
    cbsPreview.data != null ? selectedTotal >= claim && claim > 0 : null;
  const coverageRatio =
    claim > 0 ? Math.min(100, (selectedTotal / claim) * 100) : 0;
  const selectedCount =
    selectedGuaranteeIds.length +
    extraAssets.filter((a) => a.description.trim()).length;
  const canSubmit =
    !!clientId &&
    !!cbsClientId.trim() &&
    (selectedGuaranteeIds.length > 0 ||
      extraAssets.some((a) => a.description.trim()));

  const create = useMutation({
    mutationFn: async () =>
      (
        await api.post<DationRequest>("/dation-requests/", {
          client: clientId,
          cbs_client_id: cbsClientId,
          guarantee_ids: selectedGuaranteeIds,
          additional_assets: extraAssets
            .filter((a) => a.description.trim())
            .map((a) => ({
              description: a.description.trim(),
              value: a.value || null,
            })),
          comment,
        })
      ).data,
    onSuccess: (data) => navigate(`/dations/${data.id}`),
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: unknown } })?.response?.data;
      const raw =
        data && typeof data === "object" && "errors" in data
          ? (data as { errors: unknown }).errors
          : data;
      setError(
        typeof raw === "string"
          ? raw
          : Array.isArray(raw)
            ? raw.map(String).join(" · ")
            : "Initiation impossible (contrôle CBS, biens ou circuit manquant).",
      );
    },
  });

  function onClientPicked(id: string, _label: string, client?: Client | null) {
    setClientId(id);
    setSelectedGuaranteeIds([]);
    setExtraAssets([]);
    setError(null);
    // Matricule Core Banking saisi à la création du client.
    setCbsClientId((client?.cbs_client_id || "").trim());
  }

  function toggleGuarantee(id: string) {
    setSelectedGuaranteeIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  if (!hasPerm(user, "guarantees.initiate_dationrequest")) {
    return (
      <div>
        <PageHeader icon={HandCoins} title="Nouvelle dation" />
        <EmptyState message="Vous n'avez pas le droit d'initier une dation en paiement." />
      </div>
    );
  }

  const coverageTone =
    covers == null ? "idle" : covers ? "ok" : selectedTotal > 0 ? "warn" : "idle";

  return (
    <div className="dation-compose">
      <PageHeader
        icon={HandCoins}
        title="Nouvelle dation en paiement"
        subtitle="Garanties Fin Flow du client + créance CBS (matricule Core Banking)"
        actions={
          <Link className="btn btn-ghost" to="/dations">
            <ArrowLeft />
            Retour
          </Link>
        }
      />

      <form
        className="dation-compose-form"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          setError(null);
          if (!clientId) {
            setError("Sélectionnez un client dans les suggestions.");
            return;
          }
          if (!cbsClientId.trim()) {
            setError(
              "Ce client n’a pas de matricule Core Banking. Renseignez-le sur la fiche client.",
            );
            return;
          }
          if (!canSubmit) {
            setError(
              "Choisissez au moins une garantie existante ou ajoutez un bien.",
            );
            return;
          }
          create.mutate();
        }}
      >
        <div className="dation-compose-layout">
          <div className="dation-compose-main">
            <section className="card form-section">
              <div className="card-title form-section-head">
                <span className="form-section-icon">
                  <UserRound size={18} />
                </span>
                <div className="form-section-heading">
                  <span className="form-section-title">1. Client</span>
                  <span className="form-section-desc">
                    Saisissez pour trouver le client. Le matricule Core Banking
                    est repris automatiquement ; la créance vient du CBS, les
                    garanties de Fin Flow.
                  </span>
                </div>
              </div>
              <div className="form-grid">
                <label className="field" style={{ gridColumn: "1 / -1" }}>
                  <span>Client</span>
                  <ClientAutocomplete
                    value={clientId}
                    onChange={onClientPicked}
                    required
                  />
                </label>
                <div className="field">
                  <span>Matricule Core Banking (CBS)</span>
                  <div
                    className={`dation-cbs-matricule${cbsClientId ? "" : " missing"}`}
                  >
                    {clientId ? (
                      cbsClientId ? (
                        <code>{cbsClientId}</code>
                      ) : (
                        <span className="muted">
                          Non renseigné sur la fiche client
                        </span>
                      )
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </div>
                </div>
              </div>
              {clientId && !cbsClientId && (
                <p className="form-error" style={{ marginTop: 10 }}>
                  Impossible d’interroger le CBS sans matricule. Complétez le
                  champ « Matricule du client (Core Banking) » sur la fiche
                  client.
                </p>
              )}
            </section>

            {!clientId ? (
              <section className="card form-section dation-compose-empty">
                <HandCoins size={28} />
                <p>
                  Recherchez un client pour charger ses garanties Fin Flow et
                  la créance CBS.
                </p>
              </section>
            ) : (
              <>
                <section className="card form-section">
                  <div className="card-title form-section-head">
                    <span className="form-section-icon">
                      <ShieldCheck size={18} />
                    </span>
                    <div className="form-section-heading">
                      <span className="form-section-title">
                        2. Garanties Fin Flow
                      </span>
                      <span className="form-section-desc">
                        Garanties actives déjà enregistrées pour ce client dans
                        Fin Flow — cochez celles à intégrer.
                      </span>
                    </div>
                    <div className="form-section-action">
                      <span className="muted small">
                        {selectedGuaranteeIds.length} sélectionnée
                        {selectedGuaranteeIds.length > 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>

                  {guarantees.isLoading ? (
                    <Spinner />
                  ) : (guarantees.data?.results ?? []).length === 0 ? (
                    <EmptyState message="Aucune garantie active pour ce client dans Fin Flow." />
                  ) : (
                    <div className="dation-guarantee-list" role="list">
                      {(guarantees.data?.results ?? []).map((g) => {
                        const checked = selectedGuaranteeIds.includes(g.id);
                        const val =
                          g.current_value ||
                          g.value_to_consider ||
                          g.expertise_value;
                        return (
                          <label
                            key={g.id}
                            role="listitem"
                            className={`dation-guarantee-row${checked ? " selected" : ""}`}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleGuarantee(g.id)}
                            />
                            <span className="dation-guarantee-body">
                              <span className="dation-guarantee-title">
                                {g.type_display}
                                <code>
                                  {g.reference || g.id.slice(0, 8)}
                                </code>
                              </span>
                              {g.description && (
                                <span className="dation-guarantee-desc">
                                  {g.description.slice(0, 140)}
                                </span>
                              )}
                            </span>
                            <span className="dation-guarantee-meta">
                              <strong>{formatMoney(val, currency)}</strong>
                              <Badge value={g.status} />
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </section>

                <section className="card form-section">
                  <div className="card-title form-section-head">
                    <span className="form-section-icon">
                      <Landmark size={18} />
                    </span>
                    <div className="form-section-heading">
                      <span className="form-section-title">
                        3. Biens additionnels
                      </span>
                      <span className="form-section-desc">
                        Ajoutez d’autres biens non encore enregistrés comme
                        garanties dans Fin Flow.
                      </span>
                    </div>
                    <div className="form-section-action">
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() =>
                          setExtraAssets((prev) => [
                            ...prev,
                            {
                              key: `${Date.now()}-${prev.length}`,
                              description: "",
                              value: "",
                            },
                          ])
                        }
                      >
                        <Plus size={14} />
                        Ajouter
                      </button>
                    </div>
                  </div>

                  {extraAssets.length === 0 ? (
                    <p className="muted small dation-compose-hint">
                      Optionnel si des garanties Fin Flow sont déjà
                      sélectionnées.
                    </p>
                  ) : (
                    <div className="dation-extra-list">
                      {extraAssets.map((asset, idx) => (
                        <div key={asset.key} className="dation-extra-row">
                          <label className="field">
                            <span>Description du bien</span>
                            <input
                              value={asset.description}
                              onChange={(e) => {
                                const v = e.target.value;
                                setExtraAssets((prev) =>
                                  prev.map((a, i) =>
                                    i === idx ? { ...a, description: v } : a,
                                  ),
                                );
                              }}
                              required
                              placeholder="Ex. terrain, véhicule, équipement…"
                            />
                          </label>
                          <label className="field">
                            <span>Valeur</span>
                            <input
                              type="number"
                              min={0}
                              step="0.01"
                              value={asset.value}
                              onChange={(e) => {
                                const v = e.target.value;
                                setExtraAssets((prev) =>
                                  prev.map((a, i) =>
                                    i === idx ? { ...a, value: v } : a,
                                  ),
                                );
                              }}
                            />
                          </label>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm dation-extra-remove"
                            onClick={() =>
                              setExtraAssets((prev) =>
                                prev.filter((_, i) => i !== idx),
                              )
                            }
                            aria-label="Retirer ce bien"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section className="card form-section">
                  <div className="card-title form-section-head">
                    <span className="form-section-icon">
                      <MessageSquareText size={18} />
                    </span>
                    <div className="form-section-heading">
                      <span className="form-section-title">4. Commentaire</span>
                      <span className="form-section-desc">
                        Contexte libre pour le circuit de validation.
                      </span>
                    </div>
                  </div>
                  <label className="field">
                    <span>Note</span>
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      rows={3}
                      placeholder="Motif, précisions sur les biens, observations…"
                    />
                  </label>
                </section>
              </>
            )}
          </div>

          <aside className="dation-compose-aside">
            <div className={`dation-coverage panel tone-${coverageTone}`}>
              <div className="dation-coverage-head">
                <Banknote size={18} />
                <strong>Créance CBS</strong>
              </div>

              {!clientId ? (
                <p className="muted small">
                  Sélectionnez un client pour interroger le CBS.
                </p>
              ) : !cbsClientId.trim() ? (
                <p className="muted small">
                  Matricule Core Banking manquant sur la fiche client.
                </p>
              ) : cbsPreview.isFetching ? (
                <p className="muted small">Interrogation du Core Banking…</p>
              ) : cbsPreview.isError ? (
                <p className="form-error" style={{ margin: 0 }}>
                  Encours CBS indisponible pour le matricule{" "}
                  <code>{cbsClientId}</code>.
                </p>
              ) : cbsPreview.data ? (
                <>
                  <p className="muted small" style={{ marginTop: 0 }}>
                    Matricule CBS <code>{cbsClientId}</code>
                  </p>
                  <div className="dation-coverage-metrics">
                    <div>
                      <span className="label">Créance (CBS)</span>
                      <strong>
                        {formatMoney(
                          cbsPreview.data.total_outstanding,
                          currency,
                        )}
                      </strong>
                    </div>
                    <div>
                      <span className="label">Biens retenus (Fin Flow)</span>
                      <strong>{formatMoney(selectedTotal, currency)}</strong>
                    </div>
                  </div>

                  <div
                    className="dation-coverage-bar"
                    role="meter"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.round(coverageRatio)}
                    aria-label="Taux de couverture de la créance"
                  >
                    <span
                      className="dation-coverage-fill"
                      style={{ width: `${coverageRatio}%` }}
                    />
                  </div>

                  <p className="dation-coverage-status">
                    {covers == null
                      ? "—"
                      : covers
                        ? "Les biens couvrent la créance."
                        : `Manque ${formatMoney(claim - selectedTotal, currency)}.`}
                  </p>
                  <p className="muted small">
                    {selectedCount} bien{selectedCount > 1 ? "s" : ""} dans le
                    dossier
                  </p>
                </>
              ) : null}
            </div>

            {error && <div className="form-error">{error}</div>}

            <div className="dation-compose-actions">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={create.isPending || !canSubmit}
              >
                {create.isPending
                  ? "Vérification CBS…"
                  : "Vérifier CBS et démarrer le circuit"}
              </button>
              <Link className="btn btn-ghost" to="/dations">
                Annuler
              </Link>
            </div>
          </aside>
        </div>
      </form>
    </div>
  );
}

export function DationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();

  const detail = useQuery({
    queryKey: ["dation-request", id],
    queryFn: async () =>
      (await api.get<DationRequest>(`/dation-requests/${id}/`)).data,
    enabled: !!id,
  });

  const workflow = useQuery({
    queryKey: ["dation-workflow", id],
    queryFn: async () =>
      (
        await api.get<{
          instance: { status: string; definition?: string } | null;
        }>(`/dation-requests/${id}/workflow/`)
      ).data,
    enabled: !!id,
  });

  const { data: myTasks } = useQuery({
    queryKey: ["my-pending-tasks"],
    queryFn: async () =>
      (await api.get<Paginated<ApprovalTask>>("/approval-tasks/my_pending/"))
        .data,
  });

  const retry = useMutation({
    mutationFn: async () =>
      (await api.post(`/dation-requests/${id}/retry_cbs/`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dation-request", id] });
      qc.invalidateQueries({ queryKey: ["guarantees"] });
    },
  });

  if (detail.isLoading || !detail.data) return <Spinner />;
  const r = detail.data;
  const cur = r.cbs_currency || "XAF";
  const myTask =
    myTasks?.results.find(
      (t) => t.target_meta?.kind === "DATION" && t.target_meta.id === r.id,
    ) ?? null;

  return (
    <div>
      <PageHeader
        icon={HandCoins}
        title={r.reference || "Dation en paiement"}
        subtitle={r.client_display}
        actions={
          <div className="row-actions">
            <Link className="btn btn-ghost" to="/dations">
              <ArrowLeft />
              Retour
            </Link>
            {r.status === "BLOCKED" && (
              <button
                className="btn btn-primary"
                onClick={() => retry.mutate()}
                disabled={retry.isPending}
              >
                <RefreshCw size={16} />
                Retenter CBS
              </button>
            )}
          </div>
        }
      />

      <div className="detail-grid">
        <Card title="Demande">
          <dl className="def-list two">
            <div>
              <dt>Statut</dt>
              <dd>
                <Badge value={r.status} label={r.status_display} />
              </dd>
            </div>
            <div>
              <dt>Client</dt>
              <dd>
                <Link to={`/clients/${r.client}`}>{r.client_display}</Link>
              </dd>
            </div>
            <div>
              <dt>ID client CBS</dt>
              <dd>
                <code>{r.cbs_client_id || "—"}</code>
              </dd>
            </div>
            <div>
              <dt>Créance CBS</dt>
              <dd>{formatMoney(r.cbs_total_outstanding, cur)}</dd>
            </div>
            <div>
              <dt>Valeur totale des biens</dt>
              <dd>
                {formatMoney(r.assets_total_value ?? r.asset_value, cur)}
              </dd>
            </div>
            <div>
              <dt>Couverture</dt>
              <dd>
                {r.covers_claim == null ? (
                  "—"
                ) : r.covers_claim ? (
                  <Badge value="OK" label="Couvre la créance" />
                ) : (
                  <Badge
                    value="WARN"
                    label={`Écart ${formatMoney(r.coverage_gap ?? null, cur)}`}
                  />
                )}
              </dd>
            </div>
            <div>
              <dt>Vérifié le</dt>
              <dd>{r.cbs_checked_at ? formatDate(r.cbs_checked_at) : "—"}</dd>
            </div>
            {r.resulting_guarantee && (
              <div>
                <dt>Garantie créée</dt>
                <dd>
                  <Link to={`/garanties/${r.resulting_guarantee}`}>
                    Voir la garantie
                  </Link>
                </dd>
              </div>
            )}
          </dl>
        </Card>

        <Card title="Biens du dossier">
          {(r.assets ?? []).length === 0 ? (
            <p>{r.asset_description || "—"}</p>
          ) : (
            <ul className="link-list">
              {r.assets!.map((a) => (
                <li key={a.id}>
                  <span>
                    <ShieldCheck size={14} />{" "}
                    {a.source_display}
                    {a.guarantee_reference && (
                      <code className="muted">
                        {" "}
                        {a.guarantee_reference}
                      </code>
                    )}
                    <em className="muted small"> — {a.description}</em>
                  </span>
                  <span className="num">
                    {formatMoney(a.value, cur)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {myTask && (
          <Card title={`Décision — ${myTask.step_name}`}>
            <div className="card-title-icon">
              <Gavel size={16} />
            </div>
            <DecisionPanel task={myTask} />
          </Card>
        )}

        <Card title="Circuit">
          {!workflow.data?.instance ? (
            <EmptyState message="Aucun circuit associé." />
          ) : (
            <dl className="def-list two">
              <div>
                <dt>Statut circuit</dt>
                <dd>
                  <Badge value={workflow.data.instance.status} />
                </dd>
              </div>
            </dl>
          )}
        </Card>
      </div>
    </div>
  );
}

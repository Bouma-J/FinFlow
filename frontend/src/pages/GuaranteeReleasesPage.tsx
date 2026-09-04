import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Banknote,
  FileUp,
  Gavel,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShieldOff,
  Unlock,
  UserRound,
} from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type {
  ApprovalTask,
  Client,
  GedDocument,
  GuaranteeReleaseRequest,
  Paginated,
  ReleaseClientContext,
  ReleaseClientCredit,
} from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
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

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

export function GuaranteeReleasesPage() {
  const { user } = useAuth();
  const canInitiate = hasPerm(
    user,
    "guarantees.initiate_guaranteereleaserequest",
  );
  const [page, setPage] = useState(1);

  const list = useQuery({
    queryKey: ["guarantee-releases", page],
    queryFn: async () =>
      (
        await api.get<Paginated<GuaranteeReleaseRequest>>("/guarantee-releases/", {
          params: { page },
        })
      ).data,
  });

  return (
    <div>
      <PageHeader
        icon={ShieldOff}
        title="Mains levées"
        subtitle="Brouillon → demande client → acte généré/signé → circuit CBS"
        actions={
          canInitiate ? (
            <Link className="btn btn-primary" to="/mains-levees/nouvelle">
              <Plus />
              Nouvelle main levée
            </Link>
          ) : undefined
        }
      />

      {list.isLoading || !list.data ? (
        <Spinner />
      ) : list.data.results.length === 0 ? (
        <EmptyState message="Aucune demande de main levée." />
      ) : (
        <>
        <table className="table card">
          <thead>
            <tr>
              <th>Référence</th>
              <th>Garantie</th>
              <th>Client</th>
              <th>Date demande</th>
              <th>Réf. prêt CBS</th>
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
                <td>{r.guarantee_reference || r.guarantee.slice(0, 8)}</td>
                <td>{r.client_display}</td>
                <td>{r.request_date ? formatDate(r.request_date) : "—"}</td>
                <td className="muted small">{r.cbs_loan_reference || "—"}</td>
                <td>
                  <Badge value={r.status} label={r.status_display} />
                </td>
                <td>
                  <Link
                    className="btn btn-ghost btn-sm"
                    to={`/mains-levees/${r.id}`}
                  >
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

export function GuaranteeReleaseNewPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [clientId, setClientId] = useState("");
  const [cbsClientId, setCbsClientId] = useState("");
  const [guaranteeId, setGuaranteeId] = useState("");
  const [selectedCreditKey, setSelectedCreditKey] = useState("");
  const [requestDate, setRequestDate] = useState(todayISO());
  const [releaseFees, setReleaseFees] = useState("");
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const context = useQuery({
    queryKey: ["release-client-context", clientId],
    queryFn: async () =>
      (
        await api.get<ReleaseClientContext>(
          "/guarantee-releases/client-context/",
          { params: { client: clientId } },
        )
      ).data,
    enabled: !!clientId,
    retry: false,
  });

  const selectedCredit: ReleaseClientCredit | null = useMemo(() => {
    const credits = context.data?.credits ?? [];
    return credits.find((c) => creditKey(c) === selectedCreditKey) ?? null;
  }, [context.data, selectedCreditKey]);

  const settledCredits = (context.data?.credits ?? []).filter(
    (c) => c.cbs_settled === true,
  );

  const canSubmit =
    !!clientId &&
    !!cbsClientId.trim() &&
    !!guaranteeId &&
    !!selectedCredit?.cbs_loan_reference &&
    selectedCredit.cbs_settled === true &&
    !!requestDate;

  const create = useMutation({
    mutationFn: async () =>
      (
        await api.post<GuaranteeReleaseRequest>("/guarantee-releases/", {
          guarantee: guaranteeId,
          loan: selectedCredit?.loan_id || null,
          cbs_loan_reference: selectedCredit?.cbs_loan_reference || "",
          cbs_client_id: cbsClientId,
          request_date: requestDate,
          release_fees: releaseFees || null,
          as_draft: true,
          comment,
        })
      ).data,
    onSuccess: (data) => navigate(`/mains-levees/${data.id}`),
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
            : "Création impossible (prêt non soldé, CBS ou circuit manquant).",
      );
    },
  });

  function onClientPicked(id: string, _label: string, client?: Client | null) {
    setClientId(id);
    setCbsClientId((client?.cbs_client_id || "").trim());
    setGuaranteeId("");
    setSelectedCreditKey("");
    setError(null);
  }

  if (!hasPerm(user, "guarantees.initiate_guaranteereleaserequest")) {
    return (
      <div>
        <PageHeader icon={ShieldOff} title="Nouvelle main levée" />
        <EmptyState message="Vous n'avez pas le droit d'initier une main levée." />
      </div>
    );
  }

  const guarantees = context.data?.guarantees ?? [];
  const credits = context.data?.credits ?? [];
  const currency = selectedCredit?.cbs_currency || "XOF";

  return (
    <div className="page-shell release-compose">
      <PageHeader
        icon={ShieldOff}
        title="Nouvelle main levée"
        subtitle="Garanties Fin Flow + crédits CBS du client (libération si prêt soldé)"
        actions={
          <Link className="btn btn-ghost" to="/mains-levees">
            <ArrowLeft />
            Retour
          </Link>
        }
      />

      <form
        className="release-compose-form"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          setError(null);
          if (!clientId) {
            setError("Sélectionnez un client.");
            return;
          }
          if (!cbsClientId.trim()) {
            setError(
              "Matricule Core Banking manquant sur la fiche client.",
            );
            return;
          }
          if (!guaranteeId) {
            setError("Choisissez la garantie à libérer.");
            return;
          }
          if (!selectedCredit || selectedCredit.cbs_settled !== true) {
            setError(
              "Sélectionnez un crédit soldé dans le CBS pour autoriser la main levée.",
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
                    Recherchez le client. Le matricule CBS est repris de la
                    fiche ; les garanties et crédits sont chargés
                    automatiquement.
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
            </section>

            {!clientId ? (
              <section className="card form-section dation-compose-empty">
                <ShieldOff size={28} />
                <p>
                  Recherchez un client pour afficher ses garanties Fin Flow et
                  ses crédits avec statut CBS.
                </p>
              </section>
            ) : context.isLoading ? (
              <Spinner />
            ) : context.isError ? (
              <div className="form-error">
                Impossible de charger le contexte client.
              </div>
            ) : (
              <>
                <section className="card form-section">
                  <div className="card-title form-section-head">
                    <span className="form-section-icon">
                      <ShieldCheck size={18} />
                    </span>
                    <div className="form-section-heading">
                      <span className="form-section-title">
                        2. Garantie à libérer
                      </span>
                      <span className="form-section-desc">
                        Garanties actives Fin Flow disponibles pour ce client.
                      </span>
                    </div>
                  </div>
                  {guarantees.length === 0 ? (
                    <EmptyState message="Aucune garantie active disponible." />
                  ) : (
                    <div className="dation-guarantee-list" role="list">
                      {guarantees.map((g) => {
                        const checked = guaranteeId === g.id;
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
                              type="radio"
                              name="release-guarantee"
                              checked={checked}
                              onChange={() => setGuaranteeId(g.id)}
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
                              <strong>
                                {formatMoney(val, currency)}
                              </strong>
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
                      <Banknote size={18} />
                    </span>
                    <div className="form-section-heading">
                      <span className="form-section-title">
                        3. Crédits & statut CBS
                      </span>
                      <span className="form-section-desc">
                        Sélectionnez le crédit soldé dans le CBS justifiant la
                        main levée.
                      </span>
                    </div>
                    <div className="form-section-action">
                      <span className="muted small">
                        {settledCredits.length} soldé
                        {settledCredits.length > 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                  {credits.length === 0 ? (
                    <EmptyState message="Aucun dossier / prêt pour ce client." />
                  ) : (
                    <div className="release-credit-list" role="list">
                      {credits.map((c) => {
                        const key = creditKey(c);
                        const checked = selectedCreditKey === key;
                        const settled = c.cbs_settled === true;
                        return (
                          <label
                            key={key}
                            role="listitem"
                            className={`release-credit-row${checked ? " selected" : ""}${settled ? " settled" : " active-loan"}`}
                          >
                            <input
                              type="radio"
                              name="release-credit"
                              checked={checked}
                              disabled={!settled || !c.cbs_loan_reference}
                              onChange={() => setSelectedCreditKey(key)}
                            />
                            <span className="release-credit-body">
                              <span className="dation-guarantee-title">
                                {c.application_reference}
                                {c.product_label && (
                                  <span className="muted small">
                                    {" "}
                                    — {c.product_label}
                                  </span>
                                )}
                              </span>
                              <span className="dation-guarantee-desc">
                                Dossier {c.application_status_display}
                                {c.loan_status_display
                                  ? ` · Prêt Fin Flow : ${c.loan_status_display}`
                                  : " · Pas de prêt local"}
                                {c.cbs_loan_reference
                                  ? ` · CBS ${c.cbs_loan_reference}`
                                  : " · Réf. CBS manquante"}
                              </span>
                              {c.cbs_error && (
                                <span className="form-error small">
                                  {c.cbs_error}
                                </span>
                              )}
                            </span>
                            <span className="dation-guarantee-meta">
                              <strong>
                                {formatMoney(c.amount, c.currency)}
                              </strong>
                              <Badge
                                value={
                                  c.cbs_settled === true
                                    ? "OK"
                                    : c.cbs_settled === false
                                      ? "WARN"
                                      : "DRAFT"
                                }
                                label={c.cbs_status_label}
                              />
                              {c.cbs_settled === false &&
                                c.cbs_outstanding != null && (
                                  <span className="muted small">
                                    Encours{" "}
                                    {formatMoney(
                                      c.cbs_outstanding,
                                      c.cbs_currency,
                                    )}
                                  </span>
                                )}
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
                      <Unlock size={18} />
                    </span>
                    <div className="form-section-heading">
                      <span className="form-section-title">
                        4. Informations de la demande
                      </span>
                      <span className="form-section-desc">
                        Date, frais et commentaire pour le circuit.
                      </span>
                    </div>
                  </div>
                  <div className="form-grid">
                    <label className="field">
                      <span>Date de la demande</span>
                      <input
                        type="date"
                        value={requestDate}
                        onChange={(e) => setRequestDate(e.target.value)}
                        required
                      />
                    </label>
                    <label className="field">
                      <span>Frais de main levée</span>
                      <input
                        type="number"
                        min={0}
                        step="0.01"
                        value={releaseFees}
                        onChange={(e) => setReleaseFees(e.target.value)}
                        placeholder="Optionnel"
                      />
                    </label>
                    <label
                      className="field"
                      style={{ gridColumn: "1 / -1" }}
                    >
                      <span>Commentaire / motif</span>
                      <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        rows={3}
                        placeholder="Observations, pièces jointes à prévoir…"
                      />
                    </label>
                  </div>
                </section>
              </>
            )}
          </div>

          <aside className="dation-compose-aside">
            <div className="dation-coverage panel">
              <div className="dation-coverage-head">
                <Unlock size={18} />
                <strong>Récapitulatif</strong>
              </div>
              {!clientId ? (
                <p className="muted small">Sélectionnez un client.</p>
              ) : (
                <dl className="def-list">
                  <div>
                    <dt>Matricule CBS</dt>
                    <dd>
                      <code>{cbsClientId || "—"}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Garanties dispo.</dt>
                    <dd>{guarantees.length}</dd>
                  </div>
                  <div>
                    <dt>Crédits CBS</dt>
                    <dd>
                      {credits.length} dont {settledCredits.length} soldé
                      {settledCredits.length > 1 ? "s" : ""}
                    </dd>
                  </div>
                  <div>
                    <dt>Crédit retenu</dt>
                    <dd>
                      {selectedCredit
                        ? selectedCredit.application_reference
                        : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt>Prêt CBS</dt>
                    <dd>
                      {selectedCredit?.cbs_settled === true
                        ? "Soldé — main levée possible"
                        : selectedCredit
                          ? "Non soldé / non sélectionnable"
                          : "—"}
                    </dd>
                  </div>
                </dl>
              )}
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
                  : "Créer le brouillon"}
              </button>
              <Link className="btn btn-ghost" to="/mains-levees">
                Annuler
              </Link>
            </div>
          </aside>
        </div>
      </form>
    </div>
  );
}

function creditKey(c: ReleaseClientCredit) {
  return `${c.application_id}:${c.loan_id || "none"}:${c.cbs_loan_reference || ""}`;
}

export function GuaranteeReleaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { user } = useAuth();
  const canInitiate = hasPerm(
    user,
    "guarantees.initiate_guaranteereleaserequest",
  );

  const [demandeFile, setDemandeFile] = useState<File | null>(null);
  const [signedFile, setSignedFile] = useState<File | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const detail = useQuery({
    queryKey: ["guarantee-release", id],
    queryFn: async () =>
      (await api.get<GuaranteeReleaseRequest>(`/guarantee-releases/${id}/`))
        .data,
    enabled: !!id,
  });

  const docs = useQuery({
    queryKey: ["guarantee-release-docs", id],
    queryFn: async () =>
      (await api.get<GedDocument[]>(`/guarantee-releases/${id}/documents/`))
        .data,
    enabled: !!id,
  });

  const workflow = useQuery({
    queryKey: ["guarantee-release-workflow", id],
    queryFn: async () =>
      (
        await api.get<{
          instance: { status: string; definition_code?: string } | null;
        }>(`/guarantee-releases/${id}/workflow/`)
      ).data,
    enabled: !!id,
  });

  const { data: myTasks } = useQuery({
    queryKey: ["my-pending-tasks"],
    queryFn: async () =>
      (await api.get<Paginated<ApprovalTask>>("/approval-tasks/my_pending/"))
        .data,
  });

  function invalidateAll() {
    qc.invalidateQueries({ queryKey: ["guarantee-release", id] });
    qc.invalidateQueries({ queryKey: ["guarantee-release-docs", id] });
    qc.invalidateQueries({ queryKey: ["guarantee-release-workflow", id] });
    qc.invalidateQueries({ queryKey: ["guarantee-releases"] });
    qc.invalidateQueries({ queryKey: ["guarantees"] });
  }

  function errMsg(err: unknown, fallback: string) {
    const data = (err as { response?: { data?: unknown } })?.response?.data;
    const raw =
      data && typeof data === "object" && "errors" in data
        ? (data as { errors: unknown }).errors
        : data;
    if (typeof raw === "string") return raw;
    if (Array.isArray(raw)) return raw.map(String).join(" · ");
    return fallback;
  }

  const retry = useMutation({
    mutationFn: async () =>
      (await api.post(`/guarantee-releases/${id}/retry_cbs/`)).data,
    onSuccess: () => invalidateAll(),
    onError: (e) => setActionError(errMsg(e, "Échec retry CBS.")),
  });

  const submit = useMutation({
    mutationFn: async () =>
      (await api.post(`/guarantee-releases/${id}/submit/`)).data,
    onSuccess: () => {
      setActionError(null);
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Soumission impossible.")),
  });

  const cancel = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/guarantee-releases/${id}/cancel/`, {
          comment: "Annulé",
        })
      ).data,
    onSuccess: () => invalidateAll(),
    onError: (e) => setActionError(errMsg(e, "Annulation impossible.")),
  });

  const generateActe = useMutation({
    mutationFn: async () =>
      (await api.post(`/guarantee-releases/${id}/generate-acte/`)).data,
    onSuccess: () => invalidateAll(),
    onError: (e) => setActionError(errMsg(e, "Génération impossible.")),
  });

  const uploadDemande = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      if (demandeFile) fd.append("file", demandeFile);
      fd.append("name", demandeFile?.name || "Demande client");
      fd.append("category", "ML_DEMANDE");
      return (
        await api.post(`/guarantee-releases/${id}/documents/`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        })
      ).data;
    },
    onSuccess: () => {
      setDemandeFile(null);
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Upload demande impossible.")),
  });

  const uploadSigned = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      if (signedFile) fd.append("file", signedFile);
      return (
        await api.post(`/guarantee-releases/${id}/upload-acte-signe/`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        })
      ).data;
    },
    onSuccess: () => {
      setSignedFile(null);
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Dépôt acte signé impossible.")),
  });

  if (detail.isLoading || !detail.data) return <Spinner />;
  const r = detail.data;
  const cur = r.cbs_currency || "XOF";
  const editable = r.status === "DRAFT" || r.status === "RETURNED";
  const canUploadDocs = !["COMPLETED", "CANCELLED", "REJECTED"].includes(
    r.status,
  );
  const myTask =
    myTasks?.results.find(
      (t) =>
        t.target_meta?.kind === "MAIN_LEVEE" && t.target_meta.id === r.id,
    ) ?? null;
  const canDepositSigned =
    Boolean(r.can_deposit_signed_acte) || canInitiate || Boolean(myTask);
  return (
    <div>
      <PageHeader
        icon={Unlock}
        title={r.reference || "Main levée"}
        subtitle={r.client_display}
        actions={
          <div className="row-actions">
            <Link className="btn btn-ghost" to="/mains-levees">
              <ArrowLeft />
              Retour
            </Link>
            {canInitiate && editable && (
              <button
                className="btn btn-primary"
                onClick={() => submit.mutate()}
                disabled={submit.isPending}
              >
                Soumettre au circuit
              </button>
            )}
            {canInitiate && editable && (
              <button
                className="btn btn-ghost"
                onClick={() => cancel.mutate()}
                disabled={cancel.isPending}
              >
                Annuler
              </button>
            )}
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

      {actionError && <div className="form-error">{actionError}</div>}

      {r.status === "APPROVED" && !r.has_signed_acte && (
        <div className="form-error">
          Dossier approuvé : déposez l&apos;acte signé pour clôturer la main
          levée.
        </div>
      )}

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
              <dt>Garantie</dt>
              <dd>
                <Link to={`/garanties/${r.guarantee}`}>
                  {r.guarantee_reference || r.guarantee.slice(0, 8)}
                </Link>
              </dd>
            </div>
            <div>
              <dt>Réf. prêt CBS</dt>
              <dd>
                <code>{r.cbs_loan_reference || "—"}</code>
              </dd>
            </div>
            <div>
              <dt>Soldé CBS</dt>
              <dd>
                {r.cbs_settled == null ? "—" : r.cbs_settled ? "Oui" : "Non"}
              </dd>
            </div>
            <div>
              <dt>Frais</dt>
              <dd>
                {formatMoney(
                  r.release_fees ?? r.fees_client_total ?? null,
                  cur,
                )}
              </dd>
            </div>
            <div>
              <dt>Acte</dt>
              <dd>
                <Badge
                  value={r.acte_status || "NONE"}
                  label={r.acte_status_display || "Non généré"}
                />
              </dd>
            </div>
            <div>
              <dt>Demande client</dt>
              <dd>{r.has_client_demande ? "Jointe" : "Manquante"}</dd>
            </div>
            <div>
              <dt>Acte signé</dt>
              <dd>{r.has_signed_acte ? "Déposé" : "Manquant"}</dd>
            </div>
          </dl>
        </Card>

        <Card title="1. Demande client">
          <p className="muted small">
            Joindre la demande de main levée transmise par le client
            (obligatoire avant soumission).
          </p>
          {(docs.data ?? []).length > 0 && (
            <ul className="link-list">
              {(docs.data ?? []).map((d) => (
                <li key={d.id}>
                  <span>
                    <FileUp size={14} /> {d.name}
                    <em className="muted small"> · {d.category_label}</em>
                  </span>
                  <a
                    className="btn btn-ghost btn-sm"
                    href={d.file}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Ouvrir
                  </a>
                </li>
              ))}
            </ul>
          )}
          {canInitiate && canUploadDocs && (
            <div className="form-grid" style={{ marginTop: 12 }}>
              <label className="field">
                <span>Fichier demande</span>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) =>
                    setDemandeFile(e.target.files?.[0] ?? null)
                  }
                />
              </label>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={!demandeFile || uploadDemande.isPending}
                onClick={() => uploadDemande.mutate()}
              >
                <FileUp size={14} />
                Charger la demande
              </button>
            </div>
          )}
        </Card>

        <Card title="2. Acte de main levée">
          <p className="muted small">
            Générez l&apos;acte, faites-le signer, puis déposez le scan. L&apos;acte
            signé est obligatoire pour clôturer.
          </p>
          <dl className="def-list two">
            <div>
              <dt>Acte généré</dt>
              <dd>
                {r.acte_generated_url ? (
                  <a href={r.acte_generated_url} target="_blank" rel="noreferrer">
                    Télécharger
                  </a>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt>Acte signé</dt>
              <dd>
                {r.acte_signed_url ? (
                  <a href={r.acte_signed_url} target="_blank" rel="noreferrer">
                    Voir le dépôt
                  </a>
                ) : (
                  "—"
                )}
              </dd>
            </div>
          </dl>
          {canInitiate && canUploadDocs && (
            <div className="row-actions" style={{ marginTop: 12, gap: 8 }}>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={generateActe.isPending || r.has_signed_acte}
                onClick={() => generateActe.mutate()}
              >
                {r.has_generated_acte ? "Régénérer l'acte" : "Générer l'acte"}
              </button>
            </div>
          )}
          {canDepositSigned &&
            r.has_generated_acte &&
            !r.has_signed_acte &&
            canUploadDocs && (
              <div className="form-grid" style={{ marginTop: 12 }}>
                <label className="field">
                  <span>Acte signé (PDF / scan)</span>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={(e) =>
                      setSignedFile(e.target.files?.[0] ?? null)
                    }
                  />
                </label>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={!signedFile || uploadSigned.isPending}
                  onClick={() => uploadSigned.mutate()}
                >
                  <FileUp size={14} />
                  Déposer l&apos;acte signé
                </button>
              </div>
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
            <EmptyState
              message={
                editable
                  ? "Circuit non démarré — joignez la demande, générez l'acte, puis soumettez."
                  : "Aucun circuit associé."
              }
            />
          ) : (
            <dl className="def-list two">
              <div>
                <dt>Circuit</dt>
                <dd>{workflow.data.instance.definition_code || "—"}</dd>
              </div>
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

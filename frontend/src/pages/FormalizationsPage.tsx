import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  FileSignature,
  FileUp,
  Gavel,
  Plus,
  Receipt,
  Stamp,
  Trash2,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import type {
  ApprovalTask,
  FormalizationFee,
  Guarantee,
  GuaranteeFormalizationRequest,
  GedDocument,
  Paginated,
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

const OPEN_FORM_STATUSES = [
  "DRAFT",
  "IN_PROGRESS",
  "IN_APPROVAL",
  "RETURNED",
  "APPROVED",
];

const EDITABLE_STATUSES = ["DRAFT", "IN_PROGRESS", "RETURNED"];

const LEGAL_STAGES = [
  { value: "NOT_SENT", label: "Non soumis chez le notaire" },
  { value: "AT_NOTARY", label: "Chez le notaire" },
  { value: "AWAITING_SIGNATURE", label: "En attente de signature" },
  { value: "SIGNED", label: "Acte signé" },
  { value: "PENDING_REGISTRATION", label: "Enregistrement / publicité en cours" },
  { value: "REGISTERED", label: "Enregistré" },
];

const FEE_TYPES = [
  { value: "NOTARY", label: "Notaire / acte" },
  { value: "REGISTRATION", label: "Enregistrement / publicité" },
  { value: "BAILIFF", label: "Huissier" },
  { value: "ADMIN", label: "Frais administratifs" },
  { value: "OTHER", label: "Divers" },
];

const DOC_CATS = [
  { value: "FORM_PROJET_ACTE", label: "Projet d'acte de constitution" },
  { value: "FORM_ACTE_SIGNE", label: "Acte de constitution signé" },
  { value: "FORM_ENREGISTREMENT", label: "Preuve d'enregistrement / publicité" },
  { value: "FORM_EXPERTISE", label: "Expertise / évaluation" },
  { value: "FORM_TITRE", label: "Titre / pièce du bien" },
  { value: "FORM_ID", label: "Pièce d'identité / quitus" },
  { value: "FORM_OTHER", label: "Autre pièce formalisation" },
];

const COMPLETABLE_STAGES = [
  "SIGNED",
  "PENDING_REGISTRATION",
  "REGISTERED",
  "DONE",
];

function legalStageLabel(value: string, display?: string) {
  return (
    display ||
    LEGAL_STAGES.find((s) => s.value === value)?.label ||
    value ||
    "—"
  );
}

function errMsg(err: unknown, fallback: string) {
  const data = (err as { response?: { data?: unknown } })?.response?.data;
  const raw =
    data && typeof data === "object" && "errors" in data
      ? (data as { errors: unknown }).errors
      : data;
  if (typeof raw === "string") return raw;
  if (Array.isArray(raw)) return raw.map(String).join(" · ");
  if (data && typeof data === "object") {
    const parts = Object.values(data as Record<string, unknown>)
      .flatMap((v) => (Array.isArray(v) ? v : [v]))
      .map(String)
      .filter(Boolean);
    if (parts.length) return parts.join(" · ");
  }
  return fallback;
}

export function FormalizationsPage() {
  const { user } = useAuth();
  const canInitiate = hasPerm(
    user,
    "guarantees.initiate_guaranteeformalizationrequest",
  );
  const [page, setPage] = useState(1);

  const list = useQuery({
    queryKey: ["guarantee-formalizations", page],
    queryFn: async () =>
      (
        await api.get<Paginated<GuaranteeFormalizationRequest>>(
          "/guarantee-formalizations/",
          { params: { page } },
        )
      ).data,
  });

  return (
    <div>
      <PageHeader
        icon={Stamp}
        title="Formalisations"
        subtitle="Constitution juridique des garanties — parallèle au crédit"
        actions={
          canInitiate ? (
            <Link className="btn btn-primary" to="/formalisations/nouvelle">
              <Plus />
              Nouvelle formalisation
            </Link>
          ) : undefined
        }
      />

      <div className="callout callout-info" style={{ marginBottom: 14 }}>
        La formalisation est parallèle au crédit et ne bloque pas le
        décaissement.
      </div>

      {list.isLoading || !list.data ? (
        <Spinner />
      ) : list.data.results.length === 0 ? (
        <EmptyState message="Aucune formalisation de garantie." />
      ) : (
        <>
          <table className="table card">
            <thead>
              <tr>
                <th>Référence</th>
                <th>Garantie</th>
                <th>Client</th>
                <th>Étape juridique</th>
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
                  <td>
                    <Badge
                      value={r.legal_stage}
                      label={legalStageLabel(
                        r.legal_stage,
                        r.legal_stage_display,
                      )}
                    />
                  </td>
                  <td>
                    <Badge value={r.status} label={r.status_display} />
                  </td>
                  <td>
                    <Link
                      className="btn btn-ghost btn-sm"
                      to={`/formalisations/${r.id}`}
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

export function FormalizationNewPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const [clientId, setClientId] = useState(searchParams.get("client") || "");
  const [guaranteeId, setGuaranteeId] = useState(
    searchParams.get("guarantee") || "",
  );
  const [notaryName, setNotaryName] = useState("");
  const [notaryReference, setNotaryReference] = useState("");
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const guarantees = useQuery({
    queryKey: ["guarantees", "for-formalization", clientId],
    queryFn: async () =>
      (
        await api.get<Paginated<Guarantee>>("/guarantees/", {
          params: { client: clientId, status: "ACTIVE", page_size: 100 },
        })
      ).data,
    enabled: !!clientId,
  });

  const openForms = useQuery({
    queryKey: ["guarantee-formalizations", "open-by-client", clientId],
    queryFn: async () =>
      (
        await api.get<Paginated<GuaranteeFormalizationRequest>>(
          "/guarantee-formalizations/",
          { params: { client: clientId, page_size: 100 } },
        )
      ).data,
    enabled: !!clientId,
  });

  const busyGuaranteeIds = useMemo(() => {
    const set = new Set<string>();
    for (const r of openForms.data?.results ?? []) {
      if (OPEN_FORM_STATUSES.includes(r.status)) set.add(r.guarantee);
    }
    return set;
  }, [openForms.data]);

  const activeGuarantees = useMemo(() => {
    const rows = guarantees.data?.results ?? [];
    const free = rows.filter((g) => !busyGuaranteeIds.has(g.id));
    return free.length > 0 ? free : rows;
  }, [guarantees.data, busyGuaranteeIds]);

  const showingAllActive =
    (guarantees.data?.results ?? []).length > 0 &&
    activeGuarantees.length === (guarantees.data?.results ?? []).length &&
    busyGuaranteeIds.size > 0;

  useEffect(() => {
    const gParam = searchParams.get("guarantee");
    if (!gParam || !guarantees.data) return;
    if (guarantees.data.results.some((g) => g.id === gParam)) {
      setGuaranteeId(gParam);
    }
  }, [guarantees.data, searchParams]);

  const canSubmit = !!clientId && !!guaranteeId;

  const create = useMutation({
    mutationFn: async () =>
      (
        await api.post<GuaranteeFormalizationRequest>(
          "/guarantee-formalizations/",
          {
            guarantee: guaranteeId,
            notary_name: notaryName,
            notary_reference: notaryReference,
            comment,
            as_draft: true,
          },
        )
      ).data,
    onSuccess: (data) => navigate(`/formalisations/${data.id}`),
    onError: (err: unknown) =>
      setError(errMsg(err, "Création impossible (garantie ou dossier ouvert).")),
  });

  function onClientPicked(id: string) {
    setClientId(id);
    setGuaranteeId("");
    setError(null);
  }

  if (!hasPerm(user, "guarantees.initiate_guaranteeformalizationrequest")) {
    return (
      <div>
        <PageHeader icon={Stamp} title="Nouvelle formalisation" />
        <EmptyState message="Vous n'avez pas le droit d'initier une formalisation." />
      </div>
    );
  }

  return (
    <div className="page-shell dation-compose">
      <PageHeader
        icon={Stamp}
        title="Nouvelle formalisation"
        subtitle="Sélectionnez une garantie active à constituer juridiquement"
        actions={
          <Link className="btn btn-ghost" to="/formalisations">
            <ArrowLeft />
            Retour
          </Link>
        }
      />

      <div className="callout callout-info" style={{ marginBottom: 14 }}>
        La formalisation est parallèle au crédit et ne bloque pas le
        décaissement.
      </div>

      <form
        className="dation-compose-form"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          if (!canSubmit) return;
          setError(null);
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
                    Choisissez le client titulaire de la garantie.
                  </span>
                </div>
              </div>
              <ClientAutocomplete
                value={clientId}
                onChange={(id) => onClientPicked(id)}
              />
            </section>

            {!clientId ? (
              <section className="card form-section dation-compose-empty">
                <EmptyState message="Sélectionnez un client pour afficher ses garanties actives." />
              </section>
            ) : guarantees.isLoading ? (
              <Spinner />
            ) : (
              <>
                <section className="card form-section">
                  <div className="card-title form-section-head">
                    <span className="form-section-icon">
                      <FileSignature size={18} />
                    </span>
                    <div className="form-section-heading">
                      <span className="form-section-title">
                        2. Garantie à formaliser
                      </span>
                      <span className="form-section-desc">
                        {showingAllActive
                          ? "Garanties actives (certaines ont déjà une formalisation ouverte)."
                          : "Garanties actives sans formalisation ouverte."}
                      </span>
                    </div>
                    <div className="form-section-action">
                      <span className="muted small">
                        {activeGuarantees.length} disponible
                        {activeGuarantees.length > 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                  {activeGuarantees.length === 0 ? (
                    <EmptyState message="Aucune garantie active pour ce client." />
                  ) : (
                    <div className="dation-guarantee-list" role="list">
                      {activeGuarantees.map((g) => {
                        const busy = busyGuaranteeIds.has(g.id);
                        const checked = guaranteeId === g.id;
                        return (
                          <label
                            key={g.id}
                            role="listitem"
                            className={`dation-guarantee-row${checked ? " selected" : ""}${busy ? " muted" : ""}`}
                          >
                            <input
                              type="radio"
                              name="formalization-guarantee"
                              checked={checked}
                              disabled={busy}
                              onChange={() => setGuaranteeId(g.id)}
                            />
                            <span className="dation-guarantee-body">
                              <span className="dation-guarantee-title">
                                {g.type_display}
                                <span className="muted small">
                                  {" "}
                                  —{" "}
                                  <code>
                                    {g.reference || g.id.slice(0, 8)}
                                  </code>
                                </span>
                              </span>
                              {g.description && (
                                <span className="dation-guarantee-desc">
                                  {g.description.slice(0, 140)}
                                </span>
                              )}
                              {busy && (
                                <span className="muted small">
                                  Formalisation déjà ouverte
                                </span>
                              )}
                            </span>
                            <span className="dation-guarantee-meta">
                              <strong>
                                {formatMoney(g.current_value)}
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
                      <Stamp size={18} />
                    </span>
                    <div className="form-section-heading">
                      <span className="form-section-title">
                        3. Notaire & commentaire
                      </span>
                      <span className="form-section-desc">
                        Optionnel à la création — modifiable ensuite.
                      </span>
                    </div>
                  </div>
                  <div className="form-grid">
                    <label className="field">
                      <span>Notaire / étude</span>
                      <input
                        value={notaryName}
                        onChange={(e) => setNotaryName(e.target.value)}
                        placeholder="Optionnel"
                      />
                    </label>
                    <label className="field">
                      <span>Réf. dossier notaire</span>
                      <input
                        value={notaryReference}
                        onChange={(e) => setNotaryReference(e.target.value)}
                        placeholder="Optionnel"
                      />
                    </label>
                    <label className="field" style={{ gridColumn: "1 / -1" }}>
                      <span>Commentaire</span>
                      <textarea
                        value={comment}
                        onChange={(e) => setComment(e.target.value)}
                        rows={3}
                        placeholder="Observations, pièces à prévoir…"
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
                <Stamp size={18} />
                <strong>Récapitulatif</strong>
              </div>
              {!clientId ? (
                <p className="muted small">Sélectionnez un client.</p>
              ) : (
                <dl className="def-list">
                  <div>
                    <dt>Garanties actives</dt>
                    <dd>{guarantees.data?.results.length ?? "…"}</dd>
                  </div>
                  <div>
                    <dt>Sélection</dt>
                    <dd>
                      {guaranteeId
                        ? activeGuarantees.find((g) => g.id === guaranteeId)
                            ?.reference || guaranteeId.slice(0, 8)
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
                {create.isPending ? "Création…" : "Créer le brouillon"}
              </button>
              <Link className="btn btn-ghost" to="/formalisations">
                Annuler
              </Link>
            </div>
          </aside>
        </div>
      </form>
    </div>
  );
}

export function FormalizationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { user } = useAuth();
  const canInitiate = hasPerm(
    user,
    "guarantees.initiate_guaranteeformalizationrequest",
  );

  const [feeType, setFeeType] = useState("NOTARY");
  const [feeAmount, setFeeAmount] = useState("");
  const [feePayer, setFeePayer] = useState("CLIENT");
  const [feeLabel, setFeeLabel] = useState("");
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docName, setDocName] = useState("");
  const [docCat, setDocCat] = useState("FORM_PROJET_ACTE");
  const [actionError, setActionError] = useState<string | null>(null);

  const [draftNotaryName, setDraftNotaryName] = useState("");
  const [draftNotaryRef, setDraftNotaryRef] = useState("");
  const [draftSentAt, setDraftSentAt] = useState("");
  const [draftExpectedReturn, setDraftExpectedReturn] = useState("");
  const [draftRegNumber, setDraftRegNumber] = useState("");
  const [draftRegDate, setDraftRegDate] = useState("");
  const [draftRegAuth, setDraftRegAuth] = useState("");
  const [draftComment, setDraftComment] = useState("");
  const [draftSynced, setDraftSynced] = useState(false);

  const [advanceStage, setAdvanceStage] = useState("");
  const [advanceNotaryName, setAdvanceNotaryName] = useState("");
  const [advanceNotaryRef, setAdvanceNotaryRef] = useState("");
  const [advanceRegNumber, setAdvanceRegNumber] = useState("");
  const [advanceRegDate, setAdvanceRegDate] = useState("");
  const [advanceRegAuth, setAdvanceRegAuth] = useState("");

  const detail = useQuery({
    queryKey: ["guarantee-formalization", id],
    queryFn: async () =>
      (
        await api.get<GuaranteeFormalizationRequest>(
          `/guarantee-formalizations/${id}/`,
        )
      ).data,
    enabled: !!id,
  });

  useEffect(() => {
    setDraftSynced(false);
  }, [id]);

  useEffect(() => {
    if (!detail.data || draftSynced) return;
    const d = detail.data;
    setDraftNotaryName(d.notary_name || "");
    setDraftNotaryRef(d.notary_reference || "");
    setDraftSentAt(d.sent_to_notary_at || "");
    setDraftExpectedReturn(d.expected_return_date || "");
    setDraftRegNumber(d.registration_number || "");
    setDraftRegDate(d.registration_date || "");
    setDraftRegAuth(d.registration_authority || "");
    setDraftComment(d.comment || "");
    setAdvanceStage(d.legal_stage || "NOT_SENT");
    setAdvanceNotaryName(d.notary_name || "");
    setAdvanceNotaryRef(d.notary_reference || "");
    setAdvanceRegNumber(d.registration_number || "");
    setAdvanceRegDate(d.registration_date || "");
    setAdvanceRegAuth(d.registration_authority || "");
    setDraftSynced(true);
  }, [detail.data, draftSynced]);

  const docs = useQuery({
    queryKey: ["guarantee-formalization-docs", id],
    queryFn: async () =>
      (
        await api.get<GedDocument[]>(
          `/guarantee-formalizations/${id}/documents/`,
        )
      ).data,
    enabled: !!id,
  });

  const workflow = useQuery({
    queryKey: ["guarantee-formalization-workflow", id],
    queryFn: async () =>
      (
        await api.get<{
          instance: { status: string; definition_code?: string } | null;
        }>(`/guarantee-formalizations/${id}/workflow/`)
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
    qc.invalidateQueries({ queryKey: ["guarantee-formalization", id] });
    qc.invalidateQueries({ queryKey: ["guarantee-formalization-docs", id] });
    qc.invalidateQueries({
      queryKey: ["guarantee-formalization-workflow", id],
    });
    qc.invalidateQueries({ queryKey: ["guarantee-formalizations"] });
    qc.invalidateQueries({ queryKey: ["guarantees"] });
    qc.invalidateQueries({ queryKey: ["guarantee"] });
    setDraftSynced(false);
  }

  const updateDraft = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/guarantee-formalizations/${id}/update-draft/`, {
          notary_name: draftNotaryName,
          notary_reference: draftNotaryRef,
          sent_to_notary_at: draftSentAt || null,
          expected_return_date: draftExpectedReturn || null,
          registration_number: draftRegNumber,
          registration_date: draftRegDate || null,
          registration_authority: draftRegAuth,
          comment: draftComment,
        })
      ).data,
    onSuccess: () => {
      setActionError(null);
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Mise à jour impossible.")),
  });

  const start = useMutation({
    mutationFn: async () =>
      (await api.post(`/guarantee-formalizations/${id}/start/`)).data,
    onSuccess: () => {
      setActionError(null);
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Démarrage impossible.")),
  });

  const advance = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = { legal_stage: advanceStage };
      if (advanceNotaryName) body.notary_name = advanceNotaryName;
      if (advanceNotaryRef) body.notary_reference = advanceNotaryRef;
      if (advanceRegNumber) body.registration_number = advanceRegNumber;
      if (advanceRegDate) body.registration_date = advanceRegDate;
      if (advanceRegAuth) body.registration_authority = advanceRegAuth;
      return (
        await api.post(
          `/guarantee-formalizations/${id}/advance-stage/`,
          body,
        )
      ).data;
    },
    onSuccess: () => {
      setActionError(null);
      invalidateAll();
    },
    onError: (e) =>
      setActionError(errMsg(e, "Avancement de l'étape impossible.")),
  });

  const submit = useMutation({
    mutationFn: async () =>
      (await api.post(`/guarantee-formalizations/${id}/submit/`)).data,
    onSuccess: () => {
      setActionError(null);
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Soumission impossible.")),
  });

  const cancel = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/guarantee-formalizations/${id}/cancel/`, {
          comment: "Annulé",
        })
      ).data,
    onSuccess: () => invalidateAll(),
    onError: (e) => setActionError(errMsg(e, "Annulation impossible.")),
  });

  const complete = useMutation({
    mutationFn: async () =>
      (await api.post(`/guarantee-formalizations/${id}/complete/`)).data,
    onSuccess: () => {
      setActionError(null);
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Clôture impossible.")),
  });

  const addFee = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/guarantee-formalizations/${id}/add-fee/`, {
          fee_type: feeType,
          label: feeLabel,
          amount: feeAmount,
          payer: feePayer,
        })
      ).data,
    onSuccess: () => {
      setFeeAmount("");
      setFeeLabel("");
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Ajout de frais impossible.")),
  });

  const removeFee = useMutation({
    mutationFn: async (feeId: string) =>
      (
        await api.post(
          `/guarantee-formalizations/${id}/remove-fee/${feeId}/`,
        )
      ).data,
    onSuccess: () => invalidateAll(),
  });

  const uploadDoc = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      if (docFile) fd.append("file", docFile);
      fd.append("name", docName || docFile?.name || "Document");
      fd.append("category", docCat);
      return (
        await api.post(`/guarantee-formalizations/${id}/documents/`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        })
      ).data;
    },
    onSuccess: () => {
      setDocFile(null);
      setDocName("");
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Upload impossible.")),
  });

  if (detail.isLoading || !detail.data) return <Spinner />;
  const r = detail.data;
  const editable = EDITABLE_STATUSES.includes(r.status);
  const canCancel =
    canInitiate &&
    ["DRAFT", "IN_PROGRESS", "RETURNED", "IN_APPROVAL"].includes(r.status);
  const canStart =
    canInitiate && ["DRAFT", "RETURNED"].includes(r.status);
  const canSubmit =
    canInitiate &&
    ["DRAFT", "IN_PROGRESS", "RETURNED"].includes(r.status);
  const canComplete =
    canInitiate &&
    !["COMPLETED", "CANCELLED", "REJECTED"].includes(r.status) &&
    COMPLETABLE_STAGES.includes(r.legal_stage);
  const myTask =
    myTasks?.results.find(
      (t) =>
        t.target_meta?.kind === "FORMALISATION" && t.target_meta.id === r.id,
    ) ?? null;
  const fees: FormalizationFee[] = r.fees ?? [];

  return (
    <div>
      <PageHeader
        icon={Stamp}
        title={r.reference || "Formalisation"}
        subtitle={r.client_display}
        actions={
          <div className="row-actions">
            <Link className="btn btn-ghost" to="/formalisations">
              <ArrowLeft />
              Retour
            </Link>
            {canStart && (
              <button
                className="btn btn-ghost"
                onClick={() => start.mutate()}
                disabled={start.isPending}
              >
                Démarrer
              </button>
            )}
            {canSubmit && (
              <button
                className="btn btn-primary"
                onClick={() => submit.mutate()}
                disabled={submit.isPending}
              >
                Soumettre au circuit
              </button>
            )}
            {canComplete && (
              <button
                className="btn btn-primary"
                onClick={() => {
                  if (
                    !window.confirm(
                      "Clôturer cette formalisation et reporter les preuves sur la garantie ?",
                    )
                  ) {
                    return;
                  }
                  complete.mutate();
                }}
                disabled={complete.isPending}
              >
                Clôturer
              </button>
            )}
            {canCancel && (
              <button
                className="btn btn-ghost"
                onClick={() => {
                  if (
                    r.status === "IN_APPROVAL" &&
                    !window.confirm(
                      "Annuler cette formalisation en cours de validation ? Le circuit sera interrompu.",
                    )
                  ) {
                    return;
                  }
                  cancel.mutate();
                }}
                disabled={cancel.isPending}
              >
                Annuler
              </button>
            )}
          </div>
        }
      />

      <div className="callout callout-info" style={{ marginBottom: 14 }}>
        La formalisation est parallèle au crédit et ne bloque pas le
        décaissement.
      </div>

      {actionError && <div className="form-error">{actionError}</div>}

      {r.status === "IN_APPROVAL" && !myTask && (
        <div className="muted small" style={{ marginBottom: 12 }}>
          Dossier en circuit de validation. Vous pouvez encore l&apos;annuler si
          besoin.
        </div>
      )}

      <div className="detail-grid">
        <Card title="Dossier">
          <dl className="def-list two">
            <div>
              <dt>Statut</dt>
              <dd>
                <Badge value={r.status} label={r.status_display} />
              </dd>
            </div>
            <div>
              <dt>Étape juridique</dt>
              <dd>
                <Badge
                  value={r.legal_stage}
                  label={legalStageLabel(
                    r.legal_stage,
                    r.legal_stage_display,
                  )}
                />
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
              <dt>Client</dt>
              <dd>
                {r.client ? (
                  <Link to={`/clients/${r.client}`}>{r.client_display}</Link>
                ) : (
                  r.client_display
                )}
              </dd>
            </div>
            <div>
              <dt>Frais client</dt>
              <dd>{formatMoney(r.fees_client_total ?? null)}</dd>
            </div>
            <div>
              <dt>Frais institution</dt>
              <dd>{formatMoney(r.fees_institution_total ?? null)}</dd>
            </div>
            {r.completed_at && (
              <div>
                <dt>Clôturée le</dt>
                <dd>{formatDate(r.completed_at)}</dd>
              </div>
            )}
          </dl>
          {r.comment && (
            <p className="muted small" style={{ marginTop: 12 }}>
              {r.comment}
            </p>
          )}
        </Card>

        <Card title="Étape juridique">
          {editable && canInitiate ? (
            <div className="form-grid">
              <label className="field">
                <span>Nouvelle étape</span>
                <select
                  value={advanceStage}
                  onChange={(e) => setAdvanceStage(e.target.value)}
                >
                  {LEGAL_STAGES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </label>
              {(advanceStage === "AT_NOTARY" ||
                advanceStage === "AWAITING_SIGNATURE") && (
                <>
                  <label className="field">
                    <span>Notaire / étude</span>
                    <input
                      value={advanceNotaryName}
                      onChange={(e) => setAdvanceNotaryName(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>Réf. notaire</span>
                    <input
                      value={advanceNotaryRef}
                      onChange={(e) => setAdvanceNotaryRef(e.target.value)}
                    />
                  </label>
                </>
              )}
              {(advanceStage === "PENDING_REGISTRATION" ||
                advanceStage === "REGISTERED") && (
                <>
                  <label className="field">
                    <span>N° d&apos;enregistrement</span>
                    <input
                      value={advanceRegNumber}
                      onChange={(e) => setAdvanceRegNumber(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>Date d&apos;enregistrement</span>
                    <input
                      type="date"
                      value={advanceRegDate}
                      onChange={(e) => setAdvanceRegDate(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>Organisme</span>
                    <input
                      value={advanceRegAuth}
                      onChange={(e) => setAdvanceRegAuth(e.target.value)}
                    />
                  </label>
                </>
              )}
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={
                  !advanceStage ||
                  advanceStage === r.legal_stage ||
                  advance.isPending
                }
                onClick={() => advance.mutate()}
              >
                Avancer l&apos;étape
              </button>
            </div>
          ) : (
            <dl className="def-list two">
              <div>
                <dt>Étape</dt>
                <dd>
                  {legalStageLabel(r.legal_stage, r.legal_stage_display)}
                </dd>
              </div>
              <div>
                <dt>Notaire</dt>
                <dd>{r.notary_name || "—"}</dd>
              </div>
              <div>
                <dt>Réf. notaire</dt>
                <dd>{r.notary_reference || "—"}</dd>
              </div>
              <div>
                <dt>N° enregistrement</dt>
                <dd>{r.registration_number || "—"}</dd>
              </div>
              <div>
                <dt>Date enregistrement</dt>
                <dd>
                  {r.registration_date
                    ? formatDate(r.registration_date)
                    : "—"}
                </dd>
              </div>
              <div>
                <dt>Organisme</dt>
                <dd>{r.registration_authority || "—"}</dd>
              </div>
            </dl>
          )}
        </Card>

        {editable && canInitiate && (
          <Card title="Notaire & enregistrement (brouillon)">
            <div className="form-grid">
              <label className="field">
                <span>Notaire / étude</span>
                <input
                  value={draftNotaryName}
                  onChange={(e) => setDraftNotaryName(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Réf. dossier notaire</span>
                <input
                  value={draftNotaryRef}
                  onChange={(e) => setDraftNotaryRef(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Transmis au notaire le</span>
                <input
                  type="date"
                  value={draftSentAt}
                  onChange={(e) => setDraftSentAt(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Retour prévu</span>
                <input
                  type="date"
                  value={draftExpectedReturn}
                  onChange={(e) => setDraftExpectedReturn(e.target.value)}
                />
              </label>
              <label className="field">
                <span>N° d&apos;enregistrement</span>
                <input
                  value={draftRegNumber}
                  onChange={(e) => setDraftRegNumber(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Date d&apos;enregistrement</span>
                <input
                  type="date"
                  value={draftRegDate}
                  onChange={(e) => setDraftRegDate(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Organisme</span>
                <input
                  value={draftRegAuth}
                  onChange={(e) => setDraftRegAuth(e.target.value)}
                />
              </label>
              <label className="field" style={{ gridColumn: "1 / -1" }}>
                <span>Commentaire</span>
                <textarea
                  value={draftComment}
                  onChange={(e) => setDraftComment(e.target.value)}
                  rows={3}
                />
              </label>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={updateDraft.isPending}
                onClick={() => updateDraft.mutate()}
              >
                Enregistrer le brouillon
              </button>
            </div>
          </Card>
        )}

        <Card title="Frais">
          {fees.length === 0 ? (
            <p className="muted small">Aucun frais enregistré.</p>
          ) : (
            <ul className="link-list">
              {fees.map((f) => (
                <li key={f.id}>
                  <span>
                    <Receipt size={14} /> {f.fee_type_display}
                    {f.label ? ` — ${f.label}` : ""}
                    <em className="muted small"> · {f.payer_display}</em>
                  </span>
                  <span className="row-actions">
                    <span className="num">{formatMoney(f.amount)}</span>
                    {editable && canInitiate && (
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => removeFee.mutate(f.id)}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {editable && canInitiate && (
            <div className="form-grid" style={{ marginTop: 12 }}>
              <label className="field">
                <span>Type</span>
                <select
                  value={feeType}
                  onChange={(e) => setFeeType(e.target.value)}
                >
                  {FEE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Montant</span>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={feeAmount}
                  onChange={(e) => setFeeAmount(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Payeur</span>
                <select
                  value={feePayer}
                  onChange={(e) => setFeePayer(e.target.value)}
                >
                  <option value="CLIENT">Client</option>
                  <option value="INSTITUTION">Institution</option>
                </select>
              </label>
              <label className="field">
                <span>Libellé</span>
                <input
                  value={feeLabel}
                  onChange={(e) => setFeeLabel(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={!feeAmount || addFee.isPending}
                onClick={() => addFee.mutate()}
              >
                <Plus size={14} />
                Ajouter frais
              </button>
            </div>
          )}
        </Card>

        <Card title="Pièces jointes">
          {(docs.data ?? []).length === 0 ? (
            <p className="muted small">Aucune pièce jointe.</p>
          ) : (
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
          {canInitiate &&
            !["COMPLETED", "CANCELLED", "REJECTED"].includes(r.status) && (
              <div className="form-grid" style={{ marginTop: 12 }}>
                <label className="field">
                  <span>Fichier</span>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.tiff,.docx"
                    onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
                  />
                </label>
                <label className="field">
                  <span>Nom</span>
                  <input
                    value={docName}
                    onChange={(e) => setDocName(e.target.value)}
                    placeholder="Optionnel"
                  />
                </label>
                <label className="field">
                  <span>Catégorie</span>
                  <select
                    value={docCat}
                    onChange={(e) => setDocCat(e.target.value)}
                  >
                    {DOC_CATS.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={!docFile || uploadDoc.isPending}
                  onClick={() => uploadDoc.mutate()}
                >
                  <FileUp size={14} />
                  Joindre
                </button>
              </div>
            )}
        </Card>

        {myTask && (
          <Card title={`Décision — ${myTask.step_name}`}>
            <div className="card-title-icon">
              <Gavel size={16} />
            </div>
            <DecisionPanel task={myTask} onDone={invalidateAll} />
          </Card>
        )}

        <Card title="Circuit">
          {!workflow.data?.instance ? (
            <EmptyState
              message={
                editable
                  ? "Circuit non démarré — soumettez le dossier."
                  : "Aucun circuit associé."
              }
            />
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

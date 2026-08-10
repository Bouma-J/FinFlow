import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleDollarSign, Download, Mail, MessageSquare } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type {
  CollectionActionType,
  CollectionCase,
  CollectionStage,
  PromiseStatus,
} from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import {
  Badge,
  Card,
  PageHeader,
  Spinner,
  formatMoney,
} from "@/components/ui";
import { exportCollectionCasePdf } from "@/utils/exportCollectionCasePdf";

const ACTION_TYPES: { value: CollectionActionType; label: string }[] = [
  { value: "CALL", label: "Appel" },
  { value: "SMS", label: "SMS" },
  { value: "EMAIL", label: "Courriel" },
  { value: "LETTER", label: "Courrier" },
  { value: "VISIT", label: "Visite" },
  { value: "LEGAL", label: "Acte judiciaire" },
];

const STAGES: { value: CollectionStage; label: string }[] = [
  { value: "AMICABLE", label: "Amiable" },
  { value: "PRECONTENTIOUS", label: "Précontentieux" },
  { value: "LITIGATION", label: "Contentieux" },
  { value: "CLOSED", label: "Clôturé" },
];

export function CollectionCaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const canRestructure = hasPerm(user, "collections.add_loanrestructure");
  const canWriteOff = hasPerm(user, "collections.add_writeoff");
  const canLitigation = hasPerm(user, "collections.change_litigationfile");

  const [payAmount, setPayAmount] = useState("");
  const [payDate, setPayDate] = useState(
    () => new Date().toISOString().slice(0, 10),
  );
  const [payRef, setPayRef] = useState("");

  const [actionType, setActionType] = useState<CollectionActionType>("CALL");
  const [actionDate, setActionDate] = useState(
    () => new Date().toISOString().slice(0, 10),
  );
  const [actionResult, setActionResult] = useState("");
  const [actionComment, setActionComment] = useState("");
  const [actionFollowUp, setActionFollowUp] = useState("");

  const [promiseAmount, setPromiseAmount] = useState("");
  const [promiseDate, setPromiseDate] = useState("");

  const [nextDate, setNextDate] = useState("");
  const [nextType, setNextType] = useState<CollectionActionType | "">("");
  const [nextNote, setNextNote] = useState("");

  const [restructureMonths, setRestructureMonths] = useState("12");
  const [restructureRate, setRestructureRate] = useState("");
  const [restructureReason, setRestructureReason] = useState("");
  const [writeOffReason, setWriteOffReason] = useState("");

  const caseQuery = useQuery({
    queryKey: ["collection-case", id],
    queryFn: async () =>
      (await api.get<CollectionCase>(`/collection-cases/${id}/`)).data,
    enabled: !!id,
  });

  useEffect(() => {
    const c = caseQuery.data;
    if (!c) return;
    setNextDate(c.next_action_date || "");
    setNextType(c.next_action_type || "");
    setNextNote(c.next_action_note || "");
  }, [caseQuery.data]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["collection-case", id] });
    qc.invalidateQueries({ queryKey: ["collection-cases"] });
    qc.invalidateQueries({ queryKey: ["collection-agent-dashboard"] });
  };

  const repayMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/collection-cases/${id}/repayments/`, {
          amount: payAmount,
          payment_date: payDate,
          reference: payRef,
        })
      ).data as CollectionCase,
    onSuccess: () => {
      setPayAmount("");
      setPayRef("");
      setSuccess("Encaissement enregistré et appliqué à l'échéancier.");
      setError(null);
      invalidate();
    },
    onError: () => setError("Impossible d'enregistrer l'encaissement."),
  });

  const actionMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post("/collection-actions/", {
          case: id,
          action_type: actionType,
          action_date: actionDate,
          result: actionResult,
          comment: actionComment,
          ...(actionFollowUp ? { next_follow_up_date: actionFollowUp } : {}),
        })
      ).data,
    onSuccess: () => {
      setActionResult("");
      setActionComment("");
      setActionFollowUp("");
      setSuccess("Action de relance enregistrée.");
      setError(null);
      invalidate();
    },
    onError: () => setError("Impossible d'enregistrer l'action."),
  });

  const promiseMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post("/payment-promises/", {
          case: id,
          amount: promiseAmount,
          promised_date: promiseDate,
          status: "PENDING" as PromiseStatus,
        })
      ).data,
    onSuccess: () => {
      setPromiseAmount("");
      setPromiseDate("");
      setSuccess("Promesse de paiement enregistrée.");
      setError(null);
      invalidate();
    },
    onError: () => setError("Impossible d'enregistrer la promesse."),
  });

  const stageMutation = useMutation({
    mutationFn: async (stage: CollectionStage) =>
      (await api.post(`/collection-cases/${id}/set-stage/`, { stage })).data,
    onSuccess: () => {
      setSuccess("Stade mis à jour.");
      setError(null);
      invalidate();
    },
    onError: () => setError("Impossible de changer le stade."),
  });

  const nextActionMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/collection-cases/${id}/set-next-action/`, {
          next_action_date: nextDate || null,
          next_action_type: nextType || "",
          next_action_note: nextNote,
        })
      ).data,
    onSuccess: () => {
      setSuccess("Prochaine action planifiée.");
      setError(null);
      invalidate();
    },
    onError: () => setError("Impossible de planifier la prochaine action."),
  });

  const reminderMutation = useMutation({
    mutationFn: async (channel: "EMAIL" | "SMS") =>
      (
        await api.post(`/collection-cases/${id}/send-reminder/`, { channel })
      ).data,
    onSuccess: (data: { reminder?: { status?: string } }) => {
      setSuccess(`Relance : ${data.reminder?.status || "OK"}`);
      setError(null);
      invalidate();
    },
    onError: () => setError("Impossible d'envoyer la relance."),
  });

  const restructureMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/collection-cases/${id}/restructure/`, {
          new_duration_months: Number(restructureMonths),
          ...(restructureRate ? { new_rate: restructureRate } : {}),
          reason: restructureReason,
        })
      ).data,
    onSuccess: () => {
      setSuccess("Restructuration appliquée — nouvel échéancier généré.");
      setError(null);
      setRestructureReason("");
      invalidate();
    },
    onError: () => setError("Restructuration impossible."),
  });

  const writeOffMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/collection-cases/${id}/write-off/`, {
          reason: writeOffReason,
        })
      ).data,
    onSuccess: () => {
      setSuccess("Prêt passé en perte — dossier clôturé.");
      setError(null);
      invalidate();
    },
    onError: () => setError("Passage en perte impossible."),
  });

  const createLitigation = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/litigations/`, {
          case: id,
          title: "Procédure contentieuse",
          action_type: "SUMMONS",
          status: "PRE_LITIGATION",
        })
      ).data as { id: string },
    onSuccess: (lit) => {
      invalidate();
      navigate(`/recouvrement/${id}/contentieux/${lit.id}`);
    },
    onError: () => setError("Impossible d'ouvrir une procédure contentieuse."),
  });

  function submitPay(e: FormEvent) {
    e.preventDefault();
    setSuccess(null);
    if (!payAmount || Number(payAmount) <= 0) {
      setError("Indiquez un montant d'encaissement positif.");
      return;
    }
    repayMutation.mutate();
  }

  function submitAction(e: FormEvent) {
    e.preventDefault();
    setSuccess(null);
    actionMutation.mutate();
  }

  function submitPromise(e: FormEvent) {
    e.preventDefault();
    setSuccess(null);
    if (!promiseAmount || !promiseDate) {
      setError("Montant et date de promesse obligatoires.");
      return;
    }
    promiseMutation.mutate();
  }

  function submitNextAction(e: FormEvent) {
    e.preventDefault();
    setSuccess(null);
    nextActionMutation.mutate();
  }

  if (caseQuery.isLoading || !caseQuery.data) {
    return <Spinner />;
  }

  const c = caseQuery.data;

  return (
    <div>
      <PageHeader
        icon={CircleDollarSign}
        title={`Recouvrement — ${c.application_reference || c.client_name}`}
        subtitle={`${c.client_name} · ${c.agency_name}${
          c.product_name ? ` · ${c.product_name}` : ""
        }`}
        actions={
          <>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => exportCollectionCasePdf(c)}
            >
              <Download size={14} /> PDF
            </button>
            <Link to="/recouvrement" className="btn btn-ghost btn-sm">
              <ArrowLeft size={14} /> Retour
            </Link>
          </>
        }
      />

      {success && (
        <div className="form-success" style={{ marginBottom: 12 }}>
          {success}
        </div>
      )}
      {error && (
        <div className="form-error" style={{ marginBottom: 12 }}>
          {error}
        </div>
      )}

      <div className="detail-grid">
        <Card title="Situation">
          <dl className="def-list two">
            <div>
              <dt>Client</dt>
              <dd>{c.client_name}</dd>
            </div>
            <div>
              <dt>Dossier</dt>
              <dd>
                {c.application_id ? (
                  <Link to={`/dossiers/${c.application_id}`}>
                    {c.application_reference || "Voir le dossier"}
                  </Link>
                ) : (
                  c.application_reference || "—"
                )}
              </dd>
            </div>
            <div>
              <dt>Produit</dt>
              <dd>{c.product_name || "—"}</dd>
            </div>
            <div>
              <dt>Capital prêt</dt>
              <dd>{formatMoney(c.loan_principal)}</dd>
            </div>
            <div>
              <dt>Statut prêt</dt>
              <dd>
                <Badge value={c.loan_status} />
              </dd>
            </div>
            <div>
              <dt>Réf. CBS</dt>
              <dd>{c.core_banking_reference || "—"}</dd>
            </div>
            <div>
              <dt>PAR</dt>
              <dd>
                <Badge value={c.par_class_display} />
              </dd>
            </div>
            <div>
              <dt>Jours de retard</dt>
              <dd>{c.days_overdue}</dd>
            </div>
            <div>
              <dt>Montant impayé</dt>
              <dd>{formatMoney(c.overdue_amount)}</dd>
            </div>
            <div>
              <dt>Capital restant dû</dt>
              <dd>{formatMoney(c.outstanding_principal || "0")}</dd>
            </div>
            <div>
              <dt>Prochaine échéance</dt>
              <dd>{c.next_due_date || "—"}</dd>
            </div>
            <div>
              <dt>Agent</dt>
              <dd>{c.assigned_to_name || "Non affecté"}</dd>
            </div>
            <div>
              <dt>Stade</dt>
              <dd>
                <select
                  value={c.stage}
                  onChange={(e) =>
                    stageMutation.mutate(e.target.value as CollectionStage)
                  }
                  disabled={stageMutation.isPending}
                >
                  {STAGES.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </dd>
            </div>
            <div>
              <dt>Prochaine action</dt>
              <dd>
                {c.next_action_date
                  ? `${c.next_action_date}${
                      c.next_action_type_display
                        ? ` · ${c.next_action_type_display}`
                        : ""
                    }`
                  : "Non planifiée"}
                {c.next_action_note ? (
                  <div className="muted small">{c.next_action_note}</div>
                ) : null}
              </dd>
            </div>
          </dl>
        </Card>

        <Card title="Nouvel encaissement">
          <form
            className="inline-form"
            style={{ boxShadow: "none", border: 0, padding: 0 }}
            onSubmit={submitPay}
          >
            <div className="form-grid">
              <label className="field">
                <span>Montant *</span>
                <input
                  type="number"
                  min="1"
                  step="0.01"
                  value={payAmount}
                  onChange={(e) => setPayAmount(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Date</span>
                <input
                  type="date"
                  value={payDate}
                  onChange={(e) => setPayDate(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Référence</span>
                <input
                  value={payRef}
                  onChange={(e) => setPayRef(e.target.value)}
                  placeholder="N° reçu / bordereau"
                />
              </label>
            </div>
            <p className="muted small">
              Le montant est réparti automatiquement sur les échéances
              impayées (FIFO).
            </p>
            <button
              className="btn btn-primary"
              disabled={repayMutation.isPending}
            >
              Enregistrer l&apos;encaissement
            </button>
          </form>
        </Card>
      </div>

      <div className="detail-grid" style={{ marginTop: 16 }}>
        <Card title="Planifier la prochaine action">
          <form
            className="inline-form"
            style={{ boxShadow: "none", border: 0, padding: 0 }}
            onSubmit={submitNextAction}
          >
            <div className="form-grid">
              <label className="field">
                <span>Date</span>
                <input
                  type="date"
                  value={nextDate}
                  onChange={(e) => setNextDate(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Type</span>
                <select
                  value={nextType}
                  onChange={(e) =>
                    setNextType(e.target.value as CollectionActionType | "")
                  }
                >
                  <option value="">—</option>
                  {ACTION_TYPES.map((a) => (
                    <option key={a.value} value={a.value}>
                      {a.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Note</span>
                <input
                  value={nextNote}
                  onChange={(e) => setNextNote(e.target.value)}
                  placeholder="Ex. visite domicile"
                />
              </label>
            </div>
            <button
              className="btn btn-primary btn-sm"
              disabled={nextActionMutation.isPending}
            >
              Enregistrer
            </button>
          </form>
        </Card>

        <Card title="Garanties & dations">
          {!c.guarantees?.length && !c.dation_requests?.length ? (
            <p className="muted small">Aucune garantie ni dation liée.</p>
          ) : (
            <>
              {!!c.guarantees?.length && (
                <ul className="timeline-list" style={{ marginBottom: 12 }}>
                  {c.guarantees.map((g) => (
                    <li key={g.id}>
                      <Link to={`/garanties/${g.id}`}>
                        {g.guarantee_type_display}
                      </Link>
                      {" · "}
                      <Badge value={g.status_display} />
                      {g.description ? (
                        <span className="muted small"> — {g.description}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
              {!!c.dation_requests?.length && (
                <ul className="timeline-list">
                  {c.dation_requests.map((d) => (
                    <li key={d.id}>
                      <Link to={`/dations/${d.id}`}>Dation</Link>
                      {" · "}
                      <Badge value={d.status_display} />
                      <span className="muted small">
                        {" "}
                        — {new Date(d.created_at).toLocaleDateString("fr-FR")}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {c.application_id && (
                <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                  <Link
                    className="btn btn-ghost btn-sm"
                    to={`/garanties?application=${c.application_id}`}
                  >
                    Voir garanties
                  </Link>
                  <Link
                    className="btn btn-ghost btn-sm"
                    to={`/dations/nouvelle?application=${c.application_id}`}
                  >
                    Nouvelle dation
                  </Link>
                </div>
              )}
            </>
          )}
        </Card>
      </div>

      <Card title="Échéancier" className="mt-card">
        {!c.installments?.length ? (
          <p className="muted">Aucune échéance.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>N°</th>
                <th>Échéance</th>
                <th className="num">Dû</th>
                <th className="num">Payé</th>
                <th className="num">Reste</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {c.installments.map((i) => (
                <tr key={i.id}>
                  <td>{i.number}</td>
                  <td>{i.due_date}</td>
                  <td className="num">{formatMoney(i.total_due)}</td>
                  <td className="num">{formatMoney(i.amount_paid)}</td>
                  <td className="num">{formatMoney(i.balance)}</td>
                  <td>
                    <Badge value={i.status_display} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <div className="detail-grid" style={{ marginTop: 16 }}>
        <Card title="Actions de relance">
          <form
            className="inline-form"
            style={{
              boxShadow: "none",
              border: 0,
              padding: 0,
              marginBottom: 16,
            }}
            onSubmit={submitAction}
          >
            <div className="form-grid">
              <label className="field">
                <span>Type</span>
                <select
                  value={actionType}
                  onChange={(e) =>
                    setActionType(e.target.value as CollectionActionType)
                  }
                >
                  {ACTION_TYPES.map((a) => (
                    <option key={a.value} value={a.value}>
                      {a.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Date</span>
                <input
                  type="date"
                  value={actionDate}
                  onChange={(e) => setActionDate(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Résultat</span>
                <input
                  value={actionResult}
                  onChange={(e) => setActionResult(e.target.value)}
                />
              </label>
              <label className="field">
                <span>Suivi prévu</span>
                <input
                  type="date"
                  value={actionFollowUp}
                  onChange={(e) => setActionFollowUp(e.target.value)}
                />
              </label>
            </div>
            <label className="field">
              <span>Commentaire</span>
              <textarea
                rows={2}
                value={actionComment}
                onChange={(e) => setActionComment(e.target.value)}
              />
            </label>
            <button
              className="btn btn-primary btn-sm"
              disabled={actionMutation.isPending}
            >
              Ajouter l&apos;action
            </button>
          </form>
          {!c.actions?.length ? (
            <p className="muted small">Aucune action.</p>
          ) : (
            <ul className="timeline-list">
              {c.actions.map((a) => (
                <li key={a.id}>
                  <strong>
                    {a.action_type_display} — {a.action_date}
                  </strong>
                  {a.result && <span> · {a.result}</span>}
                  {a.next_follow_up_date && (
                    <span className="muted small">
                      {" "}
                      · suivi {a.next_follow_up_date}
                    </span>
                  )}
                  {a.comment && <p className="muted small">{a.comment}</p>}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Promesses de paiement">
          <form
            className="inline-form"
            style={{
              boxShadow: "none",
              border: 0,
              padding: 0,
              marginBottom: 16,
            }}
            onSubmit={submitPromise}
          >
            <div className="form-grid">
              <label className="field">
                <span>Montant</span>
                <input
                  type="number"
                  min="1"
                  step="0.01"
                  value={promiseAmount}
                  onChange={(e) => setPromiseAmount(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Date promise</span>
                <input
                  type="date"
                  value={promiseDate}
                  onChange={(e) => setPromiseDate(e.target.value)}
                  required
                />
              </label>
            </div>
            <button
              className="btn btn-primary btn-sm"
              disabled={promiseMutation.isPending}
            >
              Enregistrer la promesse
            </button>
          </form>
          {!c.promises?.length ? (
            <p className="muted small">Aucune promesse.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th className="num">Montant</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {c.promises.map((p) => (
                  <tr key={p.id}>
                    <td>{p.promised_date}</td>
                    <td className="num">{formatMoney(p.amount)}</td>
                    <td>
                      <Badge value={p.status_display} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <div className="detail-grid" style={{ marginTop: 16 }}>
        <Card title="Relances">
          <p className="muted small" style={{ marginBottom: 10 }}>
            Envoi immédiat (force les préférences filiale). SMS = stub
            journalisé.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={reminderMutation.isPending || c.stage === "CLOSED"}
              onClick={() => reminderMutation.mutate("EMAIL")}
            >
              <Mail size={14} /> Relancer e-mail
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={reminderMutation.isPending || c.stage === "CLOSED"}
              onClick={() => reminderMutation.mutate("SMS")}
            >
              <MessageSquare size={14} /> Relancer SMS
            </button>
          </div>
        </Card>

        {canRestructure && c.stage !== "CLOSED" && c.loan_status === "ACTIVE" && (
          <Card title="Restructuration">
            <form
              className="inline-form"
              style={{ boxShadow: "none", border: 0, padding: 0 }}
              onSubmit={(e) => {
                e.preventDefault();
                if (
                  !window.confirm(
                    "Remplacer les échéances non soldées par un nouvel échéancier ?",
                  )
                ) {
                  return;
                }
                setSuccess(null);
                restructureMutation.mutate();
              }}
            >
              <div className="form-grid">
                <label className="field">
                  <span>Nouvelle durée (mois)</span>
                  <input
                    type="number"
                    min={1}
                    value={restructureMonths}
                    onChange={(e) => setRestructureMonths(e.target.value)}
                    required
                  />
                </label>
                <label className="field">
                  <span>Nouveau taux % (optionnel)</span>
                  <input
                    type="number"
                    step="0.001"
                    value={restructureRate}
                    onChange={(e) => setRestructureRate(e.target.value)}
                    placeholder="inchangé"
                  />
                </label>
                <label className="field">
                  <span>Motif</span>
                  <input
                    value={restructureReason}
                    onChange={(e) => setRestructureReason(e.target.value)}
                  />
                </label>
              </div>
              <p className="muted small">
                Capital restant dû : {formatMoney(c.outstanding_principal || "0")}
              </p>
              <button
                className="btn btn-primary btn-sm"
                disabled={restructureMutation.isPending}
              >
                Appliquer la restructuration
              </button>
            </form>
            {!!c.restructures?.length && (
              <ul className="timeline-list" style={{ marginTop: 12 }}>
                {c.restructures.map((r) => (
                  <li key={r.id}>
                    <strong>{r.effective_date}</strong>
                    <span className="muted small">
                      {" "}
                      · {r.new_duration_months} mois ·{" "}
                      {formatMoney(r.outstanding_principal)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        )}
      </div>

      {(canWriteOff || canLitigation) && (
        <div className="detail-grid" style={{ marginTop: 16 }}>
          {canWriteOff && c.loan_status === "ACTIVE" && (
            <Card title="Passage en perte">
              <p className="muted small">
                Met le prêt en statut « Passé en perte / défaut » et clôture le
                dossier. Les échéances restent pour l&apos;historique.
              </p>
              <label className="field">
                <span>Motif</span>
                <input
                  value={writeOffReason}
                  onChange={(e) => setWriteOffReason(e.target.value)}
                  placeholder="Irrécouvrable / décision comité…"
                />
              </label>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{ marginTop: 8 }}
                disabled={writeOffMutation.isPending}
                onClick={() => {
                  if (
                    !window.confirm(
                      "Confirmer le passage en perte de ce prêt ?",
                    )
                  ) {
                    return;
                  }
                  setSuccess(null);
                  writeOffMutation.mutate();
                }}
              >
                Passer en perte
              </button>
              {!!c.write_offs?.length && (
                <ul className="timeline-list" style={{ marginTop: 12 }}>
                  {c.write_offs.map((w) => (
                    <li key={w.id}>
                      <strong>
                        {w.write_off_date} — {formatMoney(w.amount)}
                      </strong>
                      {w.reason && (
                        <p className="muted small">{w.reason}</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )}

          {canLitigation && (
            <Card title="Contentieux">
              <p className="muted small">
                Procédures judiciaires : cabinets, audiences, pièces, frais et
                saisies.
              </p>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                style={{ marginBottom: 12 }}
                disabled={createLitigation.isPending}
                onClick={() => createLitigation.mutate()}
              >
                Nouvelle procédure
              </button>
              <ul className="timeline-list">
                {(c.litigations || (c.litigation ? [c.litigation] : [])).map(
                  (lit) => (
                    <li key={lit.id}>
                      <Link to={`/recouvrement/${id}/contentieux/${lit.id}`}>
                        <strong>
                          {lit.title || lit.case_reference || "Procédure"}
                        </strong>
                      </Link>
                      {" · "}
                      <Badge value={lit.status_display} />
                      {lit.hearing_date && (
                        <span className="muted small">
                          {" "}
                          · audience {lit.hearing_date}
                        </span>
                      )}
                      {lit.law_firm_detail?.name && (
                        <span className="muted small">
                          {" "}
                          · {lit.law_firm_detail.name}
                        </span>
                      )}
                    </li>
                  ),
                )}
                {!c.litigations?.length && !c.litigation && (
                  <li className="muted small">Aucune procédure.</li>
                )}
              </ul>
              <Link
                className="btn btn-ghost btn-sm"
                to="/intervenants-juridiques"
                style={{ marginTop: 8 }}
              >
                Intervenants juridiques
              </Link>
            </Card>
          )}
        </div>
      )}

      <Card title="Historique des stades" className="mt-card">
        {!c.stage_history?.length ? (
          <p className="muted small">Aucun changement de stade.</p>
        ) : (
          <ul className="timeline-list">
            {c.stage_history.map((h) => (
              <li key={h.id}>
                <strong>
                  {h.from_stage_display} → {h.to_stage_display}
                </strong>
                <span className="muted small">
                  {" "}
                  — {new Date(h.created_at).toLocaleString("fr-FR")}
                  {h.automatic ? " · auto" : ""}
                  {h.changed_by_name ? ` · ${h.changed_by_name}` : ""}
                </span>
                {h.reason && <p className="muted small">{h.reason}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Historique des encaissements" className="mt-card">
        {!c.repayments?.length ? (
          <p className="muted">Aucun encaissement.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Date</th>
                <th className="num">Montant</th>
                <th>Référence</th>
              </tr>
            </thead>
            <tbody>
              {c.repayments.map((r) => (
                <tr key={r.id}>
                  <td>{r.payment_date}</td>
                  <td className="num">{formatMoney(r.amount)}</td>
                  <td>{r.reference || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

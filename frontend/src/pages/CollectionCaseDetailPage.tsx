import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CircleDollarSign } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type {
  CollectionActionType,
  CollectionCase,
  CollectionStage,
  PromiseStatus,
} from "@/api/types";
import {
  Badge,
  Card,
  PageHeader,
  Spinner,
  formatMoney,
} from "@/components/ui";

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
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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

  const [promiseAmount, setPromiseAmount] = useState("");
  const [promiseDate, setPromiseDate] = useState("");

  const caseQuery = useQuery({
    queryKey: ["collection-case", id],
    queryFn: async () =>
      (await api.get<CollectionCase>(`/collection-cases/${id}/`)).data,
    enabled: !!id,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["collection-case", id] });
    qc.invalidateQueries({ queryKey: ["collection-cases"] });
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
        })
      ).data,
    onSuccess: () => {
      setActionResult("");
      setActionComment("");
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

  if (caseQuery.isLoading || !caseQuery.data) {
    return <Spinner />;
  }

  const c = caseQuery.data;

  return (
    <div>
      <PageHeader
        icon={CircleDollarSign}
        title={`Recouvrement — ${c.application_reference || c.client_name}`}
        subtitle={`${c.client_name} · ${c.agency_name}`}
        actions={
          <Link to="/recouvrement" className="btn btn-ghost btn-sm">
            <ArrowLeft size={14} /> Retour
          </Link>
        }
      />

      {success && <div className="form-success" style={{ marginBottom: 12 }}>{success}</div>}
      {error && <div className="form-error" style={{ marginBottom: 12 }}>{error}</div>}

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
          </dl>
        </Card>

        <Card title="Nouvel encaissement">
          <form className="inline-form" style={{ boxShadow: "none", border: 0, padding: 0 }} onSubmit={submitPay}>
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

      <Card title="Échéancier">
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
            style={{ boxShadow: "none", border: 0, padding: 0, marginBottom: 16 }}
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
                  {a.comment && <p className="muted small">{a.comment}</p>}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Promesses de paiement">
          <form
            className="inline-form"
            style={{ boxShadow: "none", border: 0, padding: 0, marginBottom: 16 }}
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

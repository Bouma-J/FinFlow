import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, GitBranch, Pencil, Power, Trash2, X } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type {
  Paginated,
  Role,
  WorkflowDefinition,
  WorkflowStep,
} from "@/api/types";
import { WORKFLOW_LABELS } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  Badge,
  Card,
  PageHeader,
  QueryStatus,
  TenantScopeNotice,
} from "@/components/ui";

type StepForm = {
  name: string;
  order: number;
  required_group: string;
  step_kind: string;
  sla_hours: number;
  min_amount: string;
  max_amount: string;
  allow_return: boolean;
};

const EMPTY_STEP: StepForm = {
  name: "",
  order: 1,
  required_group: "",
  step_kind: "CONSULTATIVE",
  sla_hours: 48,
  min_amount: "",
  max_amount: "",
  allow_return: true,
};

function parseApiError(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: { errors?: unknown } } })?.response
    ?.data;
  const errors = data?.errors;
  if (typeof errors === "string") return errors;
  if (Array.isArray(errors) && errors.length > 0) return String(errors[0]);
  if (errors && typeof errors === "object") {
    const obj = errors as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    const flat = Object.values(obj).flat();
    if (flat.length > 0) return String(flat[0]);
  }
  return fallback;
}

function stepToForm(s: WorkflowStep): StepForm {
  return {
    name: s.name,
    order: s.order,
    required_group: s.required_group ? String(s.required_group) : "",
    step_kind: s.step_kind,
    sla_hours: s.sla_hours ?? 48,
    min_amount: s.min_amount ?? "",
    max_amount: s.max_amount ?? "",
    allow_return: s.allow_return !== false,
  };
}

function formToPayload(form: StepForm) {
  return {
    name: form.name,
    order: form.order,
    required_group: Number(form.required_group),
    step_kind: form.step_kind,
    sla_hours: form.sla_hours,
    min_amount: form.min_amount || null,
    max_amount: form.max_amount || null,
    allow_return: form.allow_return,
  };
}

export function AdminWorkflowPage() {
  const { user, activeTenant } = useAuth();
  const qc = useQueryClient();
  const needsTenant = user?.is_group_level && !activeTenant;

  const [def, setDef] = useState({
    code: "",
    name: "",
    version: 1,
    target_type: "CREDIT",
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [stepError, setStepError] = useState<string | null>(null);
  const [editingStepId, setEditingStepId] = useState<string | null>(null);
  const [step, setStep] = useState<StepForm>({ ...EMPTY_STEP });
  const [editStep, setEditStep] = useState<StepForm>({ ...EMPTY_STEP });

  const defs = useQuery({
    queryKey: ["workflow-definitions", activeTenant],
    queryFn: async () =>
      (await api.get<Paginated<WorkflowDefinition>>("/workflow-definitions/"))
        .data,
    enabled: !needsTenant,
  });
  const tenants = useQuery({
    queryKey: ["tenants"],
    queryFn: async () =>
      (await api.get<Paginated<{ id: string; code: string; name: string }>>("/tenants/")).data,
    enabled: !!user?.is_group_level,
  });
  const roles = useQuery({
    queryKey: ["admin-roles", activeTenant],
    queryFn: async () => (await api.get<Paginated<Role>>("/roles/")).data,
    enabled: !needsTenant,
  });

  const bootstrapRoles = useMutation({
    mutationFn: async () => {
      const tenantId = activeTenant ?? user?.tenant;
      if (!tenantId) throw new Error("Aucune filiale sélectionnée.");
      return (await api.post(`/tenants/${tenantId}/bootstrap/`)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-roles"] });
      setStepError(null);
    },
    onError: (err) =>
      setStepError(
        parseApiError(err, "Impossible d'initialiser les rôles par défaut."),
      ),
  });

  const createDef = useMutation({
    mutationFn: async () =>
      (await api.post("/workflow-definitions/", def)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflow-definitions"] });
      setDef({ code: "", name: "", version: 1, target_type: "CREDIT" });
    },
  });
  const createStep = useMutation({
    mutationFn: async () =>
      (
        await api.post("/workflow-steps/", {
          definition: selectedId,
          ...formToPayload(step),
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflow-definitions"] });
      setStep({ ...step, name: "", order: step.order + 1 });
      setStepError(null);
    },
    onError: (err) =>
      setStepError(parseApiError(err, "Ajout impossible. Vérifiez les champs.")),
  });

  const updateStep = useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: ReturnType<typeof formToPayload>;
    }) => (await api.patch(`/workflow-steps/${id}/`, data)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflow-definitions"] });
      setEditingStepId(null);
      setStepError(null);
    },
    onError: (err) =>
      setStepError(
        parseApiError(err, "Modification impossible pour cette étape."),
      ),
  });

  const deleteStep = useMutation({
    mutationFn: async (stepId: string) =>
      (await api.delete(`/workflow-steps/${stepId}/`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflow-definitions"] });
      setStepError(null);
      if (editingStepId) setEditingStepId(null);
    },
    onError: (err) =>
      setStepError(
        parseApiError(
          err,
          "Suppression impossible. Ce circuit est peut-être déjà utilisé.",
        ),
      ),
  });

  const cloneDef = useMutation({
    mutationFn: async (id: string) =>
      (
        await api.post<WorkflowDefinition>(
          `/workflow-definitions/${id}/clone/`,
          { deactivate_source: true },
        )
      ).data,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["workflow-definitions"] });
      setSelectedId(data.id);
      setEditingStepId(null);
      setStepError(null);
      setStep({
        ...EMPTY_STEP,
        order: Math.max(1, data.steps.length + 1),
      });
    },
    onError: (err) =>
      setStepError(parseApiError(err, "Duplication impossible.")),
  });

  const toggleActive = useMutation({
    mutationFn: async ({
      id,
      is_active,
    }: {
      id: string;
      is_active: boolean;
    }) =>
      (
        await api.patch<WorkflowDefinition>(`/workflow-definitions/${id}/`, {
          is_active,
        })
      ).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflow-definitions"] });
      setStepError(null);
    },
    onError: (err) =>
      setStepError(parseApiError(err, "Changement d'état impossible.")),
  });

  function removeStep(stepId: string, stepName: string) {
    if (
      !window.confirm(
        `Supprimer l'étape « ${stepName} » ? Cette action est irréversible.`,
      )
    ) {
      return;
    }
    setStepError(null);
    deleteStep.mutate(stepId);
  }

  function startEdit(s: WorkflowStep) {
    setEditingStepId(s.id);
    setEditStep(stepToForm(s));
    setStepError(null);
  }

  if (needsTenant) {
    return (
      <div>
        <PageHeader
          icon={GitBranch}
          title="Circuits d'approbation"
          subtitle="Par filiale"
        />
        <TenantScopeNotice />
      </div>
    );
  }

  const selected = defs.data?.results.find((d) => d.id === selectedId);
  const roleName = (id: number | null) =>
    roles.data?.results.find((r) => r.id === id)?.name ?? "—";

  const scopeLabel = user?.is_group_level
    ? tenants.data?.results.find((t) => t.id === activeTenant)?.name ?? "filiale sélectionnée"
    : "votre filiale";

  const hasRoles = (roles.data?.results.length ?? 0) > 0;
  const circuitEditable = (d: WorkflowDefinition) => d.is_used !== true;

  return (
    <div>
      <PageHeader
        icon={GitBranch}
        title="Circuits d'approbation"
        subtitle={`Étapes, rôles habilités, seuils et SLA — ${scopeLabel}`}
      />

      {user?.is_group_level && activeTenant && (
        <p className="muted small" style={{ marginBottom: 12 }}>
          Paramétrage de la filiale <strong>{scopeLabel}</strong>. Chaque filiale
          possède ses propres circuits, indépendants des autres.
        </p>
      )}

      {!hasRoles && roles.data && (
        <Card title="Configuration requise">
          <p className="muted small">
            Avant d'ajouter des étapes, cette filiale doit disposer de rôles
            (Chargé d'affaire, Chef d'agence, Comité de crédit, etc.).
          </p>
          <div className="row-actions" style={{ marginTop: 8 }}>
            {user?.is_group_level && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={bootstrapRoles.isPending}
                onClick={() => bootstrapRoles.mutate()}
              >
                Créer les rôles par défaut
              </button>
            )}
            <a className="btn btn-ghost btn-sm" href="/admin/roles">
              Gérer les rôles
            </a>
          </div>
        </Card>
      )}

      <form
        className="inline-form"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          createDef.mutate();
        }}
      >
        <div className="form-grid">
          <label className="field">
            <span>Code</span>
            <input
              value={def.code}
              onChange={(e) => setDef({ ...def, code: e.target.value })}
              required
            />
          </label>
          <label className="field">
            <span>Nom</span>
            <input
              value={def.name}
              onChange={(e) => setDef({ ...def, name: e.target.value })}
              required
            />
          </label>
          <label className="field">
            <span>Version</span>
            <input
              type="number"
              value={def.version}
              onChange={(e) =>
                setDef({ ...def, version: Number(e.target.value) })
              }
            />
          </label>
          <label className="field">
            <span>Type de processus</span>
            <select
              value={def.target_type}
              onChange={(e) =>
                setDef({ ...def, target_type: e.target.value })
              }
            >
              {Object.entries(WORKFLOW_LABELS.target_type).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button className="btn btn-primary btn-sm" disabled={createDef.isPending}>
          Créer le circuit
        </button>
      </form>

      <div className="detail-grid stacked">
        <Card title="Circuits">
          <QueryStatus
            isLoading={defs.isLoading}
            isError={defs.isError}
            isEmpty={!defs.data?.results.length}
            emptyMessage="Aucun circuit."
            onRetry={() => defs.refetch()}
          >
            <table className="table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Nom</th>
                  <th>Processus</th>
                  <th className="num">Étapes</th>
                  <th>Statut</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {(defs.data?.results ?? []).map((d) => (
                  <tr key={d.id}>
                    <td>
                      {d.code} v{d.version}
                    </td>
                    <td>{d.name}</td>
                    <td>
                      {WORKFLOW_LABELS.target_type[d.target_type] ||
                        d.target_type}
                    </td>
                    <td className="num">{d.steps.length}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <Badge
                          value={d.is_active ? "success" : "info"}
                          label={d.is_active ? "Actif" : "Inactif"}
                        />
                        <Badge
                          value={circuitEditable(d) ? "success" : "warning"}
                          label={circuitEditable(d) ? "Modifiable" : "Utilisé"}
                        />
                        {d.decision_gaps && (
                          <Badge
                            value="DECISION_GAP"
                            tone="danger"
                            label="Sans décideur"
                            title={
                              `Montants sans étape décisionnelle : ` +
                              `${d.decision_gaps.label}. Les dossiers concernés ` +
                              `seraient approuvés sur de simples avis consultatifs.`
                            }
                          />
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="row-actions" style={{ gap: 4 }}>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => {
                            setSelectedId(d.id);
                            setEditingStepId(null);
                            setStepError(null);
                            setStep({
                              ...EMPTY_STEP,
                              order: Math.max(1, d.steps.length + 1),
                            });
                          }}
                        >
                          Étapes
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          title={
                            d.is_active
                              ? "Désactiver ce circuit"
                              : "Activer ce circuit"
                          }
                          disabled={toggleActive.isPending}
                          onClick={() =>
                            toggleActive.mutate({
                              id: d.id,
                              is_active: !d.is_active,
                            })
                          }
                        >
                          <Power size={14} />
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          title="Dupliquer en nouvelle version"
                          disabled={cloneDef.isPending}
                          onClick={() => {
                            if (
                              !window.confirm(
                                `Dupliquer « ${d.code} » en v${d.version + 1} ?` +
                                  (d.is_active
                                    ? " La version actuelle sera désactivée."
                                    : ""),
                              )
                            ) {
                              return;
                            }
                            cloneDef.mutate(d.id);
                          }}
                        >
                          <Copy size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </QueryStatus>
        </Card>

        <Card title={selected ? `Étapes — ${selected.code}` : "Étapes"}>
          {!selected ? (
            <p className="muted">Sélectionnez un circuit.</p>
          ) : (
            <>
              <div className="workflow-step-line" style={{ marginBottom: 12 }}>
                <Badge
                  value={circuitEditable(selected) ? "success" : "warning"}
                  label={circuitEditable(selected) ? "Circuit modifiable" : "Circuit utilisé"}
                />
                {circuitEditable(selected) ? (
                  <span className="muted small">
                    Circuit non utilisé : vous pouvez ajouter, modifier ou supprimer
                    des étapes.
                  </span>
                ) : (
                  <span className="muted small">
                    Ce circuit a servi pour des dossiers. Dupliquez-le en nouvelle
                    version pour modifier les étapes.
                  </span>
                )}
              </div>
              <p className="muted small" style={{ marginBottom: 12 }}>
                Plusieurs étapes avec le <strong>même numéro d&apos;ordre</strong>{" "}
                s&apos;ouvrent en parallèle ; le circuit avance quand toutes sont
                traitées.
              </p>

              <ol className="workflow-steps">
                {selected.steps
                  .slice()
                  .sort((a, b) => a.order - b.order)
                  .map((s) => (
                    <li key={s.id}>
                      <div className="workflow-step-line" style={{ width: "100%" }}>
                        <span>
                          {s.order}. {s.name}
                        </span>
                        <Badge value="info" label={roleName(s.required_group)} />
                        <Badge
                          value={s.step_kind === "DECISIONAL" ? "warning" : "info"}
                          label={
                            WORKFLOW_LABELS.step_kind[s.step_kind] || s.step_kind
                          }
                        />
                        <span className="muted small">SLA {s.sla_hours}h</span>
                        {!s.allow_return && (
                          <Badge value="warning" label="Sans retour" />
                        )}
                        {circuitEditable(selected) && (
                          <span style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              title="Modifier cette étape"
                              disabled={updateStep.isPending}
                              onClick={() => startEdit(s)}
                            >
                              <Pencil />
                            </button>
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm"
                              title="Supprimer cette étape"
                              disabled={deleteStep.isPending}
                              onClick={() => removeStep(s.id, s.name)}
                            >
                              <Trash2 />
                            </button>
                          </span>
                        )}
                      </div>
                    </li>
                  ))}
                {selected.steps.length === 0 && (
                  <li className="muted">Aucune étape.</li>
                )}
              </ol>

              {stepError && <div className="form-error">{stepError}</div>}

              {editingStepId && circuitEditable(selected) && (
                <Card title="Modifier l'étape">
                  <form
                    className="stack"
                    onSubmit={(e: FormEvent) => {
                      e.preventDefault();
                      updateStep.mutate({
                        id: editingStepId,
                        data: formToPayload(editStep),
                      });
                    }}
                  >
                    <StepFields
                      form={editStep}
                      setForm={setEditStep}
                      roles={roles.data?.results ?? []}
                    />
                    <div className="row-actions">
                      <button
                        className="btn btn-primary btn-sm"
                        disabled={updateStep.isPending}
                      >
                        Enregistrer
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => setEditingStepId(null)}
                      >
                        <X /> Annuler
                      </button>
                    </div>
                  </form>
                </Card>
              )}

              {circuitEditable(selected) && hasRoles && (
                <form
                  className="stack"
                  style={{ marginTop: 12 }}
                  onSubmit={(e: FormEvent) => {
                    e.preventDefault();
                    createStep.mutate();
                  }}
                >
                  <p className="field-legend">Ajouter une étape</p>
                  <StepFields
                    form={step}
                    setForm={setStep}
                    roles={roles.data?.results ?? []}
                  />
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={createStep.isPending}
                  >
                    Ajouter l'étape
                  </button>
                </form>
              )}
            </>
          )}
        </Card>
      </div>
    </div>
  );
}

function StepFields({
  form,
  setForm,
  roles,
}: {
  form: StepForm;
  setForm: (f: StepForm) => void;
  roles: Role[];
}) {
  return (
    <div className="page-shell form-grid">
      <label className="field">
        <span>Nom de l'étape</span>
        <input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
      </label>
      <label className="field">
        <span>Ordre</span>
        <input
          type="number"
          value={form.order}
          onChange={(e) => setForm({ ...form, order: Number(e.target.value) })}
        />
      </label>
      <label className="field">
        <span>Rôle habilité</span>
        <select
          value={form.required_group}
          onChange={(e) => setForm({ ...form, required_group: e.target.value })}
          required
        >
          <option value="">— choisir —</option>
          {roles.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Nature de l'étape</span>
        <select
          value={form.step_kind}
          onChange={(e) => setForm({ ...form, step_kind: e.target.value })}
        >
          <option value="CONSULTATIVE">Consultative</option>
          <option value="DECISIONAL">Décisionnelle</option>
        </select>
      </label>
      <label className="field">
        <span>SLA (heures)</span>
        <input
          type="number"
          value={form.sla_hours}
          onChange={(e) => setForm({ ...form, sla_hours: Number(e.target.value) })}
        />
      </label>
      <label className="field">
        <span>Montant plancher</span>
        <input
          type="number"
          value={form.min_amount}
          onChange={(e) => setForm({ ...form, min_amount: e.target.value })}
        />
      </label>
      <label className="field">
        <span>Montant plafond</span>
        <input
          type="number"
          value={form.max_amount}
          onChange={(e) => setForm({ ...form, max_amount: e.target.value })}
        />
      </label>
      <label className="checkbox" style={{ alignSelf: "end" }}>
        <input
          type="checkbox"
          checked={form.allow_return}
          onChange={(e) =>
            setForm({ ...form, allow_return: e.target.checked })
          }
        />
        <span>Autoriser le renvoi à cette étape</span>
      </label>
    </div>
  );
}

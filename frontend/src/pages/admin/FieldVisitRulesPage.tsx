import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MapPin, Plus, Trash2, Edit2, Save, X } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import type { FieldVisitRule, Paginated } from "@/api/types";
import { ErrorState, PageHeader, Spinner } from "@/components/ui";

const EMPTY_RULE: Omit<FieldVisitRule, "id" | "created_at" | "updated_at" | "blocking_stage_display"> = {
  name: "",
  is_active: true,
  priority: 0,
  client_type: "",
  individual_profile: "",
  amount_min: null,
  amount_max: null,
  required_role: "",
  blocking_stage: "SUBMIT",
};

export function AdminFieldVisitRulesPage() {
  const qc = useQueryClient();
  const [editing, setEditing] = useState<FieldVisitRule | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(EMPTY_RULE);

  const rules = useQuery({
    queryKey: ["field-visit-rules"],
    queryFn: async () =>
      (await api.get<Paginated<FieldVisitRule>>("/field-visit-rules/")).data,
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) =>
      await api.delete(`/field-visit-rules/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["field-visit-rules"] });
    },
  });

  const saveMutation = useMutation({
    mutationFn: async (data: typeof form) => {
      if (editing) {
        return await api.patch(`/field-visit-rules/${editing.id}/`, data);
      } else {
        return await api.post("/field-visit-rules/", data);
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["field-visit-rules"] });
      setCreating(false);
      setEditing(null);
      setForm(EMPTY_RULE);
    },
  });

  const handleEdit = (rule: FieldVisitRule) => {
    setEditing(rule);
    setForm({
      name: rule.name,
      is_active: rule.is_active,
      priority: rule.priority,
      client_type: rule.client_type,
      individual_profile: rule.individual_profile,
      amount_min: rule.amount_min,
      amount_max: rule.amount_max,
      required_role: rule.required_role,
      blocking_stage: rule.blocking_stage,
    });
    setCreating(false);
  };

  const handleCreate = () => {
    setCreating(true);
    setEditing(null);
    setForm(EMPTY_RULE);
  };

  const handleCancel = () => {
    setCreating(false);
    setEditing(null);
    setForm(EMPTY_RULE);
  };

  const handleSave = () => {
    saveMutation.mutate(form);
  };

  if (rules.isLoading) {
    return <Spinner />;
  }

  if (rules.isError) {
    return <ErrorState message="Erreur lors du chargement des règles." />;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <PageHeader
        title="Règles de Visite Terrain"
        subtitle="Configurez les règles conditionnelles pour obliger les visites terrain selon le profil client, montant, et rôle."
        icon={<MapPin size={32} />}
      />

      <div className="mt-6 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Règles actives ({rules.data?.results.length || 0})
          </h2>
          <button
            onClick={handleCreate}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus size={20} />
            Nouvelle règle
          </button>
        </div>

        {(creating || editing) && (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
            <h3 className="text-md font-semibold mb-4">
              {editing ? "Modifier la règle" : "Créer une règle"}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nom de la règle *
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Ex: Particulier indépendant 0-100K : visite par chargé de compte"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Type de client
                </label>
                <select
                  value={form.client_type}
                  onChange={(e) =>
                    setForm({ ...form, client_type: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="">Tous types</option>
                  <option value="INDIVIDUAL">Particulier</option>
                  <option value="CORPORATE">Entreprise</option>
                  <option value="PROFESSIONAL">Groupement</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Profil particulier
                </label>
                <select
                  value={form.individual_profile}
                  onChange={(e) =>
                    setForm({ ...form, individual_profile: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="">Tous profils</option>
                  <option value="SALARIE">Salarié</option>
                  <option value="INDEPENDANT">Indépendant</option>
                  <option value="RETRAITE">Retraité</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Montant minimum
                </label>
                <input
                  type="number"
                  value={form.amount_min || ""}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      amount_min: e.target.value ? e.target.value : null,
                    })
                  }
                  placeholder="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Montant maximum
                </label>
                <input
                  type="number"
                  value={form.amount_max || ""}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      amount_max: e.target.value ? e.target.value : null,
                    })
                  }
                  placeholder="Illimité"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Rôle requis *
                </label>
                <input
                  type="text"
                  value={form.required_role}
                  onChange={(e) =>
                    setForm({ ...form, required_role: e.target.value })
                  }
                  placeholder="Ex: CHARGE_COMPTE, RESP_EXPLOITATION"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Étape de blocage *
                </label>
                <select
                  value={form.blocking_stage}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      blocking_stage: e.target.value as
                        | "SUBMIT"
                        | "OPINION"
                        | "APPROVAL",
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  <option value="SUBMIT">À la soumission</option>
                  <option value="OPINION">À la saisie de l'avis</option>
                  <option value="APPROVAL">À l'approbation</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Priorité
                </label>
                <input
                  type="number"
                  value={form.priority}
                  onChange={(e) =>
                    setForm({ ...form, priority: parseInt(e.target.value) || 0 })
                  }
                  placeholder="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={form.is_active}
                  onChange={(e) =>
                    setForm({ ...form, is_active: e.target.checked })
                  }
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded"
                />
                <label
                  htmlFor="is_active"
                  className="ml-2 text-sm font-medium text-gray-700"
                >
                  Règle active
                </label>
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <button
                onClick={handleSave}
                disabled={!form.name || !form.required_role}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:bg-gray-400"
              >
                <Save size={20} />
                Enregistrer
              </button>
              <button
                onClick={handleCancel}
                className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                <X size={20} />
                Annuler
              </button>
            </div>
          </div>
        )}

        {rules.data?.results.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            Aucune règle configurée. Créez-en une pour commencer.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                    Priorité
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                    Nom
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                    Type Client
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                    Montant
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                    Rôle Requis
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                    Blocage
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                    Statut
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {rules.data?.results.map((rule) => (
                  <tr key={rule.id} className="border-b border-gray-100">
                    <td className="px-4 py-3 text-sm">{rule.priority}</td>
                    <td className="px-4 py-3 text-sm font-medium">
                      {rule.name}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {rule.client_type || "Tous"}
                      {rule.individual_profile && ` - ${rule.individual_profile}`}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {rule.amount_min && rule.amount_max
                        ? `${rule.amount_min} - ${rule.amount_max}`
                        : rule.amount_min
                          ? `≥ ${rule.amount_min}`
                          : rule.amount_max
                            ? `≤ ${rule.amount_max}`
                            : "Tous montants"}
                    </td>
                    <td className="px-4 py-3 text-sm">{rule.required_role}</td>
                    <td className="px-4 py-3 text-sm">
                      {rule.blocking_stage_display}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`px-2 py-1 rounded-full text-xs ${
                          rule.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {rule.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-right">
                      <button
                        onClick={() => handleEdit(rule)}
                        className="inline-flex items-center gap-1 px-2 py-1 text-blue-600 hover:bg-blue-50 rounded"
                      >
                        <Edit2 size={16} />
                        Modifier
                      </button>
                      <button
                        onClick={() => {
                          if (
                            confirm(
                              `Supprimer la règle "${rule.name}" ? Cette action est irréversible.`
                            )
                          ) {
                            deleteMutation.mutate(rule.id);
                          }
                        }}
                        className="inline-flex items-center gap-1 px-2 py-1 ml-2 text-red-600 hover:bg-red-50 rounded"
                      >
                        <Trash2 size={16} />
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

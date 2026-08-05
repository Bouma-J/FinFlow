import { useMutation } from "@tanstack/react-query";
import { Calculator, Play } from "lucide-react";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { SimulationResult } from "@/api/types";
import { Card, PageHeader, formatMoney } from "@/components/ui";

export function SimulatorPage() {
  const [form, setForm] = useState({
    amount: "1000000",
    annual_rate: "12.5",
    months: 12,
  });

  const sim = useMutation({
    mutationFn: async () =>
      (await api.post<SimulationResult>("/credit-applications/simulate/", form))
        .data,
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    sim.mutate();
  }

  const result = sim.data;

  return (
    <div>
      <PageHeader
        icon={Calculator}
        title="Simulateur de crédit"
        subtitle="Échéancier à mensualités constantes"
      />
      <div className="detail-grid">
        <Card title="Paramètres">
          <form onSubmit={submit} className="stack">
            <label className="field">
              <span>Montant</span>
              <input
                type="number"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Taux annuel (%)</span>
              <input
                type="number"
                step="0.001"
                value={form.annual_rate}
                onChange={(e) =>
                  setForm({ ...form, annual_rate: e.target.value })
                }
              />
            </label>
            <label className="field">
              <span>Durée (mois)</span>
              <input
                type="number"
                value={form.months}
                onChange={(e) =>
                  setForm({ ...form, months: Number(e.target.value) })
                }
              />
            </label>
            <button className="btn btn-primary" disabled={sim.isPending}>
              <Play />
              Simuler
            </button>
          </form>
        </Card>

        <Card title="Résultat">
          {!result ? (
            <p className="muted">Lancez une simulation.</p>
          ) : (
            <>
              <div className="stat-grid tight">
                <div className="stat-card">
                  <span className="stat-label">Mensualité</span>
                  <span className="stat-value">
                    {formatMoney(result.monthly_payment)}
                  </span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Total remboursé</span>
                  <span className="stat-value">
                    {formatMoney(result.total_repayment)}
                  </span>
                </div>
                <div className="stat-card tone-warning">
                  <span className="stat-label">Intérêts</span>
                  <span className="stat-value">
                    {formatMoney(result.total_interest)}
                  </span>
                </div>
              </div>
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Échéance</th>
                      <th className="num">Capital</th>
                      <th className="num">Intérêts</th>
                      <th className="num">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.schedule.map((row) => (
                      <tr key={row.number}>
                        <td>{row.number}</td>
                        <td>{row.due_date}</td>
                        <td className="num">{formatMoney(row.principal)}</td>
                        <td className="num">{formatMoney(row.interest)}</td>
                        <td className="num">{formatMoney(row.total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}

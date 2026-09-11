import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Banknote,
  FileUp,
  Gavel,
  HandCoins,
  Landmark,
  MessageSquareText,
  Plus,
  Receipt,
  RefreshCw,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import type {
  ApprovalTask,
  Client,
  CreditApplication,
  DationFee,
  DationRequest,
  GedDocument,
  Guarantee,
  Paginated,
} from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import {
  PERM_CLIENTS,
  PERM_COLLECTIONS,
  PERM_CREDITS,
  PERM_GUARANTEES,
} from "@/auth/routePerms";
import {
  ClientAutocomplete,
  clientOptionLabel,
} from "@/components/ClientAutocomplete";
import { PermLink } from "@/components/PermLink";
import { DecisionPanel } from "@/components/DecisionPanel";
import {
  AgencyFilter,
  ClientFilterBanner,
  FilterField,
  FilterSelect,
  ListFilters,
  PROCESS_STATUS_OPTIONS,
  SearchInput,
  countActive,
  useClientSearchParam,
} from "@/components/ListFilters";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  PageHeader,
  PaginationBar,
  QueryStatus,
  Spinner,
  formatDate,
  formatMoney,
} from "@/components/ui";

type ExtraAsset = {
  key: string;
  description: string;
  value: string;
  asset_type: string;
};

type DraftFee = {
  key: string;
  fee_type: string;
  label: string;
  amount: string;
  payer: string;
};

type CbsPreview = {
  cbs_client_id: string;
  total_outstanding: string;
  currency: string;
  breakdown: unknown[];
};

const ASSET_TYPES = [
  { value: "REAL_ESTATE", label: "Immobilier" },
  { value: "VEHICLE", label: "Véhicule" },
  { value: "EQUIPMENT", label: "Matériel" },
  { value: "JEWELRY", label: "Bijoux / valeur" },
  { value: "FINANCIAL", label: "Actif financier" },
  { value: "OTHER", label: "Autre" },
];

const FEE_TYPES = [
  { value: "NOTARY", label: "Notaire / acte" },
  { value: "APPRAISAL", label: "Expertise" },
  { value: "REGISTRATION", label: "Enregistrement" },
  { value: "BAILIFF", label: "Huissier" },
  { value: "TRANSFER_TAX", label: "Droits de mutation" },
  { value: "OTHER", label: "Divers" },
];

const DOC_CATS = [
  { value: "DAT_ACTE", label: "Acte de dation" },
  { value: "DAT_PHOTO", label: "Photo du bien" },
  { value: "DAT_EXPERTISE", label: "Expertise" },
  { value: "DAT_TITRE", label: "Titre / carte grise" },
  { value: "DAT_FACTURE", label: "Facture / frais" },
  { value: "DAT_OTHER", label: "Autre" },
];

export function DationsPage() {
  const { user } = useAuth();
  const { clientFilter, clearClientFilter } = useClientSearchParam();
  const canInitiate = hasPerm(user, "guarantees.initiate_dationrequest");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [agency, setAgency] = useState("");

  function setFilter<T>(setter: (v: T) => void) {
    return (value: T) => {
      setter(value);
      setPage(1);
    };
  }

  const list = useQuery({
    queryKey: ["dation-requests", page, search, status, agency, clientFilter],
    queryFn: async () =>
      (
        await api.get<Paginated<DationRequest>>("/dation-requests/", {
          params: {
            page,
            ...(search.trim() ? { search: search.trim() } : {}),
            ...(status ? { status } : {}),
            ...(agency ? { agency } : {}),
            ...(clientFilter ? { client: clientFilter } : {}),
          },
        })
      ).data,
  });

  return (
    <div>
      <PageHeader
        icon={HandCoins}
        title="Dations en paiement"
        subtitle="Biens, frais, pièces jointes, couverture CBS et circuit paramétrable"
        actions={
          canInitiate ? (
            <Link className="btn btn-primary" to="/dations/nouvelle">
              <Plus />
              Nouvelle dation
            </Link>
          ) : undefined
        }
      />

      <ListFilters
        search={
          <SearchInput
            value={search}
            onChange={setFilter(setSearch)}
            placeholder="Référence, client, description du bien…"
          />
        }
        activeCount={countActive(search, status, agency, clientFilter)}
        onReset={() => {
          setSearch("");
          setStatus("");
          setAgency("");
          setPage(1);
          if (clientFilter) clearClientFilter();
        }}
      >
        <FilterField label="Statut" active={!!status}>
          <FilterSelect value={status} onChange={setFilter(setStatus)}>
            {PROCESS_STATUS_OPTIONS.map(([value, label]) => (
              <option key={value || "all"} value={value}>
                {label}
              </option>
            ))}
          </FilterSelect>
        </FilterField>
        <AgencyFilter value={agency} onChange={setFilter(setAgency)} />
      </ListFilters>
      <ClientFilterBanner
        clientId={clientFilter}
        onClear={() => {
          clearClientFilter();
          setPage(1);
        }}
      />

      <QueryStatus
        isLoading={list.isLoading}
        isError={list.isError}
        isEmpty={!list.data?.results.length}
        emptyMessage="Aucune dation ne correspond à ces critères."
        onRetry={() => list.refetch()}
      >
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
            {(list.data?.results ?? []).map((r) => (
              <tr key={r.id}>
                <td>
                  <code>{r.reference || "—"}</code>
                </td>
                <td>{r.client_display}</td>
                <td className="num">
                  {formatMoney(r.cbs_total_outstanding, r.cbs_currency || "XOF")}
                </td>
                <td className="num">
                  {formatMoney(
                    r.assets_total_value ?? r.asset_value,
                    r.cbs_currency || "XOF",
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
          count={list.data?.count ?? 0}
          onPageChange={setPage}
        />
        </>
      </QueryStatus>
    </div>
  );
}

export function DationNewPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const applicationId = searchParams.get("application") || "";
  const clientFromQuery = searchParams.get("client") || "";
  const guaranteeFromQuery = searchParams.get("guarantee") || "";
  const [clientId, setClientId] = useState("");
  const [clientLabel, setClientLabel] = useState("");
  const [applicationRef, setApplicationRef] = useState("");
  const [cbsClientId, setCbsClientId] = useState("");
  const [selectedGuaranteeIds, setSelectedGuaranteeIds] = useState<string[]>(
    [],
  );
  const [extraAssets, setExtraAssets] = useState<ExtraAsset[]>([]);
  const [fees, setFees] = useState<DraftFee[]>([]);
  const [requireFullCoverage, setRequireFullCoverage] = useState(false);
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

  const currency = cbsPreview.data?.currency || "XOF";
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

  const clientFeesTotal = useMemo(
    () =>
      fees
        .filter((f) => f.payer === "CLIENT")
        .reduce((sum, f) => sum + Number(f.amount || 0), 0),
    [fees],
  );
  const claimToCover = claim + clientFeesTotal;
  const covers =
    cbsPreview.data != null
      ? selectedTotal >= claimToCover && claimToCover > 0
      : null;
  const coverageRatio =
    claimToCover > 0
      ? Math.min(100, (selectedTotal / claimToCover) * 100)
      : 0;
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
          application: applicationId || null,
          cbs_client_id: cbsClientId,
          as_draft: true,
          require_full_coverage: requireFullCoverage,
          guarantee_ids: selectedGuaranteeIds,
          additional_assets: extraAssets
            .filter((a) => a.description.trim())
            .map((a) => ({
              description: a.description.trim(),
              value: a.value || null,
              asset_type: a.asset_type || "OTHER",
            })),
          fees: fees
            .filter((f) => Number(f.amount || 0) > 0)
            .map((f) => ({
              fee_type: f.fee_type,
              label: f.label.trim(),
              amount: f.amount,
              payer: f.payer,
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
            : "Création impossible (contrôle CBS, biens ou circuit manquant).",
      );
    },
  });

  function onClientPicked(id: string, label: string, client?: Client | null) {
    setClientId(id);
    setClientLabel(label);
    setSelectedGuaranteeIds([]);
    setExtraAssets([]);
    setError(null);
    setCbsClientId((client?.cbs_client_id || "").trim());
  }

  useEffect(() => {
    if (!applicationId && !clientFromQuery) {
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        let nextClientId = clientFromQuery;
        if (applicationId) {
          const app = (
            await api.get<CreditApplication>(
              `/credit-applications/${applicationId}/`,
            )
          ).data;
          if (cancelled) return;
          setApplicationRef(app.reference || "");
          if (!nextClientId) {
            nextClientId = app.client;
          }
        }
        if (!nextClientId) return;
        const client = (await api.get<Client>(`/clients/${nextClientId}/`)).data;
        if (cancelled) return;
        onClientPicked(client.id, clientOptionLabel(client), client);
      } catch {
        if (!cancelled) {
          setError("Impossible de préremplir le client depuis le dossier.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // Prefill once from the incoming deep-link.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applicationId, clientFromQuery]);

  useEffect(() => {
    if (!guaranteeFromQuery) return;
    const ids = (guarantees.data?.results ?? []).map((g) => g.id);
    if (!ids.includes(guaranteeFromQuery)) return;
    setSelectedGuaranteeIds((prev) =>
      prev.includes(guaranteeFromQuery)
        ? prev
        : [...prev, guaranteeFromQuery],
    );
  }, [guaranteeFromQuery, guarantees.data]);

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
    <div className="page-shell dation-compose">
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
                    initialLabel={clientLabel}
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
                        const busy = Boolean(g.process_busy);
                        const val =
                          g.current_value ||
                          g.value_to_consider ||
                          g.expertise_value;
                        return (
                          <label
                            key={g.id}
                            role="listitem"
                            className={`dation-guarantee-row${checked ? " selected" : ""}${busy ? " muted" : ""}`}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              disabled={busy}
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
                              {busy && (
                                <span className="muted small">
                                  {g.process_busy?.label}
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
                              asset_type: "OTHER",
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
                            <span>Type</span>
                            <select
                              value={asset.asset_type}
                              onChange={(e) => {
                                const v = e.target.value;
                                setExtraAssets((prev) =>
                                  prev.map((a, i) =>
                                    i === idx ? { ...a, asset_type: v } : a,
                                  ),
                                );
                              }}
                            >
                              {ASSET_TYPES.map((t) => (
                                <option key={t.value} value={t.value}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="field">
                            <span>Valeur retenue</span>
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
                      <Receipt size={18} />
                    </span>
                    <div className="form-section-heading">
                      <span className="form-section-title">4. Frais</span>
                      <span className="form-section-desc">
                        Notaire, expertise, enregistrement… Les frais client
                        s’ajoutent à la créance à couvrir.
                      </span>
                    </div>
                    <div className="form-section-action">
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() =>
                          setFees((prev) => [
                            ...prev,
                            {
                              key: `${Date.now()}-${prev.length}`,
                              fee_type: "NOTARY",
                              label: "",
                              amount: "",
                              payer: "CLIENT",
                            },
                          ])
                        }
                      >
                        <Plus size={14} />
                        Ajouter
                      </button>
                    </div>
                  </div>
                  {fees.length === 0 ? (
                    <p className="muted small dation-compose-hint">
                      Optionnel — vous pourrez aussi en ajouter sur la fiche
                      brouillon.
                    </p>
                  ) : (
                    <div className="dation-extra-list">
                      {fees.map((fee, idx) => (
                        <div key={fee.key} className="dation-extra-row">
                          <label className="field">
                            <span>Type</span>
                            <select
                              value={fee.fee_type}
                              onChange={(e) => {
                                const v = e.target.value;
                                setFees((prev) =>
                                  prev.map((f, i) =>
                                    i === idx ? { ...f, fee_type: v } : f,
                                  ),
                                );
                              }}
                            >
                              {FEE_TYPES.map((t) => (
                                <option key={t.value} value={t.value}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="field">
                            <span>Libellé</span>
                            <input
                              value={fee.label}
                              onChange={(e) => {
                                const v = e.target.value;
                                setFees((prev) =>
                                  prev.map((f, i) =>
                                    i === idx ? { ...f, label: v } : f,
                                  ),
                                );
                              }}
                              placeholder="Optionnel"
                            />
                          </label>
                          <label className="field">
                            <span>Montant</span>
                            <input
                              type="number"
                              min={0}
                              step="0.01"
                              value={fee.amount}
                              onChange={(e) => {
                                const v = e.target.value;
                                setFees((prev) =>
                                  prev.map((f, i) =>
                                    i === idx ? { ...f, amount: v } : f,
                                  ),
                                );
                              }}
                              required
                            />
                          </label>
                          <label className="field">
                            <span>Payeur</span>
                            <select
                              value={fee.payer}
                              onChange={(e) => {
                                const v = e.target.value;
                                setFees((prev) =>
                                  prev.map((f, i) =>
                                    i === idx ? { ...f, payer: v } : f,
                                  ),
                                );
                              }}
                            >
                              <option value="CLIENT">Client</option>
                              <option value="INSTITUTION">Institution</option>
                            </select>
                          </label>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm dation-extra-remove"
                            onClick={() =>
                              setFees((prev) =>
                                prev.filter((_, i) => i !== idx),
                              )
                            }
                            aria-label="Retirer ce frais"
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
                      <span className="form-section-title">5. Commentaire</span>
                      <span className="form-section-desc">
                        Contexte libre. Les documents/photos s’ajoutent ensuite
                        sur la fiche brouillon.
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
                  <label
                    className="field"
                    style={{
                      flexDirection: "row",
                      alignItems: "center",
                      gap: 8,
                      marginTop: 12,
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={requireFullCoverage}
                      onChange={(e) =>
                        setRequireFullCoverage(e.target.checked)
                      }
                    />
                    <span>
                      Exiger la couverture intégrale à la soumission du
                      circuit
                    </span>
                  </label>
                  {applicationId && (
                    <p className="muted small" style={{ marginTop: 8 }}>
                      Dossier crédit lié :{" "}
                      <PermLink
                        user={user}
                        anyOf={PERM_CREDITS}
                        to={`/dossiers/${applicationId}`}
                      >
                        {applicationRef || applicationId.slice(0, 8)}
                      </PermLink>
                    </p>
                  )}
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
                      <span className="label">Frais client</span>
                      <strong>
                        {formatMoney(clientFeesTotal, currency)}
                      </strong>
                    </div>
                    <div>
                      <span className="label">Créance à couvrir</span>
                      <strong>{formatMoney(claimToCover, currency)}</strong>
                    </div>
                    <div>
                      <span className="label">Biens retenus</span>
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
                        ? "Les biens couvrent la créance à couvrir."
                        : `Manque ${formatMoney(claimToCover - selectedTotal, currency)}.`}
                  </p>
                  <p className="muted small">
                    {selectedCount} bien{selectedCount > 1 ? "s" : ""} — puis
                    pièces jointes sur la fiche.
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
                  : "Créer le brouillon"}
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
  const { user } = useAuth();
  const canInitiate = hasPerm(user, "guarantees.initiate_dationrequest");

  const [feeType, setFeeType] = useState("NOTARY");
  const [feeAmount, setFeeAmount] = useState("");
  const [feePayer, setFeePayer] = useState("CLIENT");
  const [feeLabel, setFeeLabel] = useState("");
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docName, setDocName] = useState("");
  const [docCat, setDocCat] = useState("DAT_PHOTO");
  const [docAsset, setDocAsset] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const detail = useQuery({
    queryKey: ["dation-request", id],
    queryFn: async () =>
      (await api.get<DationRequest>(`/dation-requests/${id}/`)).data,
    enabled: !!id,
  });

  const docs = useQuery({
    queryKey: ["dation-docs", id],
    queryFn: async () =>
      (await api.get<GedDocument[]>(`/dation-requests/${id}/documents/`)).data,
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

  function invalidateAll() {
    qc.invalidateQueries({ queryKey: ["dation-request", id] });
    qc.invalidateQueries({ queryKey: ["dation-docs", id] });
    qc.invalidateQueries({ queryKey: ["dation-workflow", id] });
    qc.invalidateQueries({ queryKey: ["dation-requests"] });
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
      (await api.post(`/dation-requests/${id}/retry_cbs/`)).data,
    onSuccess: () => invalidateAll(),
    onError: (e) => setActionError(errMsg(e, "Échec retry CBS.")),
  });

  const submit = useMutation({
    mutationFn: async () =>
      (await api.post(`/dation-requests/${id}/submit/`)).data,
    onSuccess: () => {
      setActionError(null);
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Soumission impossible.")),
  });

  const cancel = useMutation({
    mutationFn: async () =>
      (await api.post(`/dation-requests/${id}/cancel/`, { comment: "Annulé" }))
        .data,
    onSuccess: () => invalidateAll(),
    onError: (e) => setActionError(errMsg(e, "Annulation impossible.")),
  });

  const refreshCbs = useMutation({
    mutationFn: async () =>
      (await api.post(`/dation-requests/${id}/refresh-cbs/`)).data,
    onSuccess: () => {
      setActionError(null);
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Rafraîchissement CBS impossible.")),
  });

  const addFee = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/dation-requests/${id}/add-fee/`, {
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
      (await api.post(`/dation-requests/${id}/remove-fee/${feeId}/`)).data,
    onSuccess: () => invalidateAll(),
  });

  const removeAsset = useMutation({
    mutationFn: async (assetId: string) =>
      (await api.post(`/dation-requests/${id}/remove-asset/${assetId}/`)).data,
    onSuccess: () => invalidateAll(),
  });

  const uploadDoc = useMutation({
    mutationFn: async () => {
      const fd = new FormData();
      if (docFile) fd.append("file", docFile);
      fd.append("name", docName || docFile?.name || "Document");
      fd.append("category", docCat);
      if (docAsset) fd.append("asset", docAsset);
      return (
        await api.post(`/dation-requests/${id}/documents/`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        })
      ).data;
    },
    onSuccess: () => {
      setDocFile(null);
      setDocName("");
      setDocAsset("");
      invalidateAll();
    },
    onError: (e) => setActionError(errMsg(e, "Upload impossible.")),
  });

  if (detail.isLoading) return <Spinner />;
  if (detail.isError || !detail.data)
    return (
      <ErrorState
        message="Impossible de charger la dation en paiement."
        onRetry={() => detail.refetch()}
      />
    );
  const r = detail.data;
  const cur = r.cbs_currency || "XOF";
  const editable = r.status === "DRAFT" || r.status === "RETURNED";
  const canCancel =
    canInitiate &&
    ["DRAFT", "RETURNED", "IN_APPROVAL", "BLOCKED"].includes(r.status);
  const canRefreshCbs =
    canInitiate &&
    !["COMPLETED", "CANCELLED", "REJECTED"].includes(r.status);
  const myTask =
    myTasks?.results.find(
      (t) => t.target_meta?.kind === "DATION" && t.target_meta.id === r.id,
    ) ?? null;
  const fees: DationFee[] = r.fees ?? [];

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
            {r.application && (
              <PermLink
                user={user}
                anyOf={PERM_CREDITS}
                className="btn btn-ghost"
                to={`/dossiers/${r.application}`}
                fallback={null}
              >
                Dossier crédit
                {r.application_reference ? ` ${r.application_reference}` : ""}
              </PermLink>
            )}
            {r.collection_case_id && (
              <PermLink
                user={user}
                anyOf={PERM_COLLECTIONS}
                className="btn btn-ghost"
                to={`/recouvrement/${r.collection_case_id}`}
                fallback={null}
              >
                Recouvrement
              </PermLink>
            )}
            {canInitiate && editable && (
              <button
                className="btn btn-primary"
                onClick={() => submit.mutate()}
                disabled={submit.isPending}
              >
                Soumettre au circuit
              </button>
            )}
            {canRefreshCbs && (
              <button
                className="btn btn-ghost"
                onClick={() => refreshCbs.mutate()}
                disabled={refreshCbs.isPending}
              >
                <RefreshCw size={16} />
                Rafraîchir CBS
              </button>
            )}
            {canCancel && (
              <button
                className="btn btn-ghost"
                onClick={() => {
                  const needsConfirm =
                    r.status === "IN_APPROVAL" || r.status === "BLOCKED";
                  if (
                    needsConfirm &&
                    !window.confirm(
                      r.status === "IN_APPROVAL"
                        ? "Annuler cette dation en cours de validation ? Le circuit sera interrompu."
                        : "Annuler cette dation bloquée CBS ?",
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

      {!r.application && (
        <div className="callout" style={{ marginBottom: 12 }}>
          Cette dation n&apos;est pas rattachée à un dossier de crédit. Le
          gel du recouvrement et les liens vers le prêt ne s&apos;appliquent
          pas tant qu&apos;un dossier n&apos;est pas indiqué.
        </div>
      )}
      {r.status === "BLOCKED" && (
        <div className="form-error">
          Dossier bloqué côté CBS. Utilisez « Rafraîchir CBS » ou « Retenter
          CBS », ou annulez la demande.
        </div>
      )}
      {r.status === "IN_APPROVAL" && !myTask && (
        <div className="muted small" style={{ marginBottom: 12 }}>
          Dossier en circuit de validation. Vous pouvez encore l&apos;annuler si
          besoin.
        </div>
      )}
      <div className="detail-grid">
        <Card title="Règlement">
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
                <PermLink
                  user={user}
                  anyOf={PERM_CLIENTS}
                  to={`/clients/${r.client}`}
                >
                  {r.client_display}
                </PermLink>
              </dd>
            </div>
            {r.application && (
              <div>
                <dt>Dossier crédit</dt>
                <dd>
                  <PermLink
                    user={user}
                    anyOf={PERM_CREDITS}
                    to={`/dossiers/${r.application}`}
                  >
                    {r.application_reference || r.application.slice(0, 8)}
                  </PermLink>
                </dd>
              </div>
            )}
            {r.collection_case_id && (
              <div>
                <dt>Recouvrement</dt>
                <dd>
                  <PermLink
                    user={user}
                    anyOf={PERM_COLLECTIONS}
                    to={`/recouvrement/${r.collection_case_id}`}
                  >
                    Fiche dossier
                  </PermLink>
                </dd>
              </div>
            )}
            <div>
              <dt>Créance CBS</dt>
              <dd>{formatMoney(r.cbs_total_outstanding, cur)}</dd>
            </div>
            <div>
              <dt>Frais client</dt>
              <dd>{formatMoney(r.fees_client_total ?? null, cur)}</dd>
            </div>
            <div>
              <dt>Créance à couvrir</dt>
              <dd>{formatMoney(r.claim_to_cover ?? null, cur)}</dd>
            </div>
            <div>
              <dt>Total biens</dt>
              <dd>
                {formatMoney(r.assets_total_value ?? r.asset_value ?? null, cur)}
              </dd>
            </div>
            <div>
              <dt>Solde résiduel</dt>
              <dd>{formatMoney(r.residual_balance ?? null, cur)}</dd>
            </div>
            <div>
              <dt>Trop-value</dt>
              <dd>{formatMoney(r.surplus_amount ?? null, cur)}</dd>
            </div>
            <div>
              <dt>Couverture</dt>
              <dd>
                {r.covers_claim == null ? (
                  "—"
                ) : r.covers_claim ? (
                  <Badge value="OK" label="Couvre" />
                ) : (
                  <Badge value="WARN" label="Insuffisant" />
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
                  <PermLink
                    user={user}
                    anyOf={PERM_GUARANTEES}
                    to={`/garanties/${r.resulting_guarantee}`}
                  >
                    Voir la garantie
                  </PermLink>
                </dd>
              </div>
            )}
          </dl>
          {r.comment && (
            <p className="muted small" style={{ marginTop: 12 }}>
              {r.comment}
            </p>
          )}
        </Card>

        <Card title="Biens du dossier">
          {(r.assets ?? []).length === 0 ? (
            <p>{r.asset_description || "—"}</p>
          ) : (
            <ul className="link-list">
              {r.assets!.map((a) => (
                <li key={a.id}>
                  <span>
                    <ShieldCheck size={14} /> {a.source_display}
                    {a.asset_type_display && (
                      <em className="muted small">
                        {" "}
                        · {a.asset_type_display}
                      </em>
                    )}
                    {a.guarantee ? (
                      <PermLink
                        user={user}
                        anyOf={PERM_GUARANTEES}
                        to={`/garanties/${a.guarantee}`}
                      >
                        <code>{a.guarantee_reference || "Garantie"}</code>
                      </PermLink>
                    ) : a.guarantee_reference ? (
                      <code className="muted"> {a.guarantee_reference}</code>
                    ) : null}
                    <em className="muted small"> — {a.description}</em>
                  </span>
                  <span className="row-actions">
                    <span className="num">{formatMoney(a.value, cur)}</span>
                    {editable && canInitiate && (
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => removeAsset.mutate(a.id)}
                        aria-label="Retirer"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

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
                    <span className="num">{formatMoney(f.amount, cur)}</span>
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
                <select value={feeType} onChange={(e) => setFeeType(e.target.value)}>
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
                <select value={feePayer} onChange={(e) => setFeePayer(e.target.value)}>
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

        <Card title="Pièces jointes (documents / photos)">
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
                  <a className="btn btn-ghost btn-sm" href={d.file} target="_blank" rel="noreferrer">
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
                  <select value={docCat} onChange={(e) => setDocCat(e.target.value)}>
                    {DOC_CATS.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Bien (optionnel)</span>
                  <select
                    value={docAsset}
                    onChange={(e) => setDocAsset(e.target.value)}
                  >
                    <option value="">Dossier entier</option>
                    {(r.assets ?? []).map((a) => (
                      <option key={a.id} value={a.id}>
                        {(a.description || a.guarantee_reference || a.id).slice(
                          0,
                          60,
                        )}
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
            <DecisionPanel task={myTask} />
          </Card>
        )}

        <Card title="Circuit">
          {!workflow.data?.instance ? (
            <EmptyState
              message={
                editable
                  ? "Circuit non démarré — soumettez le brouillon."
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

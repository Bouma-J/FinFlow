import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Building2,
  Contact,
  FileText,
  FilePlus2,
  FilePenLine,
  Trash2,
  GitBranch,
  Cable,
  Heart,
  History,
  IdCard,
  ImageOff,
  Landmark,
  Pencil,
  Phone,
  TriangleAlert,
  User,
  UserRound,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { CLIENT_LABELS, type AuditLog, type Client, type Paginated } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import { Badge, Card, ErrorState, Spinner, formatDate } from "@/components/ui";

function label(map: Record<string, string>, key: string) {
  return map[key] || key || "—";
}

/** Ligne d'une liste de définitions ; masquée si la valeur est vide. */
function Row({ term, value }: { term: string; value?: ReactNode }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div>
      <dt>{term}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function DocLink({ label: text, url }: { label: string; url: string | null }) {
  if (!url) return null;
  return (
    <a
      className="doc-chip"
      href={url}
      target="_blank"
      rel="noreferrer"
      title={`Ouvrir : ${text}`}
    >
      <FileText size={15} />
      {text}
    </a>
  );
}

function SubSection({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="subsection">
      <div className="subsection-title">
        <Icon size={15} />
        {title}
      </div>
      {children}
    </div>
  );
}

const ACTION_META: Record<
  string,
  { label: string; icon: LucideIcon; tone: string }
> = {
  CREATE: { label: "Création", icon: FilePlus2, tone: "success" },
  UPDATE: { label: "Modification", icon: FilePenLine, tone: "info" },
  DELETE: { label: "Suppression", icon: Trash2, tone: "danger" },
  WORKFLOW: { label: "Action workflow", icon: GitBranch, tone: "info" },
  INTEGRATION: { label: "Échange Core Banking", icon: Cable, tone: "muted" },
};

function InterventionHistory({ clientId }: { clientId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["client-audit", clientId],
    queryFn: async () =>
      (
        await api.get<Paginated<AuditLog>>("/audit-logs/", {
          params: { object_id: clientId, ordering: "-timestamp" },
        })
      ).data,
    enabled: !!clientId,
  });

  if (isLoading) return <Spinner />;
  const logs = data?.results ?? [];
  if (logs.length === 0)
    return <p className="muted small">Aucune intervention enregistrée.</p>;

  return (
    <ol className="timeline">
      {logs.map((log) => {
        const meta =
          ACTION_META[log.action] ?? {
            label: log.action,
            icon: History,
            tone: "muted",
          };
        const Icon = meta.icon;
        const changed =
          log.action === "UPDATE" && log.changes
            ? Object.keys(log.changes)
            : [];
        return (
          <li key={log.id} className="timeline-item">
            <span className={`timeline-dot tone-${meta.tone}`}>
              <Icon size={14} />
            </span>
            <div className="timeline-body">
              <div className="timeline-head">
                <strong>{meta.label}</strong>
                <span className="timeline-date">{formatDate(log.timestamp)}</span>
              </div>
              <div className="timeline-sub">
                par {log.user_display || "système"}
                {changed.length > 0 && (
                  <span className="muted">
                    {" "}
                    · {changed.length} champ(s) modifié(s)
                  </span>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const canChange = hasPerm(user, "clients.change_client");
  const canDelete = hasPerm(user, "clients.delete_client");

  const { data: c, isLoading, isError, refetch } = useQuery({
    queryKey: ["client", id],
    queryFn: async () => (await api.get<Client>(`/clients/${id}/`)).data,
    enabled: !!id,
  });

  const deleteMutation = useMutation({
    mutationFn: async () => api.delete(`/clients/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clients"] });
      navigate("/clients");
    },
  });

  if (isLoading) return <Spinner />;
  if (isError || !c) {
    return (
      <ErrorState
        message="Impossible de charger le client."
        onRetry={() => refetch()}
      />
    );
  }

  const isCorporate = c.client_type === "CORPORATE";
  const fullName = `${c.first_name} ${c.last_name}`.trim();
  const hasSpouse =
    c.spouse_last_name ||
    c.spouse_first_name ||
    c.spouse_phone ||
    c.spouse_profession;
  const hasParents =
    c.father_last_name ||
    c.father_first_name ||
    c.mother_last_name ||
    c.mother_first_name;

  const bannerName = isCorporate
    ? c.company_name || c.display_name
    : fullName || c.display_name;

  return (
    <div className="page-shell client-detail-page">
      {confirmDelete && (
        <div className="confirm-bar">
          <span>
            <TriangleAlert size={17} />
            Confirmer la suppression définitive de <strong>{c.display_name}</strong> ?
          </span>
          <div className="row-actions">
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setConfirmDelete(false)}
              disabled={deleteMutation.isPending}
            >
              Annuler
            </button>
            <button
              className="btn btn-danger btn-sm"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Suppression…" : "Oui, supprimer"}
            </button>
          </div>
        </div>
      )}

      {/* Bandeau : identité, actions et photo */}
      <div className="client-banner">
        <div className="client-banner-main">
          <div className="client-banner-info">
            <span className="client-banner-icon">
              {isCorporate ? <Building2 size={26} /> : <UserRound size={26} />}
            </span>
            <div className="client-banner-identity">
              <h2 className="client-banner-name">{bannerName}</h2>
              <p className="client-banner-ref">
                Matricule <code>{c.reference || "—"}</code>
              </p>
              <div className="client-banner-meta">
                <Badge
                  value={c.client_type}
                  label={label(CLIENT_LABELS.client_type, c.client_type)}
                />
                <Badge value={c.kyc_status} />
                <span className={`dot-status ${c.is_active ? "on" : "off"}`}>
                  {c.is_active ? "Actif" : "Inactif"}
                </span>
              </div>
            </div>
          </div>

          <div className="client-banner-actions">
            <Link className="btn btn-banner" to="/clients">
              <ArrowLeft size={15} />
              Retour
            </Link>
            {canChange && (
              <Link className="btn btn-banner" to={`/clients/${c.id}/modifier`}>
                <Pencil size={15} />
                Modifier
              </Link>
            )}
            {canDelete && (
              <button
                className="btn btn-banner btn-banner-danger"
                onClick={() => setConfirmDelete(true)}
              >
                <Trash2 size={15} />
                Supprimer
              </button>
            )}
          </div>
        </div>

        <div className="client-photo-panel">
          {c.photo ? (
            <a
              className="client-photo-frame"
              href={c.photo}
              target="_blank"
              rel="noreferrer"
            >
              <img
                // Ne pas ajouter de query (?v=) : une URL MinIO présignée
                // serait invalidée (signature cassée) alors que le href marche.
                src={c.photo}
                alt="Photo du client"
              />
            </a>
          ) : (
            <div className="client-photo-frame client-photo-empty">
              <ImageOff size={26} />
              <span>Aucune photo</span>
            </div>
          )}
          <span className="client-photo-caption">Photo du client</span>
        </div>
      </div>

      <div className="detail-grid stacked client-detail-sections">
        {isCorporate ? (
          <Card
            title={
              <>
                <Building2 size={17} /> Informations de l'entreprise
              </>
            }
          >
            <SubSection icon={Building2} title="Entreprise">
              <dl className="def-list two">
                <Row term="Raison sociale" value={c.company_name} />
                <Row
                  term="Statut juridique"
                  value={
                    c.legal_form && label(CLIENT_LABELS.legal_form, c.legal_form)
                  }
                />
                <Row term="Numéro IFU" value={c.ifu} />
                <Row term="Numéro RCCM" value={c.rccm} />
              </dl>
              {(c.ifu_scan || c.rccm_scan) && (
                <div className="doc-row">
                  <DocLink label="Scan IFU" url={c.ifu_scan} />
                  <DocLink label="Scan RCCM" url={c.rccm_scan} />
                </div>
              )}
            </SubSection>

            <SubSection icon={Phone} title="Coordonnées">
              <dl className="def-list two">
                <Row term="Téléphone principal" value={c.phone} />
                {c.phones && c.phones.length > 0 && (
                  <Row
                    term="Autres numéros"
                    value={c.phones.map((p) => p.number).join(" · ")}
                  />
                )}
                <Row term="Email" value={c.email} />
                <Row term="Adresse" value={c.address} />
                <Row term="Ville" value={c.city} />
              </dl>
            </SubSection>

            <SubSection icon={Landmark} title="Core Banking">
              <dl className="def-list two">
                <Row term="Matricule Core Banking" value={c.cbs_client_id} />
                <Row term="N° de compte Core Banking" value={c.cbs_account_number} />
              </dl>
            </SubSection>

            <SubSection icon={Contact} title="Gérant">
              <dl className="def-list two">
                <Row
                  term="Nom & prénom"
                  value={`${c.manager_first_name} ${c.manager_last_name}`.trim()}
                />
                <Row term="Téléphone" value={c.manager_phone} />
                <Row term="Email" value={c.manager_email} />
                <Row term="Adresse" value={c.manager_address} />
                <Row
                  term="Pièce d'identité"
                  value={
                    c.manager_id_document_type &&
                    `${label(CLIENT_LABELS.id_document_type, c.manager_id_document_type)} — ${c.manager_id_document_number}`
                  }
                />
              </dl>
              {c.manager_id_document_scan && (
                <div className="doc-row">
                  <DocLink label="Scan pièce du gérant" url={c.manager_id_document_scan} />
                </div>
              )}
            </SubSection>
          </Card>
        ) : (
          <>
            {/* Section fusionnée : Identité + Pièce + Coordonnées + Parents */}
            <Card
              title={
                <>
                  <User size={17} /> Informations personnelles
                </>
              }
            >
              <SubSection icon={User} title="Identité">
                <dl className="def-list two">
                  <Row
                    term="Civilité"
                    value={c.civility && label(CLIENT_LABELS.civility, c.civility)}
                  />
                  <Row term="Nom complet" value={fullName} />
                  <Row term="Date de naissance" value={formatDate(c.birth_date)} />
                  <Row term="Pays de naissance" value={c.birth_country} />
                  <Row term="Nationalité" value={c.nationality} />
                  <Row
                    term="Situation matrimoniale"
                    value={
                      c.marital_status &&
                      label(CLIENT_LABELS.marital_status, c.marital_status)
                    }
                  />
                  <Row term="Profession" value={c.profession} />
                </dl>
              </SubSection>

              <SubSection icon={IdCard} title="Pièce d'identité">
                <dl className="def-list two">
                  <Row
                    term="Type"
                    value={
                      c.id_document_type &&
                      label(CLIENT_LABELS.id_document_type, c.id_document_type)
                    }
                  />
                  <Row term="Numéro" value={c.national_id} />
                  <Row
                    term="Établie le"
                    value={
                      c.id_document_issue_date &&
                      formatDate(c.id_document_issue_date)
                    }
                  />
                  <Row
                    term="Expire le"
                    value={
                      c.id_document_expiry_date &&
                      formatDate(c.id_document_expiry_date)
                    }
                  />
                </dl>
                {c.id_document_scan && (
                  <div className="doc-row">
                    <DocLink label="Scan de la pièce" url={c.id_document_scan} />
                  </div>
                )}
              </SubSection>

              <SubSection icon={Phone} title="Coordonnées">
                <dl className="def-list two">
                  <Row term="Téléphone principal" value={c.phone} />
                  {c.phones && c.phones.length > 0 && (
                    <Row
                      term="Autres numéros"
                      value={c.phones.map((p) => p.number).join(" · ")}
                    />
                  )}
                  <Row term="Email" value={c.email} />
                  <Row term="Adresse" value={c.address} />
                  <Row term="Ville" value={c.city} />
                  <Row term="Pays" value={c.country} />
                </dl>
              </SubSection>

              <SubSection icon={Landmark} title="Core Banking">
                <dl className="def-list two">
                  <Row term="Matricule Core Banking" value={c.cbs_client_id} />
                  <Row
                    term="N° de compte Core Banking"
                    value={c.cbs_account_number}
                  />
                </dl>
              </SubSection>

              {hasParents && (
                <SubSection icon={Users} title="Parents">
                  <dl className="def-list two">
                    <Row
                      term="Père"
                      value={`${c.father_first_name} ${c.father_last_name}`.trim()}
                    />
                    <Row
                      term="Mère"
                      value={`${c.mother_first_name} ${c.mother_last_name}`.trim()}
                    />
                  </dl>
                </SubSection>
              )}
            </Card>

            {hasSpouse && (
              <Card
                title={
                  <>
                    <Heart size={17} /> Conjoint
                  </>
                }
              >
                <dl className="def-list two">
                  <Row
                    term="Nom & prénom"
                    value={`${c.spouse_first_name} ${c.spouse_last_name}`.trim()}
                  />
                  <Row term="Téléphone" value={c.spouse_phone} />
                  <Row term="Profession" value={c.spouse_profession} />
                </dl>
              </Card>
            )}
          </>
        )}
      </div>

      {/* Historique des interventions — section discrète */}
      <section className="history-panel">
        <div className="history-head">
          <History size={16} />
          <span>Historique des interventions</span>
        </div>
        <InterventionHistory clientId={c.id} />
      </section>
    </div>
  );
}

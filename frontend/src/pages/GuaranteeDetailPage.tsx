import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Banknote,
  Car,
  FilePenLine,
  FileText,
  Gem,
  Images,
  Landmark,
  ShieldCheck,
  ShieldOff,
  Stamp,
  Trash2,
  UploadCloud,
  User,
  type LucideIcon,
} from "lucide-react";
import { type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import {
  GUARANTEE_LABELS,
  type Guarantee,
  type GuaranteeFormalizationRequest,
  type Paginated,
} from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasPerm } from "@/auth/permissions";
import {
  Badge,
  Card,
  PageHeader,
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

function lbl(map: Record<string, string>, key: string) {
  return map[key] || key || "—";
}

function Row({ term, value }: { term: string; value?: ReactNode }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div>
      <dt>{term}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children: ReactNode;
}) {
  return (
    <Card
      title={
        <>
          <Icon size={17} /> {title}
        </>
      }
    >
      {children}
    </Card>
  );
}

function DocChip({ label, href }: { label: string; href: string | null }) {
  if (!href) return null;
  return (
    <a className="doc-chip" href={href} target="_blank" rel="noreferrer">
      <FileText size={15} />
      {label}
    </a>
  );
}

export function GuaranteeDetailPage({
  manageable = false,
}: {
  manageable?: boolean;
}) {
  const { id, appId } = useParams<{ id: string; appId?: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();

  const { data: g, isLoading } = useQuery({
    queryKey: ["guarantee", id],
    queryFn: async () => (await api.get<Guarantee>(`/guarantees/${id}/`)).data,
    enabled: !!id,
  });

  const openFormalization = useQuery({
    queryKey: ["guarantee-formalizations", "open", id],
    queryFn: async () => {
      if (g?.open_formalization_id) {
        return {
          id: g.open_formalization_id,
          status: "IN_PROGRESS",
        } as Pick<GuaranteeFormalizationRequest, "id" | "status">;
      }
      const data = (
        await api.get<Paginated<GuaranteeFormalizationRequest>>(
          "/guarantee-formalizations/",
          { params: { guarantee: id, page_size: 10 } },
        )
      ).data;
      return (
        data.results.find((r) => OPEN_FORM_STATUSES.includes(r.status)) ?? null
      );
    },
    enabled: !!id && !!g,
    retry: false,
  });

  const deleteMutation = useMutation({
    mutationFn: async () => api.delete(`/guarantees/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["guarantees"] });
      navigate("/garanties");
    },
  });

  if (isLoading || !g) return <Spinner />;

  const backTo = appId ? `/dossiers/${appId}` : "/garanties";
  const isMortgage = g.guarantee_type === "MORTGAGE";
  const isPledge = g.guarantee_type === "PLEDGE";
  const isVehicle = isPledge && g.pledge_category === "VEHICLE";
  const isValuable = isPledge && g.pledge_category === "VALUABLE";
  const isFinancial = g.guarantee_type === "FINANCIAL";
  const photos = g.photos ?? [];
  const canEdit = manageable && hasPerm(user, "guarantees.change_guarantee");
  const canDelete = manageable && hasPerm(user, "guarantees.delete_guarantee");
  const canRelease =
    g.status === "ACTIVE" &&
    hasPerm(user, "guarantees.initiate_guaranteereleaserequest");
  const canFormalize =
    g.status === "ACTIVE" &&
    !openFormalization.data &&
    !g.formalized_at &&
    hasPerm(user, "guarantees.initiate_guaranteeformalizationrequest");
  const openFormId =
    openFormalization.data?.id || g.open_formalization_id || null;

  function remove() {
    if (
      window.confirm(
        "Supprimer définitivement cette garantie ? Cette action est irréversible.",
      )
    ) {
      deleteMutation.mutate();
    }
  }

  return (
    <div>
      <PageHeader
        icon={ShieldCheck}
        title={g.reference || "Garantie"}
        subtitle={
          g.type_display +
          (isPledge && g.pledge_category
            ? ` — ${lbl(GUARANTEE_LABELS.pledge_category, g.pledge_category)}`
            : "")
        }
        actions={
          <div className="row-actions">
            <Link className="btn btn-ghost" to={backTo}>
              <ArrowLeft />
              Retour
            </Link>
            {(canEdit ||
              canDelete ||
              canRelease ||
              canFormalize ||
              openFormId) && (
              <>
                {canEdit && (
                  <Link
                    className="btn btn-ghost"
                    to={`/garanties/${id}/modifier`}
                  >
                    <FilePenLine />
                    Modifier
                  </Link>
                )}
                {canFormalize && (
                  <Link
                    className="btn btn-primary"
                    to={`/formalisations/nouvelle?client=${g.client}&guarantee=${g.id}`}
                  >
                    <Stamp />
                    Formaliser
                  </Link>
                )}
                {openFormId && (
                  <Link
                    className="btn btn-ghost"
                    to={`/formalisations/${openFormId}`}
                  >
                    <Stamp />
                    Voir formalisation
                  </Link>
                )}
                {canRelease && (
                  <Link
                    className="btn btn-primary"
                    to={`/mains-levees/nouvelle?client=${g.client}&guarantee=${g.id}`}
                  >
                    <ShieldOff />
                    Main levée
                  </Link>
                )}
                {canDelete && (
                  <button
                    className="btn btn-danger"
                    onClick={remove}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 />
                    Supprimer
                  </button>
                )}
              </>
            )}
          </div>
        }
      />

      <div className="client-banner">
        <div className="client-banner-info">
          <span className="client-banner-icon">
            <ShieldCheck size={26} />
          </span>
          <div>
            <h2 className="client-banner-name">{g.type_display}</h2>
            <div className="client-banner-meta">
              <code>{g.reference || g.id.slice(0, 8)}</code>
              <Badge value={g.status} />
              {openFormId && (
                <Badge value="IN_PROGRESS" label="Formalisation en cours" />
              )}
              {g.formalized_at && <Badge value="OK" label="Formalisée" />}
              <span className="muted">
                Valeur actualisée : {formatMoney(g.current_value)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {(g.formalized_at ||
        g.registration_number ||
        g.registration_date ||
        g.registration_authority) && (
        <Card title="Constitution juridique">
          <dl className="def-list two">
            <Row
              term="Formalisée le"
              value={g.formalized_at && formatDate(g.formalized_at)}
            />
            <Row term="N° d'enregistrement" value={g.registration_number} />
            <Row
              term="Date d'enregistrement"
              value={g.registration_date && formatDate(g.registration_date)}
            />
            <Row term="Organisme" value={g.registration_authority} />
          </dl>
          <p className="muted small" style={{ marginTop: 8 }}>
            La formalisation est parallèle au crédit et ne bloque pas le
            décaissement.
          </p>
        </Card>
      )}

      <div className="detail-row">
        <Section icon={User} title="Propriété du bien">
          <dl className="def-list two">
            <Row
              term="Appartient au client demandeur"
              value={g.belongs_to_applicant === false ? "Non" : "Oui"}
            />
            {g.belongs_to_applicant === false && (
              <Row
                term="Caution (propriétaire)"
                value={
                  g.surety ? (
                    <Link to={`/cautions/${g.surety}`}>
                      {g.surety_display || "Voir la caution"}
                    </Link>
                  ) : (
                    g.surety_display
                  )
                }
              />
            )}
          </dl>
        </Section>

        {isMortgage && (
          <>
            <Section icon={User} title="Identité du propriétaire">
              <dl className="def-list two">
                <Row term="Nom" value={g.owner_last_name} />
                <Row term="Prénom" value={g.owner_first_name} />
                <Row
                  term="Situation matrimoniale"
                  value={g.owner_marital_status}
                />
                <Row
                  term="Régime matrimonial"
                  value={
                    g.matrimonial_regime &&
                    lbl(GUARANTEE_LABELS.matrimonial_regime, g.matrimonial_regime)
                  }
                />
              </dl>
            </Section>

            <Section icon={Landmark} title="Bien immobilier">
              <dl className="def-list two">
                <Row
                  term="Type de document"
                  value={
                    g.document_type &&
                    lbl(GUARANTEE_LABELS.document_type, g.document_type)
                  }
                />
                <Row term="Numéro du document" value={g.document_number} />
                <Row
                  term="Date d'établissement"
                  value={
                    g.document_issue_date && formatDate(g.document_issue_date)
                  }
                />
                <Row term="Adresse du bien" value={g.address} />
                <Row
                  term="Valeur expertisée"
                  value={g.expertise_value && formatMoney(g.expertise_value)}
                />
                <Row
                  term="Date de l'expertise"
                  value={g.expertise_date && formatDate(g.expertise_date)}
                />
                <Row term="Cabinet d'expertise" value={g.expertise_firm} />
                <Row term="Nom de l'expert" value={g.expert_name} />
                <Row
                  term="Valeur à considérer"
                  value={g.value_to_consider && formatMoney(g.value_to_consider)}
                />
                <Row
                  term="Taux de couverture"
                  value={
                    g.ltv_ratio
                      ? `${(Number(g.ltv_ratio) * 100).toFixed(0)} %`
                      : undefined
                  }
                />
                <Row
                  term="Statut d'occupation"
                  value={
                    g.occupancy_status &&
                    lbl(GUARANTEE_LABELS.occupancy_status, g.occupancy_status)
                  }
                />
                <Row term="Bien assuré" value={g.is_insured ? "Oui" : "Non"} />
              </dl>
            </Section>
          </>
        )}

        {isVehicle && (
          <Section icon={Car} title="Moyen roulant">
            <dl className="def-list two">
              <Row term="Nom du propriétaire" value={g.owner_last_name} />
              <Row term="Prénom du propriétaire" value={g.owner_first_name} />
              <Row term="Numéro de châssis" value={g.chassis_number} />
              <Row term="Numéro du moteur" value={g.engine_number} />
              <Row term="Marque" value={g.brand} />
              <Row term="Modèle" value={g.model_name} />
              <Row term="Immatriculation" value={g.registration} />
              <Row term="Puissance" value={g.power} />
              <Row
                term="Année de 1re mise en circulation"
                value={g.first_registration_year ?? undefined}
              />
              <Row
                term="Date d'acquisition"
                value={g.acquisition_date && formatDate(g.acquisition_date)}
              />
              <Row
                term="Valeur d'acquisition"
                value={g.acquisition_value && formatMoney(g.acquisition_value)}
              />
              <Row
                term="Valeur estimée à la revente"
                value={g.resale_value && formatMoney(g.resale_value)}
              />
              <Row
                term="Date d'estimation"
                value={g.estimation_date && formatDate(g.estimation_date)}
              />
              <Row
                term="Date de l'expertise"
                value={g.expertise_date && formatDate(g.expertise_date)}
              />
              <Row term="Cabinet d'expertise" value={g.expertise_firm} />
              <Row term="Nom de l'expert" value={g.expert_name} />
            </dl>
            {g.additional_info && (
              <p className="prose">{g.additional_info}</p>
            )}
          </Section>
        )}

        {isValuable && (
          <Section icon={Gem} title="Objet de valeur">
            <dl className="def-list two">
              <Row
                term="Valeur estimée"
                value={g.expertise_value && formatMoney(g.expertise_value)}
              />
              <Row
                term="Date d'expertise"
                value={g.expertise_date && formatDate(g.expertise_date)}
              />
              <Row term="Cabinet d'expertise" value={g.expertise_firm} />
              <Row term="Nom de l'expert" value={g.expert_name} />
              <Row
                term="Cours de la matière première"
                value={g.raw_material_price && formatMoney(g.raw_material_price)}
              />
            </dl>
            {g.description && <p className="prose">{g.description}</p>}
            {g.jewelry_items && g.jewelry_items.length > 0 && (
              <div className="jewelry-list" style={{ marginTop: 16 }}>
                <h4 className="section-subtitle">Composantes du gage</h4>
                <table className="table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Nature</th>
                      <th>Poids (g)</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.jewelry_items.map((item, idx) => (
                      <tr key={item.id ?? idx}>
                        <td>{idx + 1}</td>
                        <td>{item.nature || "—"}</td>
                        <td>
                          {item.weight !== null &&
                          item.weight !== undefined &&
                          item.weight !== ""
                            ? String(item.weight)
                            : "—"}
                        </td>
                        <td>{item.description || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>
        )}

        {isFinancial && (
          <Section icon={Banknote} title="Garantie financière">
            <dl className="def-list two">
              <Row
                term="Type"
                value={
                  g.financial_type &&
                  lbl(GUARANTEE_LABELS.financial_type, g.financial_type)
                }
              />
              <Row term="Numéro de compte" value={g.account_number} />
              <Row term="Solde" value={g.balance && formatMoney(g.balance)} />
              <Row
                term="Taux de rémunération"
                value={g.remuneration_rate && `${g.remuneration_rate} %`}
              />
              <Row
                term="Échéance du dépôt"
                value={
                  g.deposit_maturity_date && formatDate(g.deposit_maturity_date)
                }
              />
              <Row term="Code ISIN / valeur" value={g.isin_code} />
              <Row
                term="Décote de sécurité"
                value={g.security_discount && `${g.security_discount} %`}
              />
            </dl>
            {g.volatility_history && (
              <p className="prose">{g.volatility_history}</p>
            )}
          </Section>
        )}

        <Section icon={UploadCloud} title="Pièces justificatives">
          <div className="doc-row">
            <DocChip label="Scan du document" href={g.document_scan} />
            <DocChip
              label="Rapport d'expertise"
              href={g.expertise_report_scan}
            />
            <DocChip label="Contrat de bail" href={g.lease_contract_scan} />
            <DocChip
              label="Certificat de situation juridique"
              href={g.legal_situation_certificate_scan}
            />
            <DocChip label="Carte grise" href={g.registration_card_scan} />
            <DocChip
              label="Expertise mécanique"
              href={g.mechanical_expertise_scan}
            />
            <DocChip
              label="Visite technique"
              href={g.technical_inspection_scan}
            />
            <DocChip label="Assurance" href={g.insurance_scan} />
            <DocChip label="Facture d'achat" href={g.purchase_invoice_scan} />
            <DocChip
              label="Certificat d'expertise"
              href={g.expertise_certificate_scan}
            />
            <DocChip
              label="Certificat d'origine / facture"
              href={g.origin_certificate_scan}
            />
            <DocChip
              label="Acte de nantissement / blocage"
              href={g.pledge_deed_scan}
            />
          </div>
          {!g.document_scan &&
            !g.expertise_report_scan &&
            !g.lease_contract_scan &&
            !g.legal_situation_certificate_scan &&
            !g.registration_card_scan &&
            !g.mechanical_expertise_scan &&
            !g.technical_inspection_scan &&
            !g.insurance_scan &&
            !g.purchase_invoice_scan &&
            !g.expertise_certificate_scan &&
            !g.origin_certificate_scan &&
            !g.pledge_deed_scan && (
              <p className="muted small">Aucune pièce jointe.</p>
            )}
          {(g.documents?.length ?? 0) > 0 && (
            <div className="doc-row" style={{ marginTop: 12 }}>
              {g.documents!.map((d) => (
                <DocChip key={d.id} label={d.title || "Document"} href={d.file} />
              ))}
            </div>
          )}
        </Section>

        <Section icon={Images} title="Photos">
          {photos.length > 0 ? (
            <div className="photo-gallery">
              {photos.map((p) => (
                <figure key={p.id} className="photo-item">
                  <a href={p.image} target="_blank" rel="noreferrer">
                    <img
                      src={p.image}
                      alt={p.caption || "Photo de la garantie"}
                    />
                  </a>
                  {p.caption && <figcaption>{p.caption}</figcaption>}
                </figure>
              ))}
            </div>
          ) : (
            <p className="muted small">Aucune photo pour cette garantie.</p>
          )}
        </Section>
      </div>
    </div>
  );
}

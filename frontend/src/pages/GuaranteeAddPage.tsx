import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type { CreditApplication } from "@/api/types";
import { GuaranteeForm } from "@/components/GuaranteeForm";
import { RenewGuaranteesPanel } from "@/components/RenewGuaranteesPanel";
import { PageHeader, Spinner } from "@/components/ui";

export function GuaranteeAddPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: app, isLoading } = useQuery({
    queryKey: ["credit-application", id],
    queryFn: async () =>
      (await api.get<CreditApplication>(`/credit-applications/${id}/`)).data,
    enabled: !!id,
  });

  if (isLoading || !app) return <Spinner />;

  const loanAmount = Number(
    app.amount_approved || app.amount_proposed || app.amount_requested || 0,
  );

  return (
    <div>
      <PageHeader
        icon={ShieldCheck}
        title="Ajouter une garantie"
        subtitle={`Dossier ${app.reference} — ${app.client_display}`}
        actions={
          <Link className="btn btn-ghost" to={`/dossiers/${id}`}>
            <ArrowLeft />
            Retour au dossier
          </Link>
        }
      />
      <RenewGuaranteesPanel
        applicationId={app.id}
        currency={app.currency || "XOF"}
      />
      <GuaranteeForm
        mode="create"
        clientId={app.client}
        applicationId={app.id}
        loanAmount={loanAmount}
        backTo={`/dossiers/${id}`}
        onSaved={() => navigate(`/dossiers/${id}`)}
      />
    </div>
  );
}

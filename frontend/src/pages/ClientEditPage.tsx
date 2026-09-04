import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, UserPen } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import type { Client } from "@/api/types";
import { ClientForm } from "@/components/ClientForm";
import { PageHeader, Spinner } from "@/components/ui";

export function ClientEditPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: client, isLoading } = useQuery({
    queryKey: ["client", id],
    queryFn: async () => (await api.get<Client>(`/clients/${id}/`)).data,
    enabled: !!id,
  });

  if (isLoading || !client) return <Spinner />;

  return (
    <div className="page-shell">
      <PageHeader
        icon={UserPen}
        title={`Modifier — ${client.display_name}`}
        subtitle={`Matricule ${client.reference}`}
        actions={
          <Link className="btn btn-ghost" to={`/clients/${client.id}`}>
            <ArrowLeft />
            Retour
          </Link>
        }
      />
      <ClientForm
        initial={client}
        onSuccess={() => navigate(`/clients/${client.id}`)}
        onCancel={() => navigate(`/clients/${client.id}`)}
      />
    </div>
  );
}

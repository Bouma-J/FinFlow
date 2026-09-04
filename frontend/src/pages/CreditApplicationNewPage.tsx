import { ArrowLeft, FilePlus2, TriangleAlert } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { CreditApplicationForm } from "@/components/CreditApplicationForm";
import { PageHeader } from "@/components/ui";

export function CreditApplicationNewPage() {
  const navigate = useNavigate();
  const { user, activeTenant } = useAuth();
  const needsTenant = Boolean(user?.is_group_level && !activeTenant);

  return (
    <div className="page-shell">
      <PageHeader
        icon={FilePlus2}
        title="Nouveau dossier de crédit"
        subtitle="Mise en place et instruction de la demande"
        actions={
          <Link className="btn btn-ghost" to="/dossiers">
            <ArrowLeft />
            Retour
          </Link>
        }
      />

      {needsTenant && (
        <div className="notice-warning">
          <TriangleAlert size={18} />
          <span>
            Vous êtes connecté au niveau Groupe. Sélectionnez d'abord une
            filiale dans la barre supérieure pour créer un dossier.
          </span>
        </div>
      )}

      <CreditApplicationForm
        onCreated={(app) => navigate(`/dossiers/${app.id}`)}
        onCancel={() => navigate("/dossiers")}
      />
    </div>
  );
}

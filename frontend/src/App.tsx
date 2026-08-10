import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminRoute } from "@/components/AdminRoute";
import { Layout } from "@/components/Layout";
import { AuditPage } from "@/pages/AuditPage";
import { ClientDetailPage } from "@/pages/ClientDetailPage";
import { ClientEditPage } from "@/pages/ClientEditPage";
import { ClientsPage } from "@/pages/ClientsPage";
import { CreditApplicationDetailPage } from "@/pages/CreditApplicationDetailPage";
import { CreditApplicationEditPage } from "@/pages/CreditApplicationEditPage";
import { FinancialAnalysisPage } from "@/pages/FinancialAnalysisPage";
import { CreditApplicationNewPage } from "@/pages/CreditApplicationNewPage";
import { CreditApplicationsPage } from "@/pages/CreditApplicationsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { GuaranteeAddPage } from "@/pages/GuaranteeAddPage";
import { GuaranteeDetailPage } from "@/pages/GuaranteeDetailPage";
import { GuaranteeEditPage } from "@/pages/GuaranteeEditPage";
import { GuaranteesPage } from "@/pages/GuaranteesPage";
import {
  GuaranteeReleaseDetailPage,
  GuaranteeReleaseNewPage,
  GuaranteeReleasesPage,
} from "@/pages/GuaranteeReleasesPage";
import {
  DationDetailPage,
  DationNewPage,
  DationsPage,
} from "@/pages/DationsPage";
import { CollectionsPage } from "@/pages/CollectionsPage";
import { CollectionCaseDetailPage } from "@/pages/CollectionCaseDetailPage";
import { SuretyEngagementAddPage } from "@/pages/SuretyEngagementAddPage";
import { LoginPage } from "@/pages/LoginPage";
import { ForceChangePasswordPage } from "@/pages/ForceChangePasswordPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { ProductsPage } from "@/pages/ProductsPage";
import { SimulatorPage } from "@/pages/SimulatorPage";
import { SuretiesPage } from "@/pages/SuretiesPage";
import { SuretyDetailPage } from "@/pages/SuretyDetailPage";
import { SuretyEditPage } from "@/pages/SuretyEditPage";
import { TasksPage } from "@/pages/TasksPage";
import { AdminAgenciesPage } from "@/pages/admin/AgenciesPage";
import { AdminTenantsPage } from "@/pages/admin/TenantsPage";
import { AdminConnectorsPage } from "@/pages/admin/ConnectorsPage";
import { AdminContractsPage } from "@/pages/admin/ContractsAdminPage";
import { AdminNotificationsPage } from "@/pages/admin/NotificationsPage";
import { AdminProductsPage } from "@/pages/admin/ProductsAdminPage";
import { AdminRolesPage } from "@/pages/admin/RolesPage";
import { AdminUsersPage } from "@/pages/admin/UsersPage";
import { AdminWorkflowPage } from "@/pages/admin/WorkflowPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/changer-mot-de-passe"
        element={
          <ProtectedRoute>
            <ForceChangePasswordPage />
          </ProtectedRoute>
        }
      />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/profil" element={<ProfilePage />} />
        <Route path="/clients" element={<ClientsPage />} />
        <Route path="/clients/:id" element={<ClientDetailPage />} />
        <Route path="/clients/:id/modifier" element={<ClientEditPage />} />
        <Route path="/dossiers" element={<CreditApplicationsPage />} />
        <Route path="/dossiers/nouveau" element={<CreditApplicationNewPage />} />
        <Route path="/dossiers/:id" element={<CreditApplicationDetailPage />} />
        <Route
          path="/dossiers/:id/modifier"
          element={<CreditApplicationEditPage />}
        />
        <Route
          path="/dossiers/:id/analyse-financiere"
          element={<FinancialAnalysisPage />}
        />
        <Route
          path="/dossiers/:id/analyse-financiere/:analysisId"
          element={<FinancialAnalysisPage />}
        />
        <Route
          path="/dossiers/:id/garanties/nouvelle"
          element={<GuaranteeAddPage />}
        />
        <Route
          path="/dossiers/:appId/garanties/:id"
          element={<GuaranteeDetailPage />}
        />
        <Route
          path="/dossiers/:appId/cautions/:id"
          element={<SuretyDetailPage />}
        />
        <Route
          path="/dossiers/:id/cautions/nouvelle"
          element={<SuretyEngagementAddPage />}
        />
        <Route path="/taches" element={<TasksPage />} />
        <Route path="/produits" element={<ProductsPage />} />
        <Route path="/cautions" element={<SuretiesPage />} />
        <Route path="/cautions/:id" element={<SuretyDetailPage manageable />} />
        <Route path="/cautions/:id/modifier" element={<SuretyEditPage />} />
        <Route path="/garanties" element={<GuaranteesPage />} />
        <Route
          path="/garanties/:id"
          element={<GuaranteeDetailPage manageable />}
        />
        <Route path="/garanties/:id/modifier" element={<GuaranteeEditPage />} />
        <Route path="/mains-levees" element={<GuaranteeReleasesPage />} />
        <Route
          path="/mains-levees/nouvelle"
          element={<GuaranteeReleaseNewPage />}
        />
        <Route
          path="/mains-levees/:id"
          element={<GuaranteeReleaseDetailPage />}
        />
        <Route path="/dations" element={<DationsPage />} />
        <Route path="/dations/nouvelle" element={<DationNewPage />} />
        <Route path="/dations/:id" element={<DationDetailPage />} />
        <Route path="/recouvrement" element={<CollectionsPage />} />
        <Route path="/recouvrement/:id" element={<CollectionCaseDetailPage />} />
        <Route path="/simulateur" element={<SimulatorPage />} />
        <Route path="/audit" element={<Navigate to="/admin/audit" replace />} />
        <Route
          path="/admin/filiales"
          element={
            <AdminRoute>
              <AdminTenantsPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/agences"
          element={
            <AdminRoute>
              <AdminAgenciesPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/utilisateurs"
          element={
            <AdminRoute>
              <AdminUsersPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/roles"
          element={
            <AdminRoute>
              <AdminRolesPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/produits"
          element={
            <AdminRoute>
              <AdminProductsPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/circuits"
          element={
            <AdminRoute>
              <AdminWorkflowPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/contrats"
          element={
            <AdminRoute>
              <AdminContractsPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/connecteurs"
          element={
            <AdminRoute>
              <AdminConnectorsPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/alertes"
          element={
            <AdminRoute>
              <AdminNotificationsPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/audit"
          element={
            <AdminRoute>
              <AuditPage />
            </AdminRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

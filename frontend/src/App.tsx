import { Navigate, Route, Routes } from "react-router-dom";

import {
  PERM_CLIENTS,
  PERM_COLLECTIONS,
  PERM_CREDIT_CREATE,
  PERM_CREDITS,
  PERM_DATIONS,
  PERM_GUARANTEES,
  PERM_LEGAL_PARTIES,
  PERM_LITIGATION,
  PERM_PRODUCTS,
  PERM_RELEASES,
  PERM_SIMULATOR,
  PERM_SURETIES,
  PERM_TASKS,
} from "@/auth/routePerms";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminRoute } from "@/components/AdminRoute";
import { PermissionRoute } from "@/components/PermissionRoute";
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
import { LegalPartiesPage } from "@/pages/LegalPartiesPage";
import { LitigationDetailPage } from "@/pages/LitigationDetailPage";
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
        <Route
          path="/clients"
          element={
            <PermissionRoute anyOf={PERM_CLIENTS}>
              <ClientsPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/clients/:id"
          element={
            <PermissionRoute anyOf={PERM_CLIENTS}>
              <ClientDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/clients/:id/modifier"
          element={
            <PermissionRoute anyOf={PERM_CLIENTS}>
              <ClientEditPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers"
          element={
            <PermissionRoute anyOf={PERM_CREDITS}>
              <CreditApplicationsPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers/nouveau"
          element={
            <PermissionRoute anyOf={PERM_CREDIT_CREATE}>
              <CreditApplicationNewPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers/:id"
          element={
            <PermissionRoute anyOf={PERM_CREDITS}>
              <CreditApplicationDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers/:id/modifier"
          element={
            <PermissionRoute anyOf={PERM_CREDITS}>
              <CreditApplicationEditPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers/:id/analyse-financiere"
          element={
            <PermissionRoute anyOf={PERM_CREDITS}>
              <FinancialAnalysisPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers/:id/analyse-financiere/:analysisId"
          element={
            <PermissionRoute anyOf={PERM_CREDITS}>
              <FinancialAnalysisPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers/:id/garanties/nouvelle"
          element={
            <PermissionRoute anyOf={PERM_GUARANTEES}>
              <GuaranteeAddPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers/:appId/garanties/:id"
          element={
            <PermissionRoute anyOf={PERM_GUARANTEES}>
              <GuaranteeDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers/:appId/cautions/:id"
          element={
            <PermissionRoute anyOf={PERM_SURETIES}>
              <SuretyDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dossiers/:id/cautions/nouvelle"
          element={
            <PermissionRoute anyOf={PERM_SURETIES}>
              <SuretyEngagementAddPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/taches"
          element={
            <PermissionRoute anyOf={PERM_TASKS}>
              <TasksPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/produits"
          element={
            <PermissionRoute anyOf={PERM_PRODUCTS}>
              <ProductsPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/cautions"
          element={
            <PermissionRoute anyOf={PERM_SURETIES}>
              <SuretiesPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/cautions/:id"
          element={
            <PermissionRoute anyOf={PERM_SURETIES}>
              <SuretyDetailPage manageable />
            </PermissionRoute>
          }
        />
        <Route
          path="/cautions/:id/modifier"
          element={
            <PermissionRoute anyOf={PERM_SURETIES}>
              <SuretyEditPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/garanties"
          element={
            <PermissionRoute anyOf={PERM_GUARANTEES}>
              <GuaranteesPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/garanties/:id"
          element={
            <PermissionRoute anyOf={PERM_GUARANTEES}>
              <GuaranteeDetailPage manageable />
            </PermissionRoute>
          }
        />
        <Route
          path="/garanties/:id/modifier"
          element={
            <PermissionRoute anyOf={PERM_GUARANTEES}>
              <GuaranteeEditPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/mains-levees"
          element={
            <PermissionRoute anyOf={PERM_RELEASES}>
              <GuaranteeReleasesPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/mains-levees/nouvelle"
          element={
            <PermissionRoute
              anyOf={["guarantees.initiate_guaranteereleaserequest"]}
            >
              <GuaranteeReleaseNewPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/mains-levees/:id"
          element={
            <PermissionRoute anyOf={PERM_RELEASES}>
              <GuaranteeReleaseDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dations"
          element={
            <PermissionRoute anyOf={PERM_DATIONS}>
              <DationsPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dations/nouvelle"
          element={
            <PermissionRoute anyOf={["guarantees.initiate_dationrequest"]}>
              <DationNewPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/dations/:id"
          element={
            <PermissionRoute anyOf={PERM_DATIONS}>
              <DationDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/recouvrement"
          element={
            <PermissionRoute anyOf={PERM_COLLECTIONS}>
              <CollectionsPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/recouvrement/:id"
          element={
            <PermissionRoute anyOf={PERM_COLLECTIONS}>
              <CollectionCaseDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/recouvrement/:caseId/contentieux/:litId"
          element={
            <PermissionRoute anyOf={PERM_LITIGATION}>
              <LitigationDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/intervenants-juridiques"
          element={
            <PermissionRoute anyOf={PERM_LEGAL_PARTIES}>
              <LegalPartiesPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/simulateur"
          element={
            <PermissionRoute anyOf={PERM_SIMULATOR}>
              <SimulatorPage />
            </PermissionRoute>
          }
        />
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

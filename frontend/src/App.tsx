import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import {
  PERM_ADMIN_AGENCIES,
  PERM_ADMIN_ALERTS,
  PERM_ADMIN_AUDIT,
  PERM_ADMIN_CBS_REF,
  PERM_ADMIN_CIRCUITS,
  PERM_ADMIN_CONNECTORS,
  PERM_ADMIN_CONTRACTS,
  PERM_ADMIN_DELEGATIONS,
  PERM_ADMIN_POLICY,
  PERM_ADMIN_PRODUCTS,
  PERM_ADMIN_REFERENTIALS,
  PERM_ADMIN_ROLES,
  PERM_ADMIN_USERS,
  PERM_AFTER_SALES,
  PERM_CLIENTS,
  PERM_CLIENTS_CHANGE,
  PERM_COLLECTIONS,
  PERM_CREDIT_CREATE,
  PERM_CREDITS,
  PERM_CREDITS_CHANGE,
  PERM_DASHBOARD,
  PERM_DATIONS,
  PERM_DOCUMENTS,
  PERM_FORMALIZATIONS,
  PERM_GUARANTEES,
  PERM_GUARANTEES_ADD,
  PERM_GUARANTEES_CHANGE,
  PERM_LEGAL_PARTIES,
  PERM_LITIGATION,
  PERM_PRODUCTS,
  PERM_RELEASES,
  PERM_SIMULATOR,
  PERM_SURETIES,
  PERM_TASKS,
  homePath,
} from "@/auth/routePerms";
import { useAuth } from "@/auth/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminRoute } from "@/components/AdminRoute";
import { PermissionRoute } from "@/components/PermissionRoute";
import { Layout } from "@/components/Layout";
import { Spinner } from "@/components/ui";

// Pages critiques chargées immédiatement (first paint)
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { ForceChangePasswordPage } from "@/pages/ForceChangePasswordPage";

// Fallback loading pour lazy pages
function PageLoadingFallback() {
  return (
    <div className="loading-screen">
      <Spinner />
      <p className="text-muted" style={{ marginTop: "1rem" }}>
        Chargement...
      </p>
    </div>
  );
}

// Pages principales - lazy loaded
const ClientsPage = lazy(() => import("@/pages/ClientsPage").then(m => ({ default: m.ClientsPage })));
const ClientDetailPage = lazy(() => import("@/pages/ClientDetailPage").then(m => ({ default: m.ClientDetailPage })));
const ClientEditPage = lazy(() => import("@/pages/ClientEditPage").then(m => ({ default: m.ClientEditPage })));

const CreditApplicationsPage = lazy(() => import("@/pages/CreditApplicationsPage").then(m => ({ default: m.CreditApplicationsPage })));
const CreditApplicationNewPage = lazy(() => import("@/pages/CreditApplicationNewPage").then(m => ({ default: m.CreditApplicationNewPage })));
const CreditApplicationDetailPage = lazy(() => import("@/pages/CreditApplicationDetailPage").then(m => ({ default: m.CreditApplicationDetailPage })));
const CreditApplicationEditPage = lazy(() => import("@/pages/CreditApplicationEditPage").then(m => ({ default: m.CreditApplicationEditPage })));
const FinancialAnalysisPage = lazy(() => import("@/pages/FinancialAnalysisPage").then(m => ({ default: m.FinancialAnalysisPage })));
const LoansPage = lazy(() => import("@/pages/LoansPage").then(m => ({ default: m.LoansPage })));
const LoanWriteOffRequestsPage = lazy(() => import("@/pages/LoanWriteOffRequestsPage").then(m => ({ default: m.LoanWriteOffRequestsPage })));
const LoanRestructuringRequestsPage = lazy(() => import("@/pages/LoanRestructuringRequestsPage").then(m => ({ default: m.LoanRestructuringRequestsPage })));

const GuaranteesPage = lazy(() => import("@/pages/GuaranteesPage").then(m => ({ default: m.GuaranteesPage })));
const GuaranteeDetailPage = lazy(() => import("@/pages/GuaranteeDetailPage").then(m => ({ default: m.GuaranteeDetailPage })));
const GuaranteeEditPage = lazy(() => import("@/pages/GuaranteeEditPage").then(m => ({ default: m.GuaranteeEditPage })));
const GuaranteeAddPage = lazy(() => import("@/pages/GuaranteeAddPage").then(m => ({ default: m.GuaranteeAddPage })));

// Pages après-vente - lazy loaded (pages lourdes)
const GuaranteeReleasesPage = lazy(() => import("@/pages/GuaranteeReleasesPage").then(m => ({ default: m.GuaranteeReleasesPage })));
const GuaranteeReleaseNewPage = lazy(() => import("@/pages/GuaranteeReleasesPage").then(m => ({ default: m.GuaranteeReleaseNewPage })));
const GuaranteeReleaseDetailPage = lazy(() => import("@/pages/GuaranteeReleasesPage").then(m => ({ default: m.GuaranteeReleaseDetailPage })));

const DationsPage = lazy(() => import("@/pages/DationsPage").then(m => ({ default: m.DationsPage })));
const DationNewPage = lazy(() => import("@/pages/DationsPage").then(m => ({ default: m.DationNewPage })));
const DationDetailPage = lazy(() => import("@/pages/DationsPage").then(m => ({ default: m.DationDetailPage })));

const FormalizationsPage = lazy(() => import("@/pages/FormalizationsPage").then(m => ({ default: m.FormalizationsPage })));
const FormalizationNewPage = lazy(() => import("@/pages/FormalizationsPage").then(m => ({ default: m.FormalizationNewPage })));
const FormalizationDetailPage = lazy(() => import("@/pages/FormalizationsPage").then(m => ({ default: m.FormalizationDetailPage })));

const AfterSalesHubPage = lazy(() => import("@/pages/AfterSalesHubPage").then(m => ({ default: m.AfterSalesHubPage })));

// Pages recouvrement - lazy loaded
const CollectionsPage = lazy(() => import("@/pages/CollectionsPage").then(m => ({ default: m.CollectionsPage })));
const CollectionCaseDetailPage = lazy(() => import("@/pages/CollectionCaseDetailPage").then(m => ({ default: m.CollectionCaseDetailPage })));
const LitigationDetailPage = lazy(() => import("@/pages/LitigationDetailPage").then(m => ({ default: m.LitigationDetailPage })));

// Pages cautions - lazy loaded
const SuretiesPage = lazy(() => import("@/pages/SuretiesPage").then(m => ({ default: m.SuretiesPage })));
const SuretyDetailPage = lazy(() => import("@/pages/SuretyDetailPage").then(m => ({ default: m.SuretyDetailPage })));
const SuretyEditPage = lazy(() => import("@/pages/SuretyEditPage").then(m => ({ default: m.SuretyEditPage })));
const SuretyEngagementAddPage = lazy(() => import("@/pages/SuretyEngagementAddPage").then(m => ({ default: m.SuretyEngagementAddPage })));

// Pages utilitaires - lazy loaded
const ProfilePage = lazy(() => import("@/pages/ProfilePage").then(m => ({ default: m.ProfilePage })));
const ProductsPage = lazy(() => import("@/pages/ProductsPage").then(m => ({ default: m.ProductsPage })));
const SimulatorPage = lazy(() => import("@/pages/SimulatorPage").then(m => ({ default: m.SimulatorPage })));
const TasksPage = lazy(() => import("@/pages/TasksPage").then(m => ({ default: m.TasksPage })));
const DocumentsPage = lazy(() => import("@/pages/DocumentsPage").then(m => ({ default: m.DocumentsPage })));
const GroupConsolidationPage = lazy(() => import("@/pages/GroupConsolidationPage").then(m => ({ default: m.GroupConsolidationPage })));

// Pages admin - lazy loaded (rarement accédées)
const AuditPage = lazy(() => import("@/pages/AuditPage").then(m => ({ default: m.AuditPage })));
const AdminAgenciesPage = lazy(() => import("@/pages/admin/AgenciesPage").then(m => ({ default: m.AdminAgenciesPage })));
const AdminTenantsPage = lazy(() => import("@/pages/admin/TenantsPage").then(m => ({ default: m.AdminTenantsPage })));
const AdminBusinessReferentialsPage = lazy(() => import("@/pages/admin/BusinessReferentialsPage").then(m => ({ default: m.AdminBusinessReferentialsPage })));
const AdminConnectorsPage = lazy(() => import("@/pages/admin/ConnectorsPage").then(m => ({ default: m.AdminConnectorsPage })));
const AdminContractsPage = lazy(() => import("@/pages/admin/ContractsAdminPage").then(m => ({ default: m.AdminContractsPage })));
const AdminNotificationsPage = lazy(() => import("@/pages/admin/NotificationsPage").then(m => ({ default: m.AdminNotificationsPage })));
const AdminCollectionEscalationRulesPage = lazy(() => import("@/pages/admin/CollectionEscalationRulesPage").then(m => ({ default: m.AdminCollectionEscalationRulesPage })));
const AdminCollectionTranchesPage = lazy(() => import("@/pages/admin/CollectionTranchesPage").then(m => ({ default: m.AdminCollectionTranchesPage })));
const AdminCreditPolicyPage = lazy(() => import("@/pages/admin/CreditPolicyPage").then(m => ({ default: m.AdminCreditPolicyPage })));
const AdminDelegationsPage = lazy(() => import("@/pages/admin/DelegationsPage").then(m => ({ default: m.AdminDelegationsPage })));
const AdminProductsPage = lazy(() => import("@/pages/admin/ProductsAdminPage").then(m => ({ default: m.AdminProductsPage })));
const AdminCbsReferentialsPage = lazy(() => import("@/pages/admin/CbsReferentialsPage").then(m => ({ default: m.AdminCbsReferentialsPage })));
const AdminCbsSituationProbePage = lazy(() => import("@/pages/admin/CbsSituationProbePage").then(m => ({ default: m.AdminCbsSituationProbePage })));
const AdminRolesPage = lazy(() => import("@/pages/admin/RolesPage").then(m => ({ default: m.AdminRolesPage })));
const AdminUsersPage = lazy(() => import("@/pages/admin/UsersPage").then(m => ({ default: m.AdminUsersPage })));
const AdminWorkflowPage = lazy(() => import("@/pages/admin/WorkflowPage").then(m => ({ default: m.AdminWorkflowPage })));
const LegalPartiesPage = lazy(() => import("@/pages/admin/LegalPartiesPage").then(m => ({ default: m.LegalPartiesPage })));

function FallbackHome() {
  const { user } = useAuth();
  return <Navigate to={homePath(user)} replace />;
}

export default function App() {
  return (
    <Suspense fallback={<PageLoadingFallback />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/login/:tenantCode" element={<LoginPage />} />
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
        <Route
          path="/"
          element={
            <PermissionRoute anyOf={PERM_DASHBOARD}>
              <DashboardPage />
            </PermissionRoute>
          }
        />
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
            <PermissionRoute anyOf={PERM_CLIENTS_CHANGE}>
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
          path="/prets"
          element={
            <PermissionRoute anyOf={PERM_CREDITS}>
              <LoansPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/prets/writeoff-requests"
          element={
            <PermissionRoute anyOf={PERM_CREDITS}>
              <LoanWriteOffRequestsPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/prets/restructuring-requests"
          element={
            <PermissionRoute anyOf={PERM_CREDITS}>
              <LoanRestructuringRequestsPage />
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
            <PermissionRoute anyOf={PERM_CREDITS_CHANGE}>
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
            <PermissionRoute anyOf={PERM_GUARANTEES_ADD}>
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
            <PermissionRoute anyOf={PERM_GUARANTEES_CHANGE}>
              <GuaranteeEditPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/apres-vente"
          element={
            <PermissionRoute anyOf={PERM_AFTER_SALES}>
              <AfterSalesHubPage />
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
          path="/formalisations"
          element={
            <PermissionRoute anyOf={PERM_FORMALIZATIONS}>
              <FormalizationsPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/formalisations/nouvelle"
          element={
            <PermissionRoute
              anyOf={["guarantees.initiate_guaranteeformalizationrequest"]}
            >
              <FormalizationNewPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/formalisations/:id"
          element={
            <PermissionRoute anyOf={PERM_FORMALIZATIONS}>
              <FormalizationDetailPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/documents"
          element={
            <PermissionRoute anyOf={PERM_DOCUMENTS}>
              <DocumentsPage />
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
          element={<Navigate to="/admin/intervenants-juridiques" replace />}
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
          path="/admin/consolidation"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_DASHBOARD}>
                <GroupConsolidationPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/agences"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_AGENCIES}>
                <AdminAgenciesPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/utilisateurs"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_USERS}>
                <AdminUsersPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/roles"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_ROLES}>
                <AdminRolesPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/produits"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_PRODUCTS}>
                <AdminProductsPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/referentiels-cbs"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_CBS_REF}>
                <AdminCbsReferentialsPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/referentiels-metier"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_REFERENTIALS}>
                <AdminBusinessReferentialsPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/intervenants-juridiques"
          element={
            <PermissionRoute anyOf={PERM_LEGAL_PARTIES}>
              <LegalPartiesPage />
            </PermissionRoute>
          }
        />
        <Route
          path="/admin/circuits"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_CIRCUITS}>
                <AdminWorkflowPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/delegations"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_DELEGATIONS}>
                <AdminDelegationsPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/contrats"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_CONTRACTS}>
                <AdminContractsPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/connecteurs"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_CONNECTORS}>
                <AdminConnectorsPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/verification-situation"
          element={
            <AdminRoute>
              <AdminCbsSituationProbePage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/alertes"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_ALERTS}>
                <AdminNotificationsPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/politique-credit"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_POLICY}>
                <AdminCreditPolicyPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
        <Route
          path="/admin/tranches-recouvrement"
          element={
            <AdminRoute>
              <AdminCollectionTranchesPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/regles-escalade"
          element={
            <AdminRoute>
              <AdminCollectionEscalationRulesPage />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/audit"
          element={
            <AdminRoute>
              <PermissionRoute anyOf={PERM_ADMIN_AUDIT}>
                <AuditPage />
              </PermissionRoute>
            </AdminRoute>
          }
        />
      </Route>
      <Route path="*" element={<FallbackHome />} />
    </Routes>
    </Suspense>
  );
}

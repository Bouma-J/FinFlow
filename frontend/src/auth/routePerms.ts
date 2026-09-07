/** Permissions minimales pour afficher / accéder aux modules métier. */

export const PERM_CLIENTS = ["clients.view_client"] as const;
export const PERM_CLIENTS_CHANGE = ["clients.change_client"] as const;
export const PERM_CLIENTS_DELETE = ["clients.delete_client"] as const;
export const PERM_CREDITS = ["credits.view_creditapplication"] as const;
export const PERM_CREDIT_CREATE = ["credits.add_creditapplication"] as const;
export const PERM_PRODUCTS = ["catalog.view_creditproduct"] as const;
export const PERM_GUARANTEES = ["guarantees.view_guarantee"] as const;
export const PERM_SURETIES = ["sureties.view_surety"] as const;
export const PERM_TASKS = ["workflow.view_approvaltask"] as const;
export const PERM_SIMULATOR = ["credits.view_creditapplication"] as const;
export const PERM_RELEASES = [
  "guarantees.view_guaranteereleaserequest",
  "guarantees.initiate_guaranteereleaserequest",
] as const;
export const PERM_DATIONS = [
  "guarantees.view_dationrequest",
  "guarantees.initiate_dationrequest",
] as const;
export const PERM_FORMALIZATIONS = [
  "guarantees.view_guaranteeformalizationrequest",
  "guarantees.initiate_guaranteeformalizationrequest",
] as const;
export const PERM_COLLECTIONS = ["collections.view_collectioncase"] as const;
export const PERM_LEGAL_PARTIES = ["collections.view_legalparty"] as const;
export const PERM_LITIGATION = ["collections.view_litigationfile"] as const;
export const PERM_DOCUMENTS = ["documents.view_document"] as const;
export const PERM_DASHBOARD = ["reporting.view_dashboard"] as const;

/** Hub après-vente : au moins un module ML / dation / formalisation / recouvrement. */
export const PERM_AFTER_SALES = [
  ...PERM_RELEASES,
  ...PERM_DATIONS,
  ...PERM_FORMALIZATIONS,
  ...PERM_COLLECTIONS,
] as const;

/** Admin — modules récents (en plus de is_staff). */
export const PERM_ADMIN_ALERTS = [
  "notifications.view_tenantnotificationsettings",
  "notifications.change_tenantnotificationsettings",
] as const;
export const PERM_ADMIN_DELEGATIONS = [
  "accounts.view_delegation",
  "accounts.add_delegation",
  "accounts.change_delegation",
] as const;
export const PERM_ADMIN_CIRCUITS = [
  "workflow.view_workflowdefinition",
  "workflow.add_workflowdefinition",
  "workflow.change_workflowdefinition",
] as const;
export const PERM_ADMIN_CONTRACTS = [
  "contracts.view_contracttemplate",
  "contracts.add_contracttemplate",
  "contracts.change_contracttemplate",
] as const;
export const PERM_ADMIN_REFERENTIALS = [
  "catalog.view_rejectreason",
  "catalog.view_checklistitem",
  "credits.view_analysisthreshold",
  "documents.view_documentcategory",
] as const;
export const PERM_ADMIN_USERS = [
  "accounts.view_user",
  "accounts.change_user",
] as const;
export const PERM_ADMIN_ROLES = [
  "auth.view_group",
  "auth.change_group",
] as const;
export const PERM_ADMIN_AGENCIES = [
  "tenants.view_agency",
  "tenants.change_agency",
] as const;
export const PERM_ADMIN_PRODUCTS = [
  "catalog.view_creditproduct",
  "catalog.change_creditproduct",
] as const;
export const PERM_ADMIN_CBS_REF = [
  "catalog.view_currency",
  "catalog.view_loanperiodicity",
  "catalog.view_repaymentmethod",
] as const;
export const PERM_ADMIN_CONNECTORS = [
  "corebanking.view_corebankingconnector",
  "corebanking.change_corebankingconnector",
] as const;
export const PERM_ADMIN_POLICY = [
  "credits.view_creditinstructionpolicy",
  "credits.change_creditinstructionpolicy",
] as const;
export const PERM_ADMIN_AUDIT = ["audit.view_auditlog"] as const;

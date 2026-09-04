/** Permissions minimales pour afficher / accéder aux modules métier. */

export const PERM_CLIENTS = ["clients.view_client"] as const;
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
export const PERM_COLLECTIONS = ["collections.view_collectioncase"] as const;
export const PERM_LEGAL_PARTIES = ["collections.view_legalparty"] as const;
export const PERM_LITIGATION = ["collections.view_litigationfile"] as const;

import { useQuery } from "@tanstack/react-query";
import { useLayoutEffect, useMemo } from "react";

import { api, tokenStore } from "@/api/client";
import type { Tenant, TenantBranding } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import {
  applyTenantTheme,
  cacheTenantBranding,
  readCachedTenantTheme,
  rememberTenantTheme,
  resolveLogoUrl,
} from "@/hooks/brandingTheme";

export {
  applyTenantTheme,
  applyCachedBrandingSync,
  cacheTenantBranding,
  DEFAULT_THEME,
  LOGIN_TENANT_CODE_KEY,
  readRememberedLoginTenantCode,
  rememberLoginTenantCode,
  resolveLogoUrl,
} from "@/hooks/brandingTheme";

/** Charte publique avant authentification (écran login). */
export function usePublicTenantBranding(code: string | null | undefined) {
  const normalized = (code || "").trim().toUpperCase();

  const query = useQuery({
    queryKey: ["public-tenant-branding", normalized],
    queryFn: async () =>
      (
        await api.get<TenantBranding>("/tenants/branding/", {
          params: { code: normalized },
        })
      ).data,
    enabled: normalized.length > 0,
    staleTime: 60_000,
    retry: false,
  });

  useLayoutEffect(() => {
    if (tokenStore.getAccess() && !query.data) return;
    const brandingData = query.data ?? null;
    applyTenantTheme(brandingData);
    cacheTenantBranding(brandingData);
  }, [query.data]);

  const logoUrl = resolveLogoUrl(query.data ?? null);

  return {
    branding: query.data ?? null,
    logoUrl,
    tenantName: query.data?.name ?? "FIN_FLOW",
    tenantCode: query.data?.code ?? null,
    isLoading: query.isFetching,
    isError: query.isError,
    notFound: Boolean(normalized) && query.isError,
  };
}

/** Applique le logo et les couleurs de la filiale active (y compris la barre de menu). */
export function useTenantBranding() {
  const { user, activeTenant } = useAuth();
  const tenantId = user?.is_group_level ? activeTenant : user?.tenant ?? null;

  const { data: tenant } = useQuery({
    queryKey: ["tenant-branding", tenantId],
    queryFn: async () =>
      tenantId
        ? (await api.get<Tenant>(`/tenants/${tenantId}/`)).data
        : null,
    enabled: !!tenantId,
    staleTime: 60_000,
  });

  const cachedTheme = useMemo(
    () => readCachedTenantTheme(),
    [tenantId, user?.tenant_branding, tenant?.id],
  );
  const branding = tenant ?? user?.tenant_branding ?? cachedTheme;

  const primary = branding?.brand_primary || "";
  const secondary = branding?.brand_secondary || "";
  const accent = branding?.brand_accent || "";

  useLayoutEffect(() => {
    if (!primary) return;
    if (tenant || user?.tenant_branding) {
      rememberTenantTheme(tenantId, branding);
      cacheTenantBranding(branding);
    }
    applyTenantTheme(branding);
  }, [primary, secondary, accent, tenant, user?.tenant_branding, tenantId, branding]);

  const logoUrl = resolveLogoUrl(branding);

  return {
    branding,
    logoUrl,
    tenantName: branding?.name ?? "FIN_FLOW",
    tenantCode: branding?.code ?? null,
  };
}

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { api } from "@/api/client";
import type { Tenant } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";

import defaultLogo from "@/assets/logo.jpg";

const DEFAULT_THEME = {
  brand_primary: "#0f9488",
  brand_secondary: "#0d7a72",
  brand_accent: "#d4a017",
};

function hexToRgb(hex: string) {
  const h = hex.replace("#", "");
  if (h.length !== 6) return { r: 15, g: 148, b: 136 };
  return {
    r: parseInt(h.slice(0, 2), 16),
    g: parseInt(h.slice(2, 4), 16),
    b: parseInt(h.slice(4, 6), 16),
  };
}

function mixHex(hex: string, target: "black" | "white", amount: number) {
  const { r, g, b } = hexToRgb(hex);
  const t = target === "black" ? 0 : 255;
  const f = Math.min(1, Math.max(0, amount / 100));
  const nr = Math.round(r + (t - r) * f);
  const ng = Math.round(g + (t - g) * f);
  const nb = Math.round(b + (t - b) * f);
  return `rgb(${nr}, ${ng}, ${nb})`;
}

function rgba(hex: string, alpha: number) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
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

  const branding = tenant ?? user?.tenant_branding ?? null;

  useEffect(() => {
    const root = document.documentElement;
    const primary = branding?.brand_primary || DEFAULT_THEME.brand_primary;
    const secondary = branding?.brand_secondary || DEFAULT_THEME.brand_secondary;
    const accent = branding?.brand_accent || DEFAULT_THEME.brand_accent;

    root.style.setProperty("--brand", primary);
    root.style.setProperty("--brand-dark", secondary);
    root.style.setProperty("--accent", accent);

    // Alias historiques : tous les écrans qui utilisent --teal-* / --gold-*
    // suivent automatiquement la charte filiale.
    root.style.setProperty("--teal-50", mixHex(primary, "white", 92));
    root.style.setProperty("--teal-100", mixHex(primary, "white", 80));
    root.style.setProperty("--teal-400", mixHex(primary, "white", 22));
    root.style.setProperty("--teal-500", primary);
    root.style.setProperty("--teal-600", secondary);
    root.style.setProperty("--teal-700", mixHex(primary, "black", 28));
    root.style.setProperty("--gold-400", mixHex(accent, "white", 18));
    root.style.setProperty("--gold-500", accent);
    root.style.setProperty("--gold-600", mixHex(accent, "black", 12));
    root.style.setProperty("--info", primary);
    root.style.setProperty("--warning", mixHex(accent, "black", 8));
    root.style.setProperty("--shadow-brand", `0 8px 20px ${rgba(primary, 0.28)}`);

    // Surfaces dérivées (confort visuel + cohérence multi-écrans)
    root.style.setProperty("--brand-soft", mixHex(primary, "white", 92));
    root.style.setProperty("--brand-softer", mixHex(primary, "white", 96));
    root.style.setProperty("--brand-ink", mixHex(primary, "black", 38));
    root.style.setProperty("--brand-ring", rgba(primary, 0.22));
    root.style.setProperty("--accent-soft", mixHex(accent, "white", 88));
    root.style.setProperty("--accent-ink", mixHex(accent, "black", 35));
    root.style.setProperty("--surface-brand", mixHex(primary, "white", 97));
    root.style.setProperty(
      "--page-wash",
      `linear-gradient(180deg, ${mixHex(primary, "white", 95)} 0%, var(--bg) 220px)`,
    );
    root.style.setProperty("--brand-glow", rgba(primary, 0.14));
    root.style.setProperty("--accent-glow", rgba(accent, 0.22));
    root.style.setProperty(
      "--hero-gradient",
      `linear-gradient(135deg, ${mixHex(secondary, "black", 38)} 0%, ${mixHex(secondary, "black", 12)} 48%, ${secondary} 100%)`,
    );
    root.style.setProperty(
      "--login-gradient",
      `linear-gradient(160deg, ${mixHex(secondary, "black", 42)}, ${mixHex(secondary, "black", 58)})`,
    );

    // Barre de menu latérale dérivée de la couleur principale / secondaire
    root.style.setProperty(
      "--sidebar-bg-start",
      mixHex(secondary, "black", 35),
    );
    root.style.setProperty(
      "--sidebar-bg-end",
      mixHex(secondary, "black", 55),
    );
    root.style.setProperty("--sidebar-text", mixHex(primary, "white", 72));
    root.style.setProperty("--sidebar-text-muted", mixHex(primary, "white", 45));
    root.style.setProperty("--sidebar-section", mixHex(primary, "white", 30));
    root.style.setProperty("--sidebar-hover-bg", "rgba(255, 255, 255, 0.07)");
    root.style.setProperty("--sidebar-active-bg", rgba(accent, 0.18));
    root.style.setProperty("--sidebar-active-bar", accent);
    root.style.setProperty("--sidebar-brand-accent", accent);
    root.style.setProperty("--topbar-accent", rgba(primary, 0.12));
  }, [branding]);

  const logoUrl = branding?.logo_url
    ? `${branding.logo_url}${branding.logo_url.includes("?") ? "&" : "?"}v=${branding.id}`
    : defaultLogo;

  return {
    branding,
    logoUrl,
    tenantName: branding?.name ?? "FIN_FLOW",
    tenantCode: branding?.code ?? null,
  };
}

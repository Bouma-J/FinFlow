import { useQuery } from "@tanstack/react-query";
import {
  Boxes,
  Building2,
  Cable,
  Calculator,
  ChevronDown,
  CircleDollarSign,
  ClipboardCheck,
  Bell,
  BookMarked,
  FileSignature,
  FileText,
  GitBranch,
  HandCoins,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Mail,
  MapPin,
  Menu,
  Package,
  PanelLeftClose,
  PanelLeftOpen,
  Scale,
  ScrollText,
  ShieldCheck,
  ShieldOff,
  Stamp,
  Unlock,
  SlidersHorizontal,
  UserRound,
  UsersRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import type { Paginated, Tenant } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { hasAnyPerm } from "@/auth/permissions";
import {
  PERM_CLIENTS,
  PERM_COLLECTIONS,
  PERM_CREDITS,
  PERM_DATIONS,
  PERM_FORMALIZATIONS,
  PERM_GUARANTEES,
  PERM_LEGAL_PARTIES,
  PERM_PRODUCTS,
  PERM_RELEASES,
  PERM_SIMULATOR,
  PERM_SURETIES,
  PERM_TASKS,
} from "@/auth/routePerms";
import { isAdmin } from "@/components/AdminRoute";
import { useTenantBranding } from "@/hooks/useTenantBranding";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Si défini, le lien n'apparaît que si l'utilisateur a au moins une permission. */
  anyOf?: readonly string[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Tableau de bord", icon: LayoutDashboard },
  {
    to: "/dossiers",
    label: "Dossiers de crédit",
    icon: FileText,
    anyOf: PERM_CREDITS,
  },
  {
    to: "/taches",
    label: "Mes validations",
    icon: ClipboardCheck,
    anyOf: PERM_TASKS,
  },
  { to: "/clients", label: "Clients", icon: UserRound, anyOf: PERM_CLIENTS },
  {
    to: "/cautions",
    label: "Cautions",
    icon: HandCoins,
    anyOf: PERM_SURETIES,
  },
  { to: "/produits", label: "Produits", icon: Boxes, anyOf: PERM_PRODUCTS },
  {
    to: "/garanties",
    label: "Garanties",
    icon: ShieldCheck,
    anyOf: PERM_GUARANTEES,
  },
  {
    to: "/mains-levees",
    label: "Mains levées",
    icon: ShieldOff,
    anyOf: PERM_RELEASES,
  },
  {
    to: "/dations",
    label: "Dations",
    icon: Unlock,
    anyOf: PERM_DATIONS,
  },
  {
    to: "/formalisations",
    label: "Formalisations",
    icon: Stamp,
    anyOf: PERM_FORMALIZATIONS,
  },
  {
    to: "/recouvrement",
    label: "Recouvrement",
    icon: CircleDollarSign,
    anyOf: PERM_COLLECTIONS,
  },
  {
    to: "/intervenants-juridiques",
    label: "Intervenants juridiques",
    icon: Scale,
    anyOf: PERM_LEGAL_PARTIES,
  },
  {
    to: "/simulateur",
    label: "Simulateur",
    icon: Calculator,
    anyOf: PERM_SIMULATOR,
  },
];

const ADMIN_ITEMS: NavItem[] = [
  { to: "/admin/filiales", label: "Filiales", icon: Building2 },
  { to: "/admin/agences", label: "Agences", icon: MapPin },
  { to: "/admin/utilisateurs", label: "Utilisateurs", icon: UsersRound },
  { to: "/admin/roles", label: "Rôles & droits", icon: KeyRound },
  { to: "/admin/produits", label: "Produits", icon: Package },
  { to: "/admin/referentiels-cbs", label: "Référentiels CBS", icon: BookMarked },
  { to: "/admin/circuits", label: "Circuits d'approbation", icon: GitBranch },
  { to: "/admin/contrats", label: "Modèles de contrats", icon: FileSignature },
  { to: "/admin/connecteurs", label: "Connecteurs CBS", icon: Cable },
  { to: "/admin/alertes", label: "Alertes e-mail", icon: Bell },
  { to: "/admin/politique-credit", label: "Politique crédit", icon: SlidersHorizontal },
  { to: "/admin/audit", label: "Audit", icon: ScrollText },
];

function NavItems({
  items,
  onNavigate,
}: {
  items: NavItem[];
  onNavigate?: () => void;
}) {
  return (
    <>
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          title={label}
          className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
          onClick={onNavigate}
        >
          <span className="nav-icon">
            <Icon />
          </span>
          <span className="nav-label">{label}</span>
        </NavLink>
      ))}
    </>
  );
}

function TenantSwitcher() {
  const { activeTenant, setActiveTenant } = useAuth();
  const { data } = useQuery({
    queryKey: ["tenants"],
    queryFn: async () => (await api.get<Paginated<Tenant>>("/tenants/")).data,
  });

  return (
    <div className="input-icon tenant-switcher-wrap">
      <Building2 />
      <select
        className="tenant-switcher"
        style={{ paddingLeft: 38 }}
        value={activeTenant ?? ""}
        onChange={(e) => setActiveTenant(e.target.value || null)}
      >
        <option value="">Groupe (consolidé)</option>
        {data?.results.map((t) => (
          <option key={t.id} value={t.id}>
            {t.code} — {t.name}
          </option>
        ))}
      </select>
    </div>
  );
}

function initials(user: {
  first_name?: string;
  last_name?: string;
  username: string;
}) {
  const a = user.first_name?.[0] ?? user.username[0];
  const b = user.last_name?.[0] ?? user.username[1] ?? "";
  return (a + b).toUpperCase();
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Bonjour";
  if (h < 18) return "Bon après-midi";
  return "Bonsoir";
}

type SessionUser = {
  first_name?: string;
  last_name?: string;
  username: string;
  email?: string;
  is_group_level?: boolean;
  roles?: string[];
};

function UserMenu({
  user,
  logout,
}: {
  user: SessionUser;
  logout: () => void | Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const fullName =
    `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim() || user.username;

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  return (
    <div className={`user-menu${open ? " open" : ""}`} ref={ref}>
      <button
        type="button"
        className="user-chip"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="avatar">{initials(user)}</span>
        <span className="user-meta">
          <span className="user-name">{fullName}</span>
          <span className="user-role">
            {user.is_group_level ? "Niveau Groupe" : "Filiale"}
          </span>
        </span>
        <ChevronDown className="chevron" size={16} />
      </button>

      {open && (
        <div className="user-menu-panel" role="menu">
          <div className="user-menu-header">
            <span className="avatar lg">{initials(user)}</span>
            <div>
              <div className="umh-name">{fullName}</div>
              {user.email && (
                <div className="umh-email">
                  <Mail size={12} />
                  {user.email}
                </div>
              )}
            </div>
          </div>
          <div className="user-menu-tags">
            <span className="scope-pill sm">
              <ShieldCheck size={13} />
              {user.is_group_level ? "Niveau Groupe" : "Espace filiale"}
            </span>
            {user.roles?.slice(0, 2).map((r) => (
              <span key={r} className="role-tag">
                {r}
              </span>
            ))}
          </div>
          <button
            type="button"
            className="user-menu-item"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              navigate("/profil");
            }}
          >
            <UserRound size={16} />
            Mon profil
          </button>
          <button
            type="button"
            className="user-menu-item danger"
            role="menuitem"
            onClick={logout}
          >
            <LogOut size={16} />
            Déconnexion
          </button>
        </div>
      )}
    </div>
  );
}

export function Layout() {
  const { user, logout } = useAuth();
  const { logoUrl, tenantName, tenantCode } = useTenantBranding();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem("sidebar-collapsed") === "1",
  );
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem("sidebar-collapsed", collapsed ? "1" : "0");
  }, [collapsed]);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMobileNavOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      document.removeEventListener("keydown", onKey);
    };
  }, [mobileNavOpen]);

  const adminItems = ADMIN_ITEMS.filter(
    (item) => item.to !== "/admin/filiales" || user?.is_group_level,
  );
  const navItems = NAV_ITEMS.filter(
    (item) => !item.anyOf || hasAnyPerm(user, item.anyOf),
  );

  const closeMobileNav = () => setMobileNavOpen(false);

  return (
    <div
      className={`app-shell${collapsed ? " sidebar-collapsed" : ""}${
        mobileNavOpen ? " mobile-nav-open" : ""
      }`}
    >
      {mobileNavOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Fermer le menu"
          onClick={closeMobileNav}
        />
      )}

      <aside className="sidebar">
        <div className="brand">
          <img src={logoUrl} alt={tenantName} className="brand-logo" />
          <span className="brand-name">
            FIN_FLOW
            <small>
              {tenantCode ? `${tenantCode} — ${tenantName}` : "Thuin Tech"}
            </small>
          </span>
          <button
            type="button"
            className="sidebar-close-mobile"
            onClick={closeMobileNav}
            aria-label="Fermer le menu"
          >
            <X size={18} />
          </button>
        </div>
        <nav className="nav">
          <NavItems items={navItems} onNavigate={closeMobileNav} />
          {isAdmin(user) && (
            <>
              <div className="nav-section">Administration</div>
              <NavItems items={adminItems} onNavigate={closeMobileNav} />
            </>
          )}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="sidebar-toggle desktop-only"
              onClick={() => setCollapsed((v) => !v)}
              aria-label={
                collapsed ? "Déployer le menu" : "Réduire le menu"
              }
              title={collapsed ? "Déployer le menu" : "Réduire le menu"}
            >
              {collapsed ? (
                <PanelLeftOpen size={18} />
              ) : (
                <PanelLeftClose size={18} />
              )}
            </button>
            <button
              type="button"
              className="sidebar-toggle mobile-only"
              onClick={() => setMobileNavOpen(true)}
              aria-label="Ouvrir le menu"
              title="Ouvrir le menu"
            >
              <Menu size={18} />
            </button>
            {user?.is_group_level ? (
              <TenantSwitcher />
            ) : (
              <span className="scope-pill">
                <Building2 size={16} />
                Espace filiale
              </span>
            )}
          </div>
          <div className="topbar-right">
            {user && (
              <span className="greeting">
                {greeting()},{" "}
                <strong>{user.first_name || user.username}</strong>
              </span>
            )}
            <span className="topbar-divider" />
            {user && <UserMenu user={user} logout={logout} />}
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

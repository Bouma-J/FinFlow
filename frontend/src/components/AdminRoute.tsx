import type { ReactNode } from "react";

import { useAuth } from "@/auth/AuthContext";
import { EmptyState } from "@/components/ui";

export function isAdmin(user: {
  is_superuser?: boolean;
  is_staff?: boolean;
} | null): boolean {
  return Boolean(user && (user.is_superuser || user.is_staff));
}

export function AdminRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!isAdmin(user)) {
    return (
      <EmptyState message="Accès réservé aux administrateurs." />
    );
  }
  return <>{children}</>;
}

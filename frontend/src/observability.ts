import { tokenStore } from "@/api/client";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const recent = new Set<string>();

/** Envoie une erreur d'écran au journal serveur (et à Sentry si un DSN est configuré). */
export function reportClientError(message: string, stack?: string) {
  const text = (message || "erreur inattendue").slice(0, 500);
  const path = window.location.pathname;
  const key = `${path}|${text}`;
  if (recent.has(key)) return;
  recent.add(key);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = tokenStore.getAccess();
  if (token) headers.Authorization = `Bearer ${token}`;

  fetch(`${BASE_URL}/client-errors/`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      message: text,
      stack: (stack || "").slice(0, 4000),
      path,
    }),
    keepalive: true,
  }).catch(() => undefined);
}

export function installClientErrorReporting() {
  window.addEventListener("error", (event) => {
    reportClientError(event.message || "erreur script", event.error?.stack);
  });
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    const message = reason instanceof Error ? reason.message : String(reason || "promesse rejetée");
    const stack = reason instanceof Error ? reason.stack : undefined;
    reportClientError(message, stack);
  });
}

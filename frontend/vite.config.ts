import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Redirige les appels vers nginx (conteneur frontend) qui route ensuite
      // vers le backend Django. On passe par nginx car le backend Docker
      // n'expose pas le port 8000 sur l'hôte.
      // Pour cibler un runserver local : VITE_API_TARGET=http://127.0.0.1:8000
      ...Object.fromEntries(
        ["/api", "/media", "/django-admin", "/static"].map((path) => [
          path,
          {
            target: process.env.VITE_API_TARGET || "http://localhost",
            changeOrigin: true,
          },
        ]),
      ),
    },
  },
});

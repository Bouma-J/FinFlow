# syntax=docker/dockerfile:1

# ========================================================================
# Stage 1: Builder — build application React
# ========================================================================
FROM node:20-alpine AS build

WORKDIR /app

# Certificats CA d'entreprise (proxy à inspection TLS) pour npm
# Hors proxy le dossier peut ne contenir que .gitkeep
COPY certs/ /certs/
RUN touch /certs/ca-bundle.crt
ENV NODE_EXTRA_CA_CERTS=/certs/ca-bundle.crt

# Installer dépendances (npm ci = reproductible, utilise package-lock.json)
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline --no-audit

# Build application
COPY . .
RUN npm run build

# ========================================================================
# Stage 2: Runtime — serveur Nginx léger et sécurisé
# ========================================================================
FROM nginx:1.27-alpine AS runtime

# Copier configuration Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copier build depuis stage précédent
COPY --from=build /app/dist /usr/share/nginx/html

# Créer utilisateur non-root pour nginx
# Note: nginx alpine utilise déjà 'nginx' user, on ajuste les permissions
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

# Modifier config nginx pour tourner en non-root (optionnel mais recommandé)
# Note: le port 80 nécessite CAP_NET_BIND_SERVICE si non-root
# Pour production, préférer un reverse proxy en amont

EXPOSE 80

# Nginx reste en root par défaut (bind port 80)
# Alternative: USER nginx + port > 1024 + reverse proxy
CMD ["nginx", "-g", "daemon off;"]

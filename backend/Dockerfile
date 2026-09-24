# syntax=docker/dockerfile:1

# ========================================================================
# Stage 1: Builder — compilation des dépendances Python
# ========================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Dépendances système pour compilation (psycopg2, Pillow)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Certificats CA d'entreprise (proxy à inspection TLS)
# Le bundle local (non versionné) est ajouté au magasin système
COPY certs/ /certs/
RUN touch /certs/ca-bundle.crt \
    && if [ -s /certs/ca-bundle.crt ]; then \
        cat /certs/ca-bundle.crt >> /etc/ssl/certs/ca-certificates.crt; \
    fi
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt

# Compiler les wheels (réutilisables, pas de gcc au runtime)
COPY requirements/ /build/requirements/
RUN pip install --upgrade pip \
    && pip wheel --no-deps --wheel-dir /wheels \
        -r requirements/prod.txt

# ========================================================================
# Stage 2: Runtime — image finale légère et sécurisée
# ========================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# Dépendances runtime uniquement (pas de build-essential)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Certificats CA (même logique que builder)
COPY certs/ /certs/
RUN touch /certs/ca-bundle.crt \
    && if [ -s /certs/ca-bundle.crt ]; then \
        cat /certs/ca-bundle.crt >> /etc/ssl/certs/ca-certificates.crt; \
    fi
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Installer wheels précompilés (pas de gcc nécessaire)
COPY --from=builder /wheels /wheels
RUN pip install --upgrade pip \
    && pip install --no-index --find-links=/wheels /wheels/* \
    && rm -rf /wheels

# Créer utilisateur non-root
RUN groupadd -r finflow --gid=1000 \
    && useradd -r -g finflow --uid=1000 --home-dir=/app --shell=/bin/bash finflow \
    && mkdir -p /app /app/staticfiles /app/media \
    && chown -R finflow:finflow /app

WORKDIR /app

# Copier code source
COPY --chown=finflow:finflow . .

# Normaliser fins de ligne et rendre exécutable
RUN sed -i 's/\r$//' docker/entrypoint.sh && chmod +x docker/entrypoint.sh

# Basculer vers utilisateur non-root
USER finflow

EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]

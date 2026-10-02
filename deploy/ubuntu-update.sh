#!/usr/bin/env bash
# =========================================================================
# FIN_FLOW — mise à jour d'une instance déjà en production (Ubuntu)
#
# À lancer sur le serveur où FinFlow est installé (typiquement /opt/finflow).
#
# Usage :
#   sudo bash deploy/ubuntu-update.sh
#   sudo bash deploy/ubuntu-update.sh /opt/finflow
#   sudo bash deploy/ubuntu-update.sh --check /opt/finflow
#
# Serveur de test (branche des dernières évolutions + supervision) :
#   sudo env GIT_BRANCH=cursor/ameliorations-techniques-acda ENABLE_MONITORING=1 \
#     bash -c 'curl -fsSL https://raw.githubusercontent.com/Bouma-J/FinFlow/cursor/ameliorations-techniques-acda/deploy/ubuntu-update.sh | bash'
#
# Branche utilisée, dans l'ordre :
#   1. --branch ou GIT_BRANCH
#   2. fichier .finflow-git-branch (écrit après chaque update)
#   3. branche déjà extraite dans le dépôt
#   4. main
#
# Options :
#   --branch NOM              Branche git à tirer
#   --monitoring              Active Prometheus, Alertmanager, Loki, Grafana
#   --no-monitoring           Retire cet overlay au prochain démarrage
#   INSTALL_DIR=/opt/finflow
#   SKIP_BACKUP=1             Ne pas sauvegarder la DB avant update
#   SKIP_GIT=1                Ne pas faire git pull
#   SKIP_BUILD=1              up -d sans --build (déconseillé)
#   ENABLE_MONITORING=1       Même effet que --monitoring
#
# Le script :
#   1. snapshot Postgres + MinIO + secrets
#   2. git fetch + checkout + pull --ff-only
#   3. complète le .env (SMTP, observabilité) sans écraser l'existant
#   4. docker compose pull + up -d --build
#      (mode IP / IP+TLS / supervision via deploy/compose-files.sh)
#   5. migrate + sync_role_packs + bootstrap_all_tenants
#   6. health API sur http://127.0.0.1:8080/api/v1/health/
# =========================================================================
set -euo pipefail

INSTALL_DIR_DEFAULT="/opt/finflow"
REPO_URL_DEFAULT="https://github.com/Bouma-J/FinFlow.git"

if [[ -t 1 ]]; then
  C_INFO='\033[1;36m'
  C_OK='\033[1;32m'
  C_WARN='\033[1;33m'
  C_ERR='\033[1;31m'
  C_RST='\033[0m'
else
  C_INFO=''
  C_OK=''
  C_WARN=''
  C_ERR=''
  C_RST=''
fi

log()  { echo -e "${C_INFO}[INFO]${C_RST} $*"; }
ok()   { echo -e "${C_OK}[OK]${C_RST} $*"; }
warn() { echo -e "${C_WARN}[WARN]${C_RST} $*"; }
err()  { echo -e "${C_ERR}[ERR]${C_RST} $*" >&2; }
die()  { err "$*"; exit 1; }

need_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "Exécutez en root : sudo bash deploy/ubuntu-update.sh"
  fi
}

# Repli si compose-files.sh n'est pas encore tiré (1re update d'une vieille instance).
detect_compose_files_fallback() {
  local dir="$1"
  local mode="" tls=""
  if [[ -f "$dir/.finflow-deploy-mode" ]]; then
    mode="$(tr -d '[:space:]' < "$dir/.finflow-deploy-mode" || true)"
  fi
  if [[ -f "$dir/.finflow-tls-mode" ]]; then
    tls="$(tr -d '[:space:]' < "$dir/.finflow-tls-mode" || true)"
  fi
  if [[ "$mode" == "ip" || -n "$tls" ]]; then
    local files="-f docker-compose.yml -f docker-compose.prod.yml"
    if [[ -f "$dir/docker-compose.ip.yml" ]]; then
      files="${files} -f docker-compose.ip.yml"
    fi
    if [[ "$tls" == "le" || "$tls" == "selfsigned" ]] && [[ -f "$dir/docker-compose.ip-tls.yml" ]]; then
      files="${files} -f docker-compose.ip-tls.yml"
    fi
    echo "$files"
    return
  fi
  if [[ "$mode" == "domain" || "$mode" == "prod" ]]; then
    echo "-f docker-compose.yml -f docker-compose.prod.yml"
    return
  fi
  if [[ -f "$dir/docker-compose.ip.yml" && -f "$dir/.env" ]]; then
    if grep -Eq '^FINFLOW_PUBLIC_IP=' "$dir/.env" 2>/dev/null \
      || grep -Eq '^FRONTEND_BASE_URL=["'"'"']?https?://([0-9]{1,3}\.){3}[0-9]{1,3}' "$dir/.env" 2>/dev/null \
      || grep -Eq '^DJANGO_SECURE_SSL_REDIRECT=["'"'"']?False["'"'"']?' "$dir/.env" 2>/dev/null; then
      echo "-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.ip.yml"
      return
    fi
  fi
  echo "-f docker-compose.yml -f docker-compose.prod.yml"
}

append_monitoring_compose() {
  local dir="$1"
  local files="$2"
  local flag=""
  if [[ -f "$dir/.finflow-monitoring" ]]; then
    flag="$(tr -d '[:space:]' < "$dir/.finflow-monitoring" || true)"
  fi
  if [[ "$flag" == "1" && -f "$dir/docker-compose.monitoring.yml" ]]; then
    files="${files} -f docker-compose.monitoring.yml"
  fi
  printf '%s\n' "$files"
}

detect_compose_files() {
  local dir="$1"
  local files=""
  if [[ -f "$dir/deploy/compose-files.sh" ]]; then
    bash "$dir/deploy/compose-files.sh" "$dir"
    return
  fi
  files="$(detect_compose_files_fallback "$dir")"
  append_monitoring_compose "$dir" "$files"
}

compose() {
  # shellcheck disable=SC2086
  docker compose $COMPOSE_FILES "$@"
}

backup_db() {
  local dir="$1"
  local script="${dir}/deploy/backup/backup.sh"
  if [[ -x "$script" || -f "$script" ]]; then
    log "Snapshot pré-update (Postgres + MinIO + secrets)"
    if FINFLOW_DIR="$dir" BACKUP_PASSPHRASE_FILE="${BACKUP_PASSPHRASE_FILE:-/root/.finflow-backup-pass}" \
      SKIP_APP_PAUSE="${SKIP_APP_PAUSE:-0}" \
      bash "$script"; then
      ok "Snapshot pré-update OK"
      return
    fi
    warn "Snapshot complet impossible — repli dump SQL"
  fi
  local stamp out
  stamp="$(date +%Y%m%d_%H%M%S)"
  out="/var/backups/finflow"
  mkdir -p "$out"
  cd "$dir"
  log "Sauvegarde PostgreSQL → ${out}/finflow_preupdate_${stamp}.sql.gz"
  if compose exec -T db pg_dump -U finflow finflow 2>/dev/null | gzip > "$out/finflow_preupdate_${stamp}.sql.gz"; then
    ok "Backup OK : $out/finflow_preupdate_${stamp}.sql.gz"
  else
    warn "Backup DB impossible (stack arrêtée ?). Poursuite…"
    rm -f "$out/finflow_preupdate_${stamp}.sql.gz"
  fi
}

ensure_mail_env() {
  local dir="$1"
  local env_file="$dir/.env"
  local key
  [[ -f "$env_file" ]] || return 0

  if ! grep -Eq '^FIELD_ENCRYPTION_KEY=' "$env_file" 2>/dev/null; then
    key="$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n')"
    {
      echo
      echo "# Ajouté par ubuntu-update.sh — chiffrement SMTP filiale"
      printf 'FIELD_ENCRYPTION_KEY="%s"\n' "$key"
    } >> "$env_file"
    ok "FIELD_ENCRYPTION_KEY ajouté au .env"
  fi

  if ! grep -Eq '^SMTP_SSL_VERIFY=' "$env_file" 2>/dev/null; then
    echo 'SMTP_SSL_VERIFY="1"' >> "$env_file"
    ok "SMTP_SSL_VERIFY=1 ajouté au .env"
  fi

  if grep -Eq '^EMAIL_BACKEND=.*console' "$env_file" 2>/dev/null; then
    warn "EMAIL_BACKEND=console détecté — passez à smtp.EmailBackend pour un envoi réel (ou SMTP filiale en UI)."
  fi
}

ensure_observability_env() {
  local dir="$1"
  local env_file="$dir/.env"
  local key missing=0 flag=""
  [[ -f "$env_file" ]] || return 0

  for key in LOG_FORMAT SENTRY_DSN SENTRY_ENVIRONMENT SENTRY_TRACES_SAMPLE_RATE \
    PROMETHEUS_METRICS_TOKEN ALERT_WEBHOOK_TOKEN ALERT_EMAIL_TO; do
    if ! grep -Eq "^${key}=" "$env_file" 2>/dev/null; then
      missing=1
      break
    fi
  done
  if [[ -f "$dir/.finflow-monitoring" ]]; then
    flag="$(tr -d '[:space:]' < "$dir/.finflow-monitoring" || true)"
    if [[ "$flag" == "1" ]] && ! grep -Eq '^GRAFANA_ADMIN_PASSWORD=' "$env_file" 2>/dev/null; then
      missing=1
    fi
  fi
  [[ "$missing" -eq 1 ]] || return 0

  {
    echo
    echo "# Observabilité — ubuntu-update.sh (clés absentes uniquement, secrets existants conservés)"
  } >> "$env_file"

  if ! grep -Eq '^LOG_FORMAT=' "$env_file" 2>/dev/null; then
    echo 'LOG_FORMAT="json"' >> "$env_file"
    ok "LOG_FORMAT=json ajouté au .env"
  fi
  if ! grep -Eq '^SENTRY_DSN=' "$env_file" 2>/dev/null; then
    echo 'SENTRY_DSN=' >> "$env_file"
    ok "SENTRY_DSN vide ajouté (Sentry désactivé tant qu'une DSN n'est pas renseignée)"
  fi
  if ! grep -Eq '^SENTRY_ENVIRONMENT=' "$env_file" 2>/dev/null; then
    echo 'SENTRY_ENVIRONMENT="production"' >> "$env_file"
  fi
  if ! grep -Eq '^SENTRY_TRACES_SAMPLE_RATE=' "$env_file" 2>/dev/null; then
    echo 'SENTRY_TRACES_SAMPLE_RATE="0.1"' >> "$env_file"
  fi
  if ! grep -Eq '^PROMETHEUS_METRICS_TOKEN=' "$env_file" 2>/dev/null; then
    printf 'PROMETHEUS_METRICS_TOKEN="%s"\n' "$(openssl rand -hex 24)" >> "$env_file"
    ok "PROMETHEUS_METRICS_TOKEN généré dans le .env"
  fi
  if ! grep -Eq '^ALERT_WEBHOOK_TOKEN=' "$env_file" 2>/dev/null; then
    printf 'ALERT_WEBHOOK_TOKEN="%s"\n' "$(openssl rand -hex 24)" >> "$env_file"
    ok "ALERT_WEBHOOK_TOKEN généré dans le .env"
  fi
  if ! grep -Eq '^ALERT_EMAIL_TO=' "$env_file" 2>/dev/null; then
    echo 'ALERT_EMAIL_TO=' >> "$env_file"
  fi
  if [[ "$flag" == "1" ]] && ! grep -Eq '^GRAFANA_ADMIN_PASSWORD=' "$env_file" 2>/dev/null; then
    printf 'GRAFANA_ADMIN_PASSWORD="%s"\n' "$(openssl rand -hex 16)" >> "$env_file"
    ok "GRAFANA_ADMIN_PASSWORD généré dans le .env (compte Grafana admin)"
  fi
}

resolve_git_branch() {
  local dir="$1"
  local saved="" current=""
  if [[ -n "${GIT_BRANCH:-}" ]]; then
    printf '%s\n' "$GIT_BRANCH"
    return
  fi
  if [[ -f "$dir/.finflow-git-branch" ]]; then
    saved="$(tr -d '[:space:]' < "$dir/.finflow-git-branch" || true)"
    if [[ -n "$saved" ]]; then
      printf '%s\n' "$saved"
      return
    fi
  fi
  if [[ -d "$dir/.git" ]]; then
    current="$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [[ -n "$current" && "$current" != "HEAD" ]]; then
      printf '%s\n' "$current"
      return
    fi
  fi
  printf '%s\n' "main"
}

remember_git_branch() {
  local dir="$1"
  local branch="$2"
  printf '%s\n' "$branch" > "$dir/.finflow-git-branch"
  chmod 644 "$dir/.finflow-git-branch"
}

apply_monitoring_flag() {
  local dir="$1"
  local flag="${ENABLE_MONITORING:-}"
  if [[ "$flag" == "1" ]]; then
    printf '1\n' > "$dir/.finflow-monitoring"
    chmod 644 "$dir/.finflow-monitoring"
    if [[ -f "$dir/docker-compose.monitoring.yml" ]]; then
      ok "Supervision activée (Prometheus, Alertmanager, Loki, Grafana)."
    else
      warn "Marqueur supervision posé, mais docker-compose.monitoring.yml est absent."
    fi
  elif [[ "$flag" == "0" ]]; then
    rm -f "$dir/.finflow-monitoring"
    ok "Supervision retirée de cette instance."
  fi
}

pull_code() {
  local dir="$1"
  local branch="$2"
  local repo="$3"

  cd "$dir"
  if [[ ! -d .git ]]; then
    warn "Pas de dépôt git dans $dir — skip git pull."
    return
  fi
  log "git fetch / checkout ${branch} / pull --ff-only…"
  git remote set-url origin "$repo" 2>/dev/null || true
  git fetch --prune origin "$branch"
  if git show-ref --verify --quiet "refs/heads/${branch}"; then
    git checkout "$branch"
  else
    git checkout -b "$branch" --track "origin/${branch}"
  fi
  git pull --ff-only origin "$branch"
  ok "Code à jour : $(git rev-parse --short HEAD) ($(git log -1 --pretty=%s))"
}

chmod_deploy_scripts() {
  local dir="$1"
  chmod +x "$dir/deploy/ubuntu-update.sh" \
    "$dir/deploy/ubuntu-install.sh" \
    "$dir/deploy/ubuntu-install-ip.sh" \
    "$dir/deploy/compose-files.sh" \
    2>/dev/null || true
  chmod +x "$dir/deploy/tls-ip/enable-ip-tls.sh" 2>/dev/null || true
  chmod +x "$dir/deploy/backup/"*.sh 2>/dev/null || true
}

rebuild_stack() {
  local dir="$1"
  local with_build="${2:-1}"
  cd "$dir"
  log "Docker Compose pull…"
  compose pull || true
  if [[ "$with_build" == "1" ]]; then
    log "Build & redémarrage (up -d --build)…"
    compose up -d --build
  else
    log "Redémarrage sans rebuild (up -d)…"
    compose up -d
  fi
  ok "Stack redémarrée."
}

wait_health() {
  log "Attente health API (max ~3 min)…"
  local i
  for i in $(seq 1 36); do
    if curl -fsS http://127.0.0.1:8080/api/v1/health/ >/dev/null 2>&1; then
      ok "API prête : http://127.0.0.1:8080/api/v1/health/"
      return 0
    fi
    sleep 5
  done
  warn "Health check encore en échec — logs : compose logs --tail=100 backend"
  return 1
}

post_deploy() {
  local dir="$1"
  cd "$dir"
  log "Migrations…"
  compose exec -T backend python manage.py migrate --noinput
  ok "Migrations appliquées."

  log "Synchronisation packs de rôles (dont Administrateur de crédit)…"
  compose exec -T backend python manage.py sync_role_packs \
    && ok "Packs RBAC synchronisés." \
    || warn "sync_role_packs à relancer."

  log "Bootstrap filiales (catalogue, Perfect, circuits ML/Dation/Formalisation)…"
  compose exec -T backend python manage.py bootstrap_all_tenants \
    && ok "Filiales bootstrapées." \
    || warn "bootstrap_all_tenants à relancer (aucune filiale ?)."
}

refresh_helpers() {
  local dir="$1"
  mkdir -p "$dir/scripts"

  cat > "$dir/scripts/finflow" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$dir"
if [[ -f "$dir/deploy/compose-files.sh" ]]; then
  exec docker compose \$(bash "$dir/deploy/compose-files.sh" "$dir") "\$@"
fi
exec docker compose -f docker-compose.yml -f docker-compose.prod.yml "\$@"
EOF
  chmod +x "$dir/scripts/finflow"
  ln -sfn "$dir/scripts/finflow" /usr/local/bin/finflow

  if [[ -f "$dir/deploy/ubuntu-update.sh" ]]; then
    ln -sfn "$dir/deploy/ubuntu-update.sh" "$dir/scripts/update.sh"
    ln -sfn "$dir/deploy/ubuntu-update.sh" /usr/local/bin/finflow-update
  fi

  ensure_backup_cron "$dir"
  ok "Helpers rafraîchis : finflow, finflow-update"
}

ensure_backup_cron() {
  local dir="$1"
  [[ -f "$dir/deploy/backup/wire-install.sh" ]] \
    || die "deploy/backup/wire-install.sh manquant — sauvegarde automatique obligatoire."
  bash "$dir/deploy/backup/wire-install.sh" "$dir" \
    || die "Cron de sauvegarde non posé (/var/backups/finflow)."
}

print_summary() {
  local dir="$1"
  local branch="${2:-}"
  local mode="" tls="" mon="non"
  [[ -f "$dir/.finflow-deploy-mode" ]] && mode="$(tr -d '[:space:]' < "$dir/.finflow-deploy-mode")"
  [[ -f "$dir/.finflow-tls-mode" ]] && tls="$(tr -d '[:space:]' < "$dir/.finflow-tls-mode")"
  if [[ -f "$dir/.finflow-monitoring" ]] && [[ "$(tr -d '[:space:]' < "$dir/.finflow-monitoring")" == "1" ]]; then
    mon="oui — Grafana http://127.0.0.1:3000 (admin / GRAFANA_ADMIN_PASSWORD dans .env)"
  fi
  cat <<EOF

${C_OK}═══════════════════════════════════════════════════════════${C_RST}
${C_OK} FIN_FLOW — mise à jour terminée${C_RST}
${C_OK}═══════════════════════════════════════════════════════════${C_RST}

  Répertoire  : ${dir}
  Branche     : ${branch:-?}
  Mode        : ${mode:-inconnu}${tls:+ + TLS ${tls}}
  Supervision : ${mon}
  Compose     : docker compose ${COMPOSE_FILES}
  Commandes   : finflow ps | finflow logs -f backend
  Prochaine   : sudo finflow-update
                (reste sur ${branch:-la branche enregistrée})

  Sauvegardes : cron 02:30 → /var/backups/finflow/snapshots (hors projet)
    sudo FINFLOW_DIR=${dir} ${dir}/deploy/backup/backup.sh

  Activer la supervision au prochain passage :
    sudo env ENABLE_MONITORING=1 finflow-update

  HTTPS IP interne (auto-signé, sans HSTS) :
    sudo bash ${dir}/deploy/tls-ip/enable-ip-tls.sh ${dir} --self-signed

  Appliqué par cette mise à jour :
    • migrations DB
    • packs de rôles, dont Administrateur de crédit
    • logs JSON, /metrics et webhook d'alertes (clés ajoutées au .env si absentes)

EOF
}

run_check() {
  local dir="$1"
  [[ -d "$dir" ]] || die "Répertoire introuvable : $dir"
  [[ -f "$dir/docker-compose.yml" ]] || die "docker-compose.yml manquant dans $dir"
  [[ -f "$dir/docker-compose.prod.yml" ]] || die "docker-compose.prod.yml manquant dans $dir"

  local via="fallback"
  if [[ -f "$dir/deploy/compose-files.sh" ]]; then
    via="compose-files.sh"
  fi
  COMPOSE_FILES="$(detect_compose_files "$dir")"
  local fallback
  fallback="$(detect_compose_files_fallback "$dir")"

  echo "FIN_FLOW — contrôle ubuntu-update (--check)"
  echo "  dir     : $dir"
  echo "  via     : $via"
  echo "  compose : docker compose $COMPOSE_FILES"
  echo "  fallback: docker compose $fallback"

  local f
  for f in docker-compose.yml docker-compose.prod.yml; do
    [[ -f "$dir/$f" ]] || die "Manquant : $f"
  done
  if echo "$COMPOSE_FILES" | grep -q 'docker-compose.ip.yml'; then
    [[ -f "$dir/docker-compose.ip.yml" ]] || die "Mode IP mais docker-compose.ip.yml absent"
  fi
  if echo "$COMPOSE_FILES" | grep -q 'docker-compose.ip-tls.yml'; then
    [[ -f "$dir/docker-compose.ip-tls.yml" ]] || die "Mode IP+TLS mais docker-compose.ip-tls.yml absent"
  fi
  if echo "$COMPOSE_FILES" | grep -q 'docker-compose.monitoring.yml'; then
    [[ -f "$dir/docker-compose.monitoring.yml" ]] || die "Supervision demandée mais docker-compose.monitoring.yml absent"
  fi

  if [[ -f "$dir/deploy/compose-files.sh" ]] && [[ "$COMPOSE_FILES" != "$fallback" ]]; then
    # Le fallback ignore l'heuristique FINFLOW_PUBLIC_IP si mode=domain ; sinon ils doivent coller
    if [[ ! -f "$dir/.finflow-deploy-mode" ]] || [[ "$(tr -d '[:space:]' < "$dir/.finflow-deploy-mode")" != "domain" ]]; then
      warn "compose-files.sh et fallback divergent (OK si heuristique plus riche)."
    fi
  fi

  echo "  backups : /var/backups/finflow/snapshots (hors projet)"
  if [[ -f /etc/cron.d/finflow-backup ]]; then
    echo "  cron    : /etc/cron.d/finflow-backup"
    grep -v '^#' /etc/cron.d/finflow-backup | grep -v '^$' || true
  else
    warn "Cron /etc/cron.d/finflow-backup absent — l'update le posera via wire-install.sh"
  fi
  [[ -f "$dir/deploy/backup/backup.sh" ]] || warn "deploy/backup/backup.sh manquant"
  [[ -f "$dir/deploy/backup/wire-install.sh" ]] || warn "deploy/backup/wire-install.sh manquant"

  ok "Contrôle de résolution Compose : OK"
}

main() {
  local check=0
  local dir=""
  local arg
  local -a cleaned=()
  for arg in "$@"; do
    cleaned+=("${arg%$'\r'}")
  done
  set -- "${cleaned[@]}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check) check=1; shift ;;
      --branch)
        [[ $# -ge 2 ]] || die "--branch attend un nom de branche."
        GIT_BRANCH="$2"
        shift 2
        ;;
      --monitoring) ENABLE_MONITORING=1; shift ;;
      --no-monitoring) ENABLE_MONITORING=0; shift ;;
      -h|--help)
        sed -n '2,/^set -euo pipefail/p' "$0"
        exit 0
        ;;
      *)
        dir="$1"
        shift
        ;;
    esac
  done
  dir="${dir:-${INSTALL_DIR:-$INSTALL_DIR_DEFAULT}}"

  if [[ "$check" -eq 1 ]]; then
    run_check "$dir"
    return 0
  fi

  need_root

  local branch repo
  branch="$(resolve_git_branch "$dir")"
  repo="${REPO_URL:-$REPO_URL_DEFAULT}"
  local skip_backup="${SKIP_BACKUP:-0}"
  local skip_git="${SKIP_GIT:-0}"
  local skip_build="${SKIP_BUILD:-0}"
  local with_build=1
  [[ "$skip_build" == "1" ]] && with_build=0

  echo
  echo "FIN_FLOW — mise à jour production"
  echo "Guide : documentation/13-guide-deploiement-ubuntu.md"
  echo

  [[ -d "$dir" ]] || die "Répertoire introuvable : $dir"
  [[ -f "$dir/docker-compose.yml" ]] || die "docker-compose.yml manquant dans $dir"
  [[ -f "$dir/docker-compose.prod.yml" ]] || die "docker-compose.prod.yml manquant dans $dir"
  [[ -f "$dir/.env" ]] || die "Fichier .env manquant dans $dir — ne pas écraser les secrets."

  COMPOSE_FILES="$(detect_compose_files "$dir")"
  log "Install dir : $dir"
  log "Compose     : docker compose $COMPOSE_FILES"
  log "Branche     : $branch"
  if [[ "$branch" == "main" && -z "${GIT_BRANCH:-}" && ! -f "$dir/.finflow-git-branch" ]]; then
    warn "Aucune branche enregistrée : la mise à jour reste sur main."
    warn "Serveur de test : sudo env GIT_BRANCH=cursor/ameliorations-techniques-acda ENABLE_MONITORING=1 finflow-update"
  fi

  if [[ "$skip_backup" != "1" ]]; then
    backup_db "$dir"
  else
    warn "SKIP_BACKUP=1 — pas de dump DB."
  fi

  if [[ "$skip_git" != "1" ]]; then
    pull_code "$dir" "$branch" "$repo"
  else
    warn "SKIP_GIT=1 — pas de git pull."
  fi
  remember_git_branch "$dir" "$branch"

  chmod_deploy_scripts "$dir"
  apply_monitoring_flag "$dir"
  COMPOSE_FILES="$(detect_compose_files "$dir")"
  log "Compose (après pull) : docker compose $COMPOSE_FILES"
  ensure_backup_cron "$dir"

  ensure_mail_env "$dir"
  ensure_observability_env "$dir"
  rebuild_stack "$dir" "$with_build"
  wait_health || true
  post_deploy "$dir"
  refresh_helpers "$dir"
  wait_health || true
  print_summary "$dir" "$branch"
}

main "$@"

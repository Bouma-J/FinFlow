#!/usr/bin/env bash
# Résout les fichiers Compose d'une instance FinFlow.
#   bash deploy/compose-files.sh /opt/finflow
#   source deploy/compose-files.sh && finflow_compose_files /opt/finflow
finflow_compose_files() {
  local dir="$1"
  local mode="" tls="" files=""

  if [[ -f "$dir/.finflow-deploy-mode" ]]; then
    mode="$(tr -d '[:space:]' < "$dir/.finflow-deploy-mode" || true)"
  fi
  if [[ -f "$dir/.finflow-tls-mode" ]]; then
    tls="$(tr -d '[:space:]' < "$dir/.finflow-tls-mode" || true)"
  fi

  _ff_is_ip() {
    [[ "$mode" == "ip" || -n "$tls" ]] && return 0
    [[ -f "$dir/docker-compose.ip.yml" && -f "$dir/.env" ]] || return 1
    grep -Eq '^FINFLOW_PUBLIC_IP=' "$dir/.env" 2>/dev/null && return 0
    grep -Eq '^FRONTEND_BASE_URL=["'"'"']?https?://([0-9]{1,3}\.){3}[0-9]{1,3}' "$dir/.env" 2>/dev/null && return 0
    grep -Eq '^DJANGO_SECURE_SSL_REDIRECT=["'"'"']?False["'"'"']?' "$dir/.env" 2>/dev/null && return 0
    return 1
  }

  _ff_finish() {
    local chosen="$1"
    local flag=""
    if [[ -f "$dir/.finflow-monitoring" ]]; then
      flag="$(tr -d '[:space:]' < "$dir/.finflow-monitoring" || true)"
    fi
    if [[ "$flag" == "1" && -f "$dir/docker-compose.monitoring.yml" ]]; then
      chosen="${chosen} -f docker-compose.monitoring.yml"
    fi
    printf '%s\n' "$chosen"
  }

  if [[ "$mode" == "domain" || "$mode" == "prod" ]] && [[ -z "$tls" ]]; then
    _ff_finish "-f docker-compose.yml -f docker-compose.prod.yml"
    return
  fi

  if _ff_is_ip; then
    files="-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.ip.yml"
    if [[ "$tls" == "le" || "$tls" == "selfsigned" ]]; then
      if [[ -f "$dir/docker-compose.ip-tls.yml" ]]; then
        files="${files} -f docker-compose.ip-tls.yml"
      fi
    fi
    _ff_finish "$files"
    return
  fi

  _ff_finish "-f docker-compose.yml -f docker-compose.prod.yml"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  finflow_compose_files "${1:-.}"
fi

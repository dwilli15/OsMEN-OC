#!/usr/bin/env bash

set -euo pipefail

LOCAL_SECRET_DIR="${HOME}/.config/osmen/secrets"
OUTPUT_ROOT="${HOME}/.local/share/osmen/credential-kit"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
OUTPUT_DIR="${OUTPUT_ROOT}/${TIMESTAMP}"
OUTPUT_FILE="${OUTPUT_DIR}/credential-kit.txt"

log_info() {
  echo "[INFO]  $*"
}

log_warn() {
  echo "[WARN]  $*" >&2
}

log_error() {
  echo "[ERROR] $*" >&2
}

check_prerequisites() {
  local command_name

  for command_name in podman sops python3; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
      log_error "Missing required command: ${command_name}"
      exit 1
    fi
  done

  if [[ ! -d "${LOCAL_SECRET_DIR}" ]]; then
    log_error "Local secret directory not found: ${LOCAL_SECRET_DIR}"
    exit 1
  fi
}

write_credential_kit() {
  mkdir -p "${OUTPUT_DIR}"
  chmod 700 "${OUTPUT_DIR}"

  {
    echo "OsMEN Credential Kit"
    echo "Generated: $(date -Iseconds)"
    echo "Host: $(hostname)"
    echo
    echo "=== Local SOPS Secret Backups ==="
    local file_path
    shopt -s nullglob
    for file_path in "${LOCAL_SECRET_DIR}"/*.enc.yaml; do
      echo
      echo "--- $(basename "${file_path}") ---"
      sops -d "${file_path}"
    done
    shopt -u nullglob
    echo
    echo "=== Podman Runtime Secrets ==="
    local secret_name secret_value
    while IFS= read -r secret_name; do
      secret_value=$(podman secret inspect "${secret_name}" --showsecret \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)[0].get("SecretData", ""))')
      printf '%s: %s\n' "${secret_name}" "${secret_value}"
    done < <(podman secret ls --format "{{.Name}}" | sort)
    echo
    echo "=== Age Key Path ==="
    echo "${HOME}/.config/sops/age/keys.txt"
    echo
    echo "Print this file and store it offline with the age key backup."
  } >"${OUTPUT_FILE}"

  chmod 600 "${OUTPUT_FILE}"
}

main() {
  check_prerequisites
  write_credential_kit
  log_info "Credential kit written to ${OUTPUT_FILE}"
  log_warn "This file is plaintext. Print/store offline and remove old exports you no longer need."
}

main "$@"
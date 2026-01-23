#!/usr/bin/env bash
set -euo pipefail

failures=0

check() {
  local label="$1"
  local status="$2"
  local detail="$3"

  if [[ "$status" == "ok" ]]; then
    printf 'OK   %-30s %s\n' "$label" "$detail"
  elif [[ "$status" == "warn" ]]; then
    printf 'WARN %-30s %s\n' "$label" "$detail"
  else
    printf 'FAIL %-30s %s\n' "$label" "$detail"
    failures=$((failures + 1))
  fi
}

if command -v python3 >/dev/null 2>&1; then
  check "python3" ok "found"
else
  check "python3" fail "missing"
fi

if [[ -d .venv ]]; then
  check "venv" ok ".venv exists"
else
  check "venv" fail "missing .venv"
fi

if [[ -f .env ]]; then
  check ".env" ok "present"
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
else
  check ".env" fail "missing .env"
fi

if [[ -f config/default.yaml ]]; then
  check "config/default.yaml" ok "present"
else
  check "config/default.yaml" fail "missing"
fi

storages_root=""
if [[ -n "${STORAGES_ROOT:-}" ]]; then
  storages_root="$STORAGES_ROOT"
else
  storages_root="./storages"
  if command -v python3 >/dev/null 2>&1; then
    storages_root=$(python3 - <<'PY'
from pathlib import Path
try:
    import yaml
except Exception:
    print("./storages")
    raise SystemExit(0)

path = Path("config/default.yaml")
if not path.exists():
    print("./storages")
    raise SystemExit(0)

with path.open("r", encoding="utf-8") as fh:
    data = yaml.safe_load(fh) or {}

storages_cfg = data.get("storages", {}) if isinstance(data, dict) else {}
print(storages_cfg.get("root_path") or "./storages")
PY
) || storages_root="./storages"
  fi
fi

if [[ -d "$storages_root" ]]; then
  check "storages dir" ok "$storages_root"
else
  check "storages dir" fail "$storages_root missing"
fi

if [[ -n "${OPENAI_API_KEY:-}" && "${OPENAI_API_KEY}" != "put-your-key-here" ]]; then
  check "OPENAI_API_KEY" ok "configured"
else
  check "OPENAI_API_KEY" fail "missing or placeholder"
fi

if [[ -n "${DEFAULT_STORAGE:-}" ]]; then
  check "DEFAULT_STORAGE" ok "$DEFAULT_STORAGE"
else
  check "DEFAULT_STORAGE" fail "not set"
fi

if [[ -n "${ZSUS_HTTP_PORT:-}" ]]; then
  if [[ "${ZSUS_HTTP_PORT}" =~ ^[0-9]+$ ]] && ((ZSUS_HTTP_PORT >= 1 && ZSUS_HTTP_PORT <= 65535)); then
    check "ZSUS_HTTP_PORT" ok "$ZSUS_HTTP_PORT"
  else
    check "ZSUS_HTTP_PORT" warn "invalid (${ZSUS_HTTP_PORT})"
  fi
else
  check "ZSUS_HTTP_PORT" ok "not set"
fi

db_filename="storage.db"
if command -v python3 >/dev/null 2>&1; then
  db_filename=$(python3 - <<'PY'
import os
from pathlib import Path
try:
    import yaml
except Exception:
    print("storage.db")
    raise SystemExit(0)

path = Path("config/default.yaml")
if not path.exists():
    print("storage.db")
    raise SystemExit(0)

with path.open("r", encoding="utf-8") as fh:
    data = yaml.safe_load(fh) or {}

storage_cfg = data.get("storage", {}) if isinstance(data, dict) else {}
print(storage_cfg.get("sqlite_filename") or "storage.db")
PY
) || db_filename="storage.db"
fi

if [[ -n "${DEFAULT_STORAGE:-}" ]]; then
  db_path="$storages_root/$DEFAULT_STORAGE/$db_filename"
  if [[ -f "$db_path" ]]; then
    check "storage database" ok "$db_path"
  else
    check "storage database" fail "$db_path missing"
  fi
else
  check "storage database" fail "DEFAULT_STORAGE not set"
fi

if [[ $failures -gt 0 ]]; then
  exit 1
fi

#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Run ./boot.sh first." >&2
  exit 1
fi

. .venv/bin/activate
exec python -m src.interfaces.http.server "$@"

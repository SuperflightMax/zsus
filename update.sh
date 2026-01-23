#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d .git ]]; then
  echo "Not a git repository (.git missing)." >&2
  exit 1
fi

git pull --rebase

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Run ./boot.sh first." >&2
  exit 1
fi

. .venv/bin/activate
python -m pip install -e .

mkdir -p logs
printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$(git rev-parse --short HEAD)" >> logs/deploy.log

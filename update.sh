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

was_running=0
pid_file="run/zsus_http.pid"
if [[ -z "${ZSUS_NO_RESTART:-}" && -f "$pid_file" ]]; then
  pid=$(cat "$pid_file")
  if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
    was_running=1
    ./stop.sh
  fi
fi

. .venv/bin/activate
python -m pip install -e .

mkdir -p logs
printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$(git rev-parse --short HEAD)" >> logs/deploy.log

if [[ -z "${ZSUS_NO_RESTART:-}" && $was_running -eq 1 ]]; then
  ./start.sh
fi

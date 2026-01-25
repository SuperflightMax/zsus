#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d .venv ]]; then
  echo "Missing .venv. Run ./boot.sh first." >&2
  exit 1
fi

mkdir -p logs run
pid_file="run/zsus_http.pid"

if [[ -f "$pid_file" ]]; then
  pid=$(cat "$pid_file")
  if [[ -n "${pid}" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "Already running (pid=${pid})"
    exit 0
  fi
fi

. .venv/bin/activate
nohup python -m src.interfaces.http.server >> logs/http.log 2>&1 &

pid=$!
echo "$pid" > "$pid_file"

echo "Started (pid=${pid})"

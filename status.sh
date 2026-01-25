#!/usr/bin/env bash
set -euo pipefail

pid_file="run/zsus_http.pid"

if [[ ! -f "$pid_file" ]]; then
  echo "STOPPED"
  exit 0
fi

pid=$(cat "$pid_file")
if [[ -z "${pid}" ]]; then
  rm -f "$pid_file"
  echo "STOPPED (stale pidfile removed)"
  exit 0
fi

if kill -0 "$pid" 2>/dev/null; then
  echo "RUNNING pid=${pid}"
  exit 0
fi

rm -f "$pid_file"

echo "STOPPED (stale pidfile pid=${pid} removed)"

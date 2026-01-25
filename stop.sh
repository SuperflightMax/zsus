#!/usr/bin/env bash
set -euo pipefail

pid_file="run/zsus_http.pid"

if [[ ! -f "$pid_file" ]]; then
  echo "Not running"
  exit 0
fi

pid=$(cat "$pid_file")
if [[ -z "${pid}" ]]; then
  rm -f "$pid_file"
  echo "Not running (stale pidfile removed)"
  exit 0
fi

if ! kill -0 "$pid" 2>/dev/null; then
  rm -f "$pid_file"
  echo "Not running (stale pidfile removed)"
  exit 0
fi

kill "$pid"

timeout=5
while kill -0 "$pid" 2>/dev/null && [[ $timeout -gt 0 ]]; do
  sleep 1
  timeout=$((timeout - 1))
done

if kill -0 "$pid" 2>/dev/null; then
  kill -9 "$pid"
fi

rm -f "$pid_file"

echo "Stopped"

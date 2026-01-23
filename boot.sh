#!/usr/bin/env bash
set -euo pipefail

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .

if [[ ! -f .env ]]; then
  cp env.example .env
fi

mkdir -p logs

cat <<'NEXT_STEPS'
Boot complete.

Next steps:
- Edit .env with your OpenAI credentials.
- Run ./doctor.sh to verify setup.
- Start CLI via ./cli.sh
NEXT_STEPS

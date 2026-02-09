#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ecosystem="${root_dir}/ops/pm2/ecosystem.config.js"

pm2 stop "$ecosystem"

#!/usr/bin/env bash
set -u

usage() {
  cat <<'EOF'
Usage: update_all.sh [--no-restart] [--only <id>]

Updates all instances under ~/zs/instances/<id>.

Options:
  --no-restart    Run update.sh with ZSUS_NO_RESTART=1
  --only <id>     Update only one instance
EOF
}

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
instances_dir="${root_dir}/instances"
no_restart=0
only_id=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-restart)
      no_restart=1
      shift
      ;;
    --only)
      only_id="${2:-}"
      if [[ -z "$only_id" ]]; then
        echo "Missing value for --only" >&2
        usage >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "$instances_dir" ]]; then
  echo "Instances directory not found: $instances_dir" >&2
  exit 1
fi

shopt -s nullglob
instance_paths=("$instances_dir"/*)
if [[ ${#instance_paths[@]} -eq 0 ]]; then
  echo "No instances found in $instances_dir" >&2
  exit 1
fi

ok_instances=()
fail_instances=()

for instance_path in "${instance_paths[@]}"; do
  [[ -d "$instance_path" ]] || continue
  instance_id="$(basename "$instance_path")"
  if [[ -n "$only_id" && "$instance_id" != "$only_id" ]]; then
    continue
  fi

  echo "==> ${instance_id}"
  status="ok"

  if [[ ! -d "$instance_path/.venv" ]]; then
    if ! (cd "$instance_path" && ./boot.sh); then
      status="fail"
    fi
  fi

  if [[ "$status" == "ok" ]]; then
    if [[ $no_restart -eq 1 ]]; then
      if ! (cd "$instance_path" && ZSUS_NO_RESTART=1 ./update.sh); then
        status="fail"
      fi
    else
      if ! (cd "$instance_path" && ./update.sh); then
        status="fail"
      fi
    fi
  fi

  if [[ "$status" == "ok" ]]; then
    ok_instances+=("$instance_id")
  else
    fail_instances+=("$instance_id")
  fi
done

if [[ -n "$only_id" && ${#ok_instances[@]} -eq 0 && ${#fail_instances[@]} -eq 0 ]]; then
  echo "Instance not found: $only_id" >&2
  exit 1
fi

echo ""
printf "%-20s %s\n" "instance" "status"
printf "%-20s %s\n" "--------" "------"
for instance_id in "${ok_instances[@]}"; do
  printf "%-20s %s\n" "$instance_id" "ok"
done
for instance_id in "${fail_instances[@]}"; do
  printf "%-20s %s\n" "$instance_id" "fail"
done

if [[ ${#fail_instances[@]} -gt 0 ]]; then
  exit 1
fi

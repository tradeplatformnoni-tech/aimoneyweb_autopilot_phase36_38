#!/usr/bin/env bash
set -euo pipefail
start="${1:-8090}"
end="${2:-8099}"
for p in $(seq "$start" "$end"); do
  if ! lsof -i :"$p" >/dev/null 2>&1; then
    echo "$p"
    exit 0
  fi
done
echo "NOFREE" && exit 1

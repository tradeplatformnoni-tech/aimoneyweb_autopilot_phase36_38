#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${NL_BUCKET:-}" ]]; then
  echo "⚠️  NL_BUCKET not set, skipping initial state pull"
  exit 0
fi

echo "☁️  Pulling initial state from $NL_BUCKET/state ..."
mkdir -p /app/state

if gsutil -m rsync -r "$NL_BUCKET/state" /app/state 2>&1; then
  echo "✅ Initial state pulled successfully"
else
  echo "⚠️  Initial state pull failed (container will start anyway)"
fi


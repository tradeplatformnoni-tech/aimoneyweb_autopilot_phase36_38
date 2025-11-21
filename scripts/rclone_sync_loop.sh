#!/usr/bin/env bash
# Periodic Google Drive Sync Wrapper
# Runs rclone_sync.sh every 30 minutes

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
SYNC_INTERVAL="${RCLONE_SYNC_INTERVAL:-1800}"  # 30 minutes default

while true; do
  NOW="$(date '+%F %T')"
  echo "[$NOW] 🔄 Starting periodic Google Drive sync..." >> "$ROOT/logs/drive_sync_loop.log" 2>&1
  bash "$ROOT/scripts/rclone_sync.sh" >> "$ROOT/logs/drive_sync_loop.log" 2>&1 || true
  echo "[$NOW] ⏸️  Sync completed. Waiting ${SYNC_INTERVAL}s until next sync..." >> "$ROOT/logs/drive_sync_loop.log" 2>&1
  sleep "$SYNC_INTERVAL"
done


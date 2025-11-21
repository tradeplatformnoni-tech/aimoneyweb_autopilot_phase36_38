#!/usr/bin/env bash
# NeoLight Fly.io State Synchronization Script
# ============================================
# Syncs state/runtime/logs to/from Fly.io before/after deployment
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="${FLY_APP:-neolight-cloud}"
SYNC_DIRECTION="${1:-to}"  # "to" = local to Fly.io, "from" = Fly.io to local

red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }

if [ "$SYNC_DIRECTION" = "to" ]; then
    green "📤 Syncing state TO Fly.io..."
    
    # Create temporary archive
    TMP_ARCHIVE="/tmp/neolight_state_$(date +%s).tar.gz"
    green "Creating archive..."
    tar -czf "$TMP_ARCHIVE" -C "$ROOT_DIR" state/ runtime/ 2>/dev/null || yellow "Some files may be locked"
    
    # Copy to Fly.io
    green "Uploading to Fly.io..."
    flyctl ssh sftp shell --app "$APP_NAME" <<EOF
put $TMP_ARCHIVE /app/state_sync.tar.gz
EOF
    
    # Extract on Fly.io
    green "Extracting on Fly.io..."
    flyctl ssh console --app "$APP_NAME" -C "cd /app && tar -xzf state_sync.tar.gz && rm state_sync.tar.gz" || yellow "Extraction may have failed"
    
    # Cleanup
    rm -f "$TMP_ARCHIVE"
    green "✅ Sync to Fly.io complete!"
    
elif [ "$SYNC_DIRECTION" = "from" ]; then
    green "📥 Syncing state FROM Fly.io..."
    
    # Download from Fly.io
    green "Downloading from Fly.io..."
    flyctl ssh sftp shell --app "$APP_NAME" <<EOF
get /app/state /tmp/neolight_state_remote
get /app/runtime /tmp/neolight_runtime_remote
EOF
    
    # Extract locally
    green "Extracting locally..."
    if [ -f /tmp/neolight_state_remote ]; then
        tar -xzf /tmp/neolight_state_remote -C "$ROOT_DIR" || yellow "Extraction may have failed"
        rm -f /tmp/neolight_state_remote
    fi
    if [ -f /tmp/neolight_runtime_remote ]; then
        tar -xzf /tmp/neolight_runtime_remote -C "$ROOT_DIR" || yellow "Extraction may have failed"
        rm -f /tmp/neolight_runtime_remote
    fi
    
    green "✅ Sync from Fly.io complete!"
else
    red "❌ Invalid direction: $SYNC_DIRECTION"
    echo "Usage: $0 [to|from]"
    exit 1
fi



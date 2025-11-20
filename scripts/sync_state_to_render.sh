#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ ☁️ Sync Local State to Render via Cloud Storage                  ║
# ║ Syncs local state files to cloud, then Render can pull them     ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Load credentials
if [ -f "$ROOT/.api_credentials" ]; then
    source <(grep -v '^#' "$ROOT/.api_credentials" | grep -v '^$' | sed 's/^/export /')
fi

RCLONE_REMOTE="${RCLONE_REMOTE:-neo_remote}"
RCLONE_PATH="${RCLONE_PATH:-neolight/state}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }

echo "═══════════════════════════════════════════════════════════════"
echo "☁️ Syncing Local State to Cloud (for Render to access)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if ! command -v rclone >/dev/null 2>&1; then
    warn "rclone not installed. Install: brew install rclone"
    exit 1
fi

info "Syncing state files to cloud storage..."
info "Remote: $RCLONE_REMOTE"
info "Path: $RCLONE_PATH/state"

# Sync state files
rclone copy "$ROOT/state" "${RCLONE_REMOTE}:${RCLONE_PATH}/state" \
    --create-empty-src-dirs \
    --transfers 4 \
    --checkers 8 \
    --progress \
    --exclude "*.lock" \
    --exclude "*.pid" \
    --exclude "*.tmp" || {
    warn "State sync failed"
    exit 1
}

info "✅ State files synced to cloud!"
echo ""
echo "📋 Next Steps:"
echo "   1. Render agents will sync state from cloud on startup"
echo "   2. Or wait for agents to generate new data"
echo "   3. Check dashboard in 5-10 minutes"
echo ""
echo "═══════════════════════════════════════════════════════════════"


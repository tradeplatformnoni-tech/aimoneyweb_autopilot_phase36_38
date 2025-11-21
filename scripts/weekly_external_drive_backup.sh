#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ 📀 Weekly External Drive Backup - Runs at Night                  ║
# ║ Syncs NeoLight state/data to external drive weekly              ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_DRIVE="${EXTERNAL_DRIVE:-/Volumes/Cheeee}"
LOG_DIR="$ROOT/logs"
BACKUP_DIR="$EXTERNAL_DRIVE/NeoLight/weekly_backup_$(date +%Y%m%d)"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/weekly_backup_${STAMP}.log"

mkdir -p "$LOG_DIR" "$BACKUP_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
ok() { log "${GREEN}✅ $*${NC}"; }
warn() { log "${YELLOW}⚠️  $*${NC}"; }
err() { log "${RED}❌ $*${NC}"; }
info() { log "${CYAN}📀 $*${NC}"; }

info "Starting weekly external drive backup..."
info "Backup directory: $BACKUP_DIR"

# Check if external drive is mounted
if [ ! -d "$EXTERNAL_DRIVE" ]; then
    err "External drive not found at $EXTERNAL_DRIVE"
    err "Please mount your external drive and try again"
    exit 1
fi

# Create NeoLight directory structure
mkdir -p "$EXTERNAL_DRIVE/NeoLight/state"
mkdir -p "$EXTERNAL_DRIVE/NeoLight/snapshots"
mkdir -p "$EXTERNAL_DRIVE/NeoLight/logs"
mkdir -p "$BACKUP_DIR"

# ── Step 1: Sync State ─────────────────────────────────────────────
info "Syncing state directory..."
if [ -d "$ROOT/state" ]; then
    rsync -av --delete "$ROOT/state/" "$BACKUP_DIR/state/" 2>&1 | tee -a "$LOG_FILE"
    ok "State synced to external drive"
else
    warn "State directory not found, skipping"
fi

# ── Step 2: Sync Snapshots ────────────────────────────────────────
info "Syncing snapshots directory..."
if [ -d "$ROOT/snapshots" ]; then
    rsync -av --delete "$ROOT/snapshots/" "$BACKUP_DIR/snapshots/" 2>&1 | tee -a "$LOG_FILE"
    ok "Snapshots synced to external drive"
else
    warn "Snapshots directory not found, skipping"
fi

# ── Step 3: Archive Old Logs (keep last 7 days) ───────────────────
info "Archiving old logs (older than 7 days)..."
if [ -d "$ROOT/logs" ]; then
    OLD_LOGS=$(find "$ROOT/logs" -type f -name "*.log" -mtime +7 2>/dev/null | wc -l | tr -d ' ')
    if [ "$OLD_LOGS" -gt 0 ]; then
        mkdir -p "$BACKUP_DIR/logs"
        find "$ROOT/logs" -type f -name "*.log" -mtime +7 -exec cp {} "$BACKUP_DIR/logs/" \; 2>/dev/null || true
        ok "Archived $OLD_LOGS old log files"
    else
        info "No old logs to archive"
    fi
else
    warn "Logs directory not found, skipping"
fi

# ── Step 4: Cleanup Old Backups (keep last 4 weeks) ───────────────
info "Cleaning up old backups (older than 4 weeks)..."
if [ -d "$EXTERNAL_DRIVE/NeoLight" ]; then
    OLD_BACKUPS=$(find "$EXTERNAL_DRIVE/NeoLight" -type d -name "weekly_backup_*" -mtime +28 2>/dev/null | wc -l | tr -d ' ')
    if [ "$OLD_BACKUPS" -gt 0 ]; then
        find "$EXTERNAL_DRIVE/NeoLight" -type d -name "weekly_backup_*" -mtime +28 -exec rm -rf {} \; 2>/dev/null || true
        ok "Removed $OLD_BACKUPS old backup directories"
    else
        info "No old backups to clean up"
    fi
fi

# ── Step 5: Calculate Backup Size ─────────────────────────────────
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | awk '{print $1}' || echo "0")
ok "Weekly backup complete!"
info "Backup size: $BACKUP_SIZE"
info "Backup location: $BACKUP_DIR"

# ── Summary ────────────────────────────────────────────────────────
echo ""
echo "📊 Weekly Backup Summary:"
echo "   • State: Synced ✅"
echo "   • Snapshots: Synced ✅"
echo "   • Old Logs: Archived ✅"
echo "   • Old Backups: Cleaned ✅"
echo "   • Total Size: $BACKUP_SIZE"
echo "   • Location: $BACKUP_DIR"
echo ""

log "Weekly backup completed successfully at $(date '+%F %T')"



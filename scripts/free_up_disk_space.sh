#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ 💾 NeoLight Disk Space Cleanup Script                            ║
# ║ Archives old logs and cleans cache to free up space              ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

info() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err() { echo -e "${RED}❌ $1${NC}"; }
step() { echo -e "${CYAN}📋 $1${NC}"; }

echo "═══════════════════════════════════════════════════════════════"
echo "💾 NeoLight Disk Space Cleanup"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check current usage
step "Current disk usage:"
TOTAL=$(du -sh "$ROOT" 2>/dev/null | awk '{print $1}')
LOGS_SIZE=$(du -sh "$ROOT/logs" 2>/dev/null | awk '{print $1}' || echo "0")
echo "   Total: $TOTAL"
echo "   Logs: $LOGS_SIZE"
echo ""

# External drive (optional)
EXTERNAL_DRIVE="${1:-}"
if [ -z "$EXTERNAL_DRIVE" ]; then
    warn "No external drive specified. Will compress logs in place."
    warn "Usage: $0 [external_drive_path]"
    echo ""
    read -p "Enter external drive path (or press Enter to skip): " EXTERNAL_DRIVE
fi

ARCHIVE_DIR=""
if [ -n "$EXTERNAL_DRIVE" ] && [ -d "$EXTERNAL_DRIVE" ]; then
    ARCHIVE_DIR="$EXTERNAL_DRIVE/neolight_archive_$(date +%Y%m%d)"
    mkdir -p "$ARCHIVE_DIR/logs"
    info "Archive directory: $ARCHIVE_DIR"
else
    warn "No external drive found. Will compress logs in place."
fi

echo ""

# Step 1: Clean Python cache
step "Step 1: Cleaning Python cache..."
PYCACHE_COUNT=$(find "$ROOT" -type d -name "__pycache__" 2>/dev/null | wc -l | xargs)
if [ "$PYCACHE_COUNT" -gt 0 ]; then
    PYCACHE_SIZE=$(find "$ROOT" -type d -name "__pycache__" -exec du -sk {} \; 2>/dev/null | awk '{sum+=$1} END {print sum/1024}')
    find "$ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$ROOT" -name "*.pyc" -delete 2>/dev/null || true
    info "Cleaned $PYCACHE_COUNT Python cache directories (~${PYCACHE_SIZE}MB)"
else
    info "No Python cache found"
fi
echo ""

# Step 2: Archive old logs (>30 days)
step "Step 2: Archiving logs older than 30 days..."
if [ -d "$ROOT/logs" ]; then
    OLD_LOGS=$(find "$ROOT/logs" -name "*.log" -mtime +30 2>/dev/null | wc -l | xargs)
    if [ "$OLD_LOGS" -gt 0 ]; then
        if [ -n "$ARCHIVE_DIR" ]; then
            find "$ROOT/logs" -name "*.log" -mtime +30 -exec mv {} "$ARCHIVE_DIR/logs/" \; 2>/dev/null || true
            info "Archived $OLD_LOGS log files to external drive"
        else
            find "$ROOT/logs" -name "*.log" -mtime +30 -exec gzip {} \; 2>/dev/null || true
            info "Compressed $OLD_LOGS old log files"
        fi
    else
        info "No logs older than 30 days found"
    fi
else
    warn "Logs directory not found"
fi
echo ""

# Step 3: Compress logs 7-30 days old
step "Step 3: Compressing logs 7-30 days old..."
if [ -d "$ROOT/logs" ]; then
    MID_LOGS=$(find "$ROOT/logs" -name "*.log" -mtime +7 -mtime -30 2>/dev/null | wc -l | xargs)
    if [ "$MID_LOGS" -gt 0 ]; then
        find "$ROOT/logs" -name "*.log" -mtime +7 -mtime -30 -exec gzip {} \; 2>/dev/null || true
        info "Compressed $MID_LOGS log files (7-30 days old)"
    else
        info "No logs in 7-30 day range found"
    fi
else
    warn "Logs directory not found"
fi
echo ""

# Step 4: Clean temporary files
step "Step 4: Cleaning temporary files..."
TMP_FILES=$(find "$ROOT" -name "*.tmp" -o -name "*.bak" -o -name "*.swp" 2>/dev/null | wc -l | xargs)
if [ "$TMP_FILES" -gt 0 ]; then
    find "$ROOT" -name "*.tmp" -delete 2>/dev/null || true
    find "$ROOT" -name "*.bak" -delete 2>/dev/null || true
    find "$ROOT" -name "*.swp" -delete 2>/dev/null || true
    info "Cleaned $TMP_FILES temporary files"
else
    info "No temporary files found"
fi
echo ""

# Final usage
step "Final disk usage:"
NEW_TOTAL=$(du -sh "$ROOT" 2>/dev/null | awk '{print $1}')
NEW_LOGS_SIZE=$(du -sh "$ROOT/logs" 2>/dev/null | awk '{print $1}' || echo "0")
echo "   Total: $NEW_TOTAL (was $TOTAL)"
echo "   Logs: $NEW_LOGS_SIZE (was $LOGS_SIZE)"
echo ""

echo "═══════════════════════════════════════════════════════════════"
info "Cleanup complete!"
echo "═══════════════════════════════════════════════════════════════"


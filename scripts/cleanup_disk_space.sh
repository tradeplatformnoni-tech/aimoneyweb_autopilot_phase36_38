#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ 🧹 NeoLight Disk Cleanup Script                                   ║
# ║ Cleans up junk files and moves non-essential data to external    ║
# ╚══════════════════════════════════════════════════════════════════╝

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# External drive path (user should set this)
EXTERNAL_DRIVE="${EXTERNAL_DRIVE:-/Volumes/Cheeee}"
BACKUP_DIR="${EXTERNAL_DRIVE}/neolight_backup_$(date +%Y%m%d)"

info() { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err() { echo -e "${RED}❌ $1${NC}"; }

echo "🧹 Starting Disk Cleanup..."
echo ""

# ── Step 1: Clean Python cache ────────────────────────────────────────
echo "1️⃣  Cleaning Python cache files..."
PYCACHE_SIZE=$(find ~ -type d -name "__pycache__" -exec du -sk {} \; 2>/dev/null | awk '{sum+=$1} END {print sum/1024}')
if [ -n "$PYCACHE_SIZE" ] && [ "$PYCACHE_SIZE" != "0" ]; then
    find ~ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    info "Cleaned ~${PYCACHE_SIZE}MB of Python cache"
else
    info "No Python cache found"
fi

# ── Step 2: Clean old log files (keep last 7 days) ───────────────────
echo ""
echo "2️⃣  Cleaning old log files..."
if [ -d "$ROOT/logs" ]; then
    # Keep last 7 days, archive older ones
    OLD_LOGS=$(find "$ROOT/logs" -type f -name "*.log" -mtime +7 2>/dev/null | wc -l | tr -d ' ')
    if [ "$OLD_LOGS" -gt 0 ]; then
        OLD_LOG_SIZE=$(find "$ROOT/logs" -type f -name "*.log" -mtime +7 -exec du -sk {} \; 2>/dev/null | awk '{sum+=$1} END {print sum/1024}')
        
        # Create backup directory on external drive if it exists
        if [ -d "$EXTERNAL_DRIVE" ]; then
            mkdir -p "$BACKUP_DIR/logs"
            find "$ROOT/logs" -type f -name "*.log" -mtime +7 -exec mv {} "$BACKUP_DIR/logs/" \; 2>/dev/null || true
            info "Moved ${OLD_LOGS} old log files (~${OLD_LOG_SIZE}MB) to external drive"
        else
            # Just delete if no external drive
            find "$ROOT/logs" -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
            info "Deleted ${OLD_LOGS} old log files (~${OLD_LOG_SIZE}MB)"
        fi
    else
        info "No old log files to clean"
    fi
fi

# ── Step 3: Clean terminal history (compress) ────────────────────────
echo ""
echo "3️⃣  Compressing terminal history..."
if [ -f ~/.zsh_history ] && [ -s ~/.zsh_history ]; then
    HIST_SIZE=$(du -sh ~/.zsh_history | awk '{print $1}')
    # Keep last 10,000 lines, archive the rest
    if [ -d "$EXTERNAL_DRIVE" ]; then
        mkdir -p "$BACKUP_DIR"
        tail -10000 ~/.zsh_history > ~/.zsh_history.tmp
        mv ~/.zsh_history "$BACKUP_DIR/zsh_history_$(date +%Y%m%d).txt"
        mv ~/.zsh_history.tmp ~/.zsh_history
        info "Compressed zsh history (${HIST_SIZE}) and backed up to external drive"
    else
        tail -10000 ~/.zsh_history > ~/.zsh_history.tmp
        mv ~/.zsh_history.tmp ~/.zsh_history
        info "Compressed zsh history (${HIST_SIZE})"
    fi
fi

# ── Step 4: Clean system cache ──────────────────────────────────────
echo ""
echo "4️⃣  Cleaning system cache..."
CACHE_DIRS=(
    ~/Library/Caches
    ~/.cache
)
for cache_dir in "${CACHE_DIRS[@]}"; do
    if [ -d "$cache_dir" ]; then
        CACHE_SIZE=$(du -sh "$cache_dir" 2>/dev/null | awk '{print $1}' || echo "0")
        # Only clean if > 1GB
        CACHE_SIZE_MB=$(du -sm "$cache_dir" 2>/dev/null | awk '{print $1}' || echo "0")
        if [ "$CACHE_SIZE_MB" -gt 1024 ]; then
            find "$cache_dir" -type f -atime +30 -delete 2>/dev/null || true
            info "Cleaned old cache files from $cache_dir (was ${CACHE_SIZE})"
        fi
    fi
done

# ── Step 5: Clean Docker (if installed) ────────────────────────────
echo ""
echo "5️⃣  Cleaning Docker (if available)..."
if command -v docker >/dev/null 2>&1; then
    DOCKER_SIZE=$(docker system df 2>/dev/null | grep -E "Images|Containers" | awk '{sum+=$3} END {print sum}' || echo "0")
    if [ "$DOCKER_SIZE" != "0" ]; then
        docker system prune -f --volumes 2>/dev/null || true
        info "Cleaned Docker images and containers"
    fi
else
    info "Docker not installed, skipping"
fi

# ── Step 6: Move large non-essential files to external drive ─────────
echo ""
echo "6️⃣  Moving large files to external drive..."
if [ -d "$EXTERNAL_DRIVE" ]; then
    mkdir -p "$BACKUP_DIR"
    
    # Find large files (>100MB) in neolight that aren't essential
    LARGE_FILES=$(find "$ROOT" -type f -size +100M ! -path "*/\.git/*" ! -path "*/state/*" ! -path "*/runtime/*" 2>/dev/null | head -10)
    
    if [ -n "$LARGE_FILES" ]; then
        for file in $LARGE_FILES; do
            FILE_SIZE=$(du -sh "$file" | awk '{print $1}')
            REL_PATH=$(echo "$file" | sed "s|$ROOT/||")
            BACKUP_PATH="$BACKUP_DIR/$(dirname "$REL_PATH")"
            mkdir -p "$BACKUP_PATH"
            mv "$file" "$BACKUP_DIR/$REL_PATH" 2>/dev/null && \
                info "Moved $REL_PATH (${FILE_SIZE}) to external drive" || \
                warn "Could not move $REL_PATH"
        done
    else
        info "No large non-essential files found to move"
    fi
else
    warn "External drive not found at $EXTERNAL_DRIVE"
    warn "Set EXTERNAL_DRIVE environment variable or mount your drive"
fi

# ── Step 7: Clean old snapshots/backups ───────────────────────────────
echo ""
echo "7️⃣  Cleaning old snapshots..."
if [ -d "$ROOT/snapshots" ]; then
    OLD_SNAPSHOTS=$(find "$ROOT/snapshots" -type f -mtime +30 2>/dev/null | wc -l | tr -d ' ')
    if [ "$OLD_SNAPSHOTS" -gt 0 ]; then
        if [ -d "$EXTERNAL_DRIVE" ]; then
            mkdir -p "$BACKUP_DIR/snapshots"
            find "$ROOT/snapshots" -type f -mtime +30 -exec mv {} "$BACKUP_DIR/snapshots/" \; 2>/dev/null || true
            info "Moved ${OLD_SNAPSHOTS} old snapshots to external drive"
        else
            find "$ROOT/snapshots" -type f -mtime +30 -delete 2>/dev/null || true
            info "Deleted ${OLD_SNAPSHOTS} old snapshots"
        fi
    else
        info "No old snapshots to clean"
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "📊 Cleanup Summary:"
echo "==================="
echo ""
df -h / | tail -1
echo ""
info "Cleanup complete!"
if [ -d "$EXTERNAL_DRIVE" ]; then
    BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | awk '{print $1}' || echo "0")
    echo "   Backed up to: $BACKUP_DIR (${BACKUP_SIZE})"
fi
echo ""
echo "💡 To free more space:"
echo "   - Review large files: du -sh ~/* | sort -hr | head -20"
echo "   - Clean Downloads folder: ~/Downloads"
echo "   - Empty Trash: rm -rf ~/.Trash/*"


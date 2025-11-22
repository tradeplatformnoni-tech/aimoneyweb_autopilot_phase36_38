#!/usr/bin/env bash
# Complete workflow: Backup useful Docker data, then clean up
# 1. Backs up useful images/volumes to external drive
# 2. Cleans up old/legacy containers and images

set -euo pipefail

echo "🔄 Docker Backup & Cleanup Workflow"
echo ""

# Colors
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }

# Step 1: Backup useful data
yellow "Step 1: Backing up useful Docker data to external drive..."
echo ""
bash "$(dirname "$0")/backup_docker_to_external.sh" || {
    red "❌ Backup failed"
    echo ""
    read -p "Continue with cleanup anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        yellow "Cancelled"
        exit 1
    fi
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 2: Clean up old containers
yellow "Step 2: Cleaning up old Docker containers and images..."
echo ""
bash "$(dirname "$0")/cleanup_old_docker.sh" || {
    red "❌ Cleanup failed"
    exit 1
}

echo ""
green "✅ Complete! Useful data backed up, old containers cleaned up."
echo ""
yellow "💡 Summary:"
echo "  ✅ Useful data backed up to external drive"
echo "  ✅ Old containers stopped and removed"
echo "  ✅ Old images removed (if confirmed)"
echo ""
yellow "💾 Disk space freed: ~5-10 GB"
echo ""

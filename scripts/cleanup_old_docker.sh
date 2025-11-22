#!/usr/bin/env bash
# Clean up old Docker containers and images
# Safe cleanup script - only removes old/unused containers

set -euo pipefail

echo "🧹 Cleaning up old Docker containers and images..."
echo ""

# Colors
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    red "❌ Docker is not running"
    exit 1
fi

echo "📊 Current Docker containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAMES|trade|autofix|guardian|observer|risk|atlas|rclone"
echo ""

# Step 1: Stop old NeoLight containers
yellow "Step 1: Stopping old NeoLight containers..."
containers=("trade" "autofix" "guardian" "observer" "risk" "atlas")
stopped=0

for container in "${containers[@]}"; do
    if docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        if docker stop "$container" 2>/dev/null; then
            green "  ✅ Stopped: $container"
            ((stopped++))
        fi
    fi
done

# Handle rclone separately (might be needed)
if docker ps --format "{{.Names}}" | grep -q "neolight_rclone_sync"; then
    yellow "  ⚠️  Found rclone sync container"
    echo "  Do you want to stop rclone sync? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        if docker stop neolight_rclone_sync 2>/dev/null; then
            green "  ✅ Stopped: neolight_rclone_sync"
            ((stopped++))
        fi
    else
        yellow "  ℹ️  Keeping rclone sync container"
    fi
fi

echo ""
echo "✅ Stopped $stopped containers"
echo ""

# Step 2: Remove stopped containers
yellow "Step 2: Removing stopped containers..."
removed=0

for container in "${containers[@]}"; do
    if docker ps -a --format "{{.Names}}" | grep -q "^${container}$"; then
        if docker rm "$container" 2>/dev/null; then
            green "  ✅ Removed: $container"
            ((removed++))
        fi
    fi
done

if docker ps -a --format "{{.Names}}" | grep -q "neolight_rclone_sync"; then
    echo "  ℹ️  Skipping rclone sync container (kept as requested)"
fi

echo ""
echo "✅ Removed $removed containers"
echo ""

# Step 3: List old images (for manual review)
yellow "Step 3: Old images found:"
docker images | grep "aimoneyweb_autopilot" || echo "  None found"
echo ""

# Ask about removing images
echo "Do you want to remove old NeoLight images? (saves disk space) (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    yellow "Removing old images..."
    images=(
        "aimoneyweb_autopilot_phase36_38-trade"
        "aimoneyweb_autopilot_phase36_38-autofix"
        "aimoneyweb_autopilot_phase36_38-guardian"
        "aimoneyweb_autopilot_phase36_38-observer"
        "aimoneyweb_autopilot_phase36_38-risk"
        "aimoneyweb_autopilot_phase36_38-atlas"
    )

    removed_images=0
    for image in "${images[@]}"; do
        if docker images --format "{{.Repository}}" | grep -q "$image"; then
            if docker rmi "$image" 2>/dev/null; then
                green "  ✅ Removed: $image"
                ((removed_images++))
            fi
        fi
    done

    echo ""
    echo "✅ Removed $removed_images images"
    echo ""
fi

# Summary
echo "📊 Summary:"
echo "  ✅ Stopped containers: $stopped"
echo "  ✅ Removed containers: $removed"
echo ""
echo "💾 Disk space saved:"
docker system df
echo ""

green "✅ Cleanup complete!"
echo ""
yellow "ℹ️  Note: To uninstall Docker Desktop completely, run:"
echo "   bash scripts/uninstall_docker.sh"

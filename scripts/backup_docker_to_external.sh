#!/usr/bin/env bash
# Backup useful Docker data to external drive before cleanup
# Saves images and volumes to external drive for future use

set -euo pipefail

echo "💾 Docker Backup to External Drive"
echo ""

# Colors
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
cyan(){ printf "\033[0;36m%s\033[0m\n" "$*"; }

# Find external drive
EXTERNAL_DRIVE=""
VOLUMES_DIR="/Volumes"

# Look for external drives
yellow "🔍 Looking for external drive..."
for volume in "$VOLUMES_DIR"/*; do
    if [ -d "$volume" ] && [ "$volume" != "$VOLUMES_DIR/." ] && [ "$volume" != "$VOLUMES_DIR/.." ]; then
        vol_name=$(basename "$volume")
        # Skip system volumes
        if [[ ! "$vol_name" =~ ^(Macintosh|Preboot|Recovery|Update|VM)$ ]]; then
            if [ -w "$volume" ]; then
                EXTERNAL_DRIVE="$volume"
                green "  ✅ Found external drive: $vol_name"
                break
            fi
        fi
    fi
done

# Ask user to confirm or specify drive
if [ -z "$EXTERNAL_DRIVE" ]; then
    yellow "⚠️  Could not auto-detect external drive"
    echo ""
    echo "Available volumes:"
    ls -1 "$VOLUMES_DIR" 2>/dev/null | grep -v "^\.$" | grep -v "^\.\.$"
    echo ""
    read -p "Enter external drive path (e.g., /Volumes/MyDrive): " EXTERNAL_DRIVE
fi

if [ ! -d "$EXTERNAL_DRIVE" ] || [ ! -w "$EXTERNAL_DRIVE" ]; then
    red "❌ External drive not found or not writable: $EXTERNAL_DRIVE"
    exit 1
fi

# Create backup directory
BACKUP_DIR="$EXTERNAL_DRIVE/neolight_docker_backup"
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$BACKUP_DATE"

mkdir -p "$BACKUP_PATH"
green "✅ Backup directory created: $BACKUP_PATH"
echo ""

# Useful images to backup (not old legacy ones)
yellow "📦 Identifying useful Docker images..."
USEFUL_IMAGES=()
ALL_IMAGES=$(docker images --format "{{.Repository}}:{{.Tag}}")

for image in $ALL_IMAGES; do
    # Skip old NeoLight containers and buildkit
    if [[ "$image" =~ ^aimoneyweb_autopilot_phase36_38-(trade|autofix|guardian|observer|risk|atlas) ]] || \
       [[ "$image" == "moby/buildkit"* ]] || \
       [[ "$image" == "<none>"* ]]; then
        yellow "  ⏭️  Skipping old/legacy: $image"
        continue
    fi

    # Keep potentially useful ones
    if [[ "$image" == "rclone/rclone"* ]] || \
       [[ "$image" =~ ^[a-z]+/[a-z]+ ]] && [[ ! "$image" =~ ^aimoneyweb ]]; then
        USEFUL_IMAGES+=("$image")
        cyan "  ✅ Will backup: $image"
    fi
done

echo ""
if [ ${#USEFUL_IMAGES[@]} -eq 0 ]; then
    yellow "ℹ️  No useful images found to backup"
else
    green "📦 Found ${#USEFUL_IMAGES[@]} useful image(s) to backup"
    echo ""

    # Backup images
    yellow "💾 Backing up images..."
    for image in "${USEFUL_IMAGES[@]}"; do
        image_name=$(echo "$image" | tr '/:' '_')
        backup_file="$BACKUP_PATH/${image_name}.tar"

        cyan "  Exporting: $image -> $backup_file"
        if docker save "$image" -o "$backup_file" 2>/dev/null; then
            file_size=$(du -h "$backup_file" | cut -f1)
            green "    ✅ Saved ($file_size): $backup_file"
        else
            red "    ❌ Failed: $image"
        fi
    done
fi

# Backup Docker volumes (if any)
yellow ""
yellow "💾 Checking for Docker volumes..."
VOLUMES=$(docker volume ls --format "{{.Name}}" 2>/dev/null || echo "")

if [ -n "$VOLUMES" ]; then
    VOLUME_COUNT=$(echo "$VOLUMES" | wc -l | tr -d ' ')
    green "  Found $VOLUME_COUNT volume(s)"

    VOLUMES_DIR_BACKUP="$BACKUP_PATH/volumes"
    mkdir -p "$VOLUMES_DIR_BACKUP"

    for volume in $VOLUMES; do
        cyan "  Backing up volume: $volume"
        if docker run --rm -v "$volume":/data -v "$VOLUMES_DIR_BACKUP":/backup alpine tar czf "/backup/${volume}.tar.gz" -C /data . 2>/dev/null; then
            green "    ✅ Saved: ${volume}.tar.gz"
        else
            yellow "    ⚠️  Could not backup volume: $volume"
        fi
    done
else
    yellow "  ℹ️  No Docker volumes found"
fi

# Save Docker compose files (if any)
yellow ""
yellow "📄 Looking for Docker Compose files..."
if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; then
    cyan "  Backing up docker-compose files..."
    cp docker-compose*.yml docker-compose*.yaml "$BACKUP_PATH/" 2>/dev/null || true
    green "    ✅ Saved docker-compose files"
fi

# Save Dockerfiles
yellow ""
yellow "📄 Backing up Dockerfiles..."
if [ -f "Dockerfile" ]; then
    cp Dockerfile "$BACKUP_PATH/" 2>/dev/null || true
    green "  ✅ Saved: Dockerfile"
fi

if [ -f "cloud-run/Dockerfile" ]; then
    mkdir -p "$BACKUP_PATH/cloud-run"
    cp cloud-run/Dockerfile "$BACKUP_PATH/cloud-run/" 2>/dev/null || true
    green "  ✅ Saved: cloud-run/Dockerfile"
fi

# Create restore script
yellow ""
yellow "📝 Creating restore script..."
cat > "$BACKUP_PATH/RESTORE.sh" << 'EOF'
#!/usr/bin/env bash
# Restore Docker images from backup

set -euo pipefail

BACKUP_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "🔧 Docker Restore from: $BACKUP_DIR"
echo ""

# Restore images
for tar_file in "$BACKUP_DIR"/*.tar; do
    if [ -f "$tar_file" ]; then
        echo "Loading: $tar_file"
        docker load -i "$tar_file"
    fi
done

# Restore volumes
if [ -d "$BACKUP_DIR/volumes" ]; then
    echo ""
    echo "To restore volumes, run:"
    echo "  docker volume create <volume-name>"
    echo "  docker run --rm -v <volume-name>:/data -v $BACKUP_DIR/volumes:/backup alpine tar xzf /backup/<volume-name>.tar.gz -C /data"
fi

echo ""
echo "✅ Restore complete!"
EOF

chmod +x "$BACKUP_PATH/RESTORE.sh"
green "  ✅ Created restore script: RESTORE.sh"

# Create summary
echo ""
yellow "📋 Creating backup summary..."
cat > "$BACKUP_PATH/BACKUP_SUMMARY.txt" << EOF
Docker Backup Summary
====================
Date: $(date)
Location: $BACKUP_PATH

Images Backed Up:
$(printf '%s\n' "${USEFUL_IMAGES[@]}")

Volumes Backed Up:
${VOLUMES:-"None"}

To Restore:
  1. cd "$BACKUP_PATH"
  2. bash RESTORE.sh

Or manually:
  docker load -i <image>.tar
EOF

cat "$BACKUP_PATH/BACKUP_SUMMARY.txt"
echo ""

# Summary
echo ""
green "✅ Backup Complete!"
echo ""
echo "📊 Summary:"
echo "  Location: $BACKUP_PATH"
echo "  Images: ${#USEFUL_IMAGES[@]}"
echo "  Volumes: ${VOLUME_COUNT:-0}"
echo ""
yellow "💡 Next steps:"
echo "  1. Review backup at: $BACKUP_PATH"
echo "  2. Run cleanup: bash scripts/cleanup_old_docker.sh"
echo ""

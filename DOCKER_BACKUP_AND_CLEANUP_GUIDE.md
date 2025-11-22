# 💾 Docker Backup & Cleanup Guide

## 🎯 Overview

This guide helps you

1. **Backup useful Docker data** to external drive (before cleanup)
2. **Clean up old/legacy containers** to free disk space
3. **Keep what's useful**, remove what's not needed

---

## 📊 Current Docker Status

### Docker Images Found

- ✅ **rclone/rclone** (103MB) - **USEFUL** - Keep for sync
- ✅ **Prometheus images** (472MB + 61MB) - **POTENTIALLY USEFUL** - Keep if monitoring needed
- ❌ **Old NeoLight containers** (6 images, ~1.4GB total) - **OLD/LEGACY** - Remove
  - trade, autofix, guardian, observer, risk, atlas (from October 2025)
- ❌ **Buildkit/Kubernetes** (~1.3GB) - **SYSTEM** - Can remove if not needed

### Docker Containers Running

- ✅ **neolight_rclone_sync** - **USEFUL** - Keep if actively syncing
- ❌ **Old NeoLight containers** (6 containers, most unhealthy) - **OLD/LEGACY** - Remove
- ❌ **Buildkit** - **SYSTEM** - Can remove if not needed

---

## 🚀 Quick Start

### Option 1: Complete Workflow (Recommended)

**Single command does everything:**

```bash
cd ~/neolight
bash scripts/backup_and_cleanup_docker.sh

```

**What it does:**

1. Finds your external drive automatically
2. Backs up useful images (rclone, Prometheus, etc.)
3. Backs up Docker volumes (if any)
4. Saves Dockerfiles for future reference
5. Creates restore script
6. Cleans up old containers
7. Removes old images (with your confirmation)

### Option 2: Step by Step

**Step 1: Backup useful data first**

```bash
cd ~/neolight
bash scripts/backup_docker_to_external.sh
```

**Step 2: Clean up old containers**

```bash
bash scripts/cleanup_old_docker.sh
```

---

## 📋 What Gets Backed Up

### ✅ Useful Images (Saved)

- `rclone/rclone` - For file syncing
- `prometheus/*` - For monitoring (if needed)
- Other third-party images (not legacy NeoLight)

### ✅ Useful Data (Saved)

- Docker volumes (if any)
- Dockerfiles (for future reference)
- docker-compose files (if any)

### ❌ NOT Backed Up (Old/Legacy)

- Old NeoLight containers (trade, autofix, guardian, etc.)
- Buildkit/Kubernetes images (can reinstall if needed)

---

## 💾 Backup Location

**Default:** `/Volumes/<YourDrive>/neolight_docker_backup/<timestamp>`

**Contains:**

- `*.tar` files - Docker images
- `volumes/` - Docker volumes (if any)
- `Dockerfile` - Docker configuration
- `RESTORE.sh` - Script to restore images
- `BACKUP_SUMMARY.txt` - What was backed up

---

## 🔄 Restore from Backup

If you need to restore later:

```bash
cd /Volumes/<YourDrive>/neolight_docker_backup/<timestamp>
bash RESTORE.sh
```

Or manually:

```bash
docker load -i <image>.tar

```

---

## 🧹 Cleanup Details

### What Gets Removed

**Containers (stopped and removed):**

- `trade` - Old NeoLight container
- `autofix` - Old NeoLight container
- `guardian` - Old NeoLight container
- `observer` - Old NeoLight container
- `risk` - Old NeoLight container
- `atlas` - Old NeoLight container
- `buildx_buildkit_multiplatform0` - Build helper

**Images (optional, with confirmation):**

- All `aimoneyweb_autopilot_phase36_38-*` images
- Old buildkit images (if not needed)

### What Gets Kept

- ✅ `rclone/rclone` (if confirmed useful)
- ✅ Prometheus images (if monitoring needed)
- ✅ Dockerfiles (for future reference)

---

## 💡 Smart Detection

The backup script automatically:

- ✅ Finds your external drive
- ✅ Identifies useful vs legacy images
- ✅ Skips old NeoLight containers
- ✅ Asks about rclone sync container
- ✅ Creates restore script

---

## 📊 Expected Results

### Disk Space Freed

- **Old containers**: ~1.4 GB
- **Old images**: ~1.4 GB
- **Buildkit/Kubernetes**: ~1.3 GB (if removed)
- **Total**: ~5-10 GB freed

### Backup Size

- **Useful images**: ~500 MB - 1 GB
- **Volumes**: Depends on your data
- **Files**: < 10 MB

---

## ⚠️ Important Notes

### Before Running

1. ✅ Verify Render deployment is working (doesn't use Docker)
2. ✅ Check if rclone sync container is actively used
3. ✅ Confirm external drive is connected

### After Running

1. ✅ Verify Render still working
2. ✅ Verify cloud agents still running
3. ✅ Check backup was successful

### If You Need Docker Again

1. Reinstall: `brew install --cask docker`
2. Restore from backup: `bash RESTORE.sh`
3. Or rebuild from Dockerfiles

---

## 🎯 Recommended Workflow

### For Most Users

```bash
# 1. Complete backup & cleanup
cd ~/neolight
bash scripts/backup_and_cleanup_docker.sh

# 2. Verify system still working
curl <https://neolight-autopilot-python.onrender.com/health>

# 3. Check disk space freed
df -h

```

### If You Want More Control

```bash
# 1. Backup first (review what's being saved)
bash scripts/backup_docker_to_external.sh

# 2. Review backup
ls -lh /Volumes/<YourDrive>/neolight_docker_backup/*/

# 3. Clean up (with confirmation for each step)
bash scripts/cleanup_old_docker.sh

```

---

## ✅ Verification Checklist

### Before

- [ ] External drive connected and writable
- [ ] Render deployment verified working
- [ ] Reviewed what will be backed up

### During

- [ ] Backup completes successfully
- [ ] Useful images saved to external drive
- [ ] Cleanup removes old containers

### After

- [ ] Render deployment still working
- [ ] Backup verified on external drive
- [ ] Disk space freed confirmed

---

## 🚨 Troubleshooting

### External Drive Not Found

```bash
# List available drives
ls -1 /Volumes

# Specify drive manually when prompted

```

### Backup Failed

- Check drive has enough space
- Check drive is writable
- Check Docker is running

### Cleanup Failed

- Some containers may be in use
- Stop them first: `docker stop <container>`
- Then retry cleanup

---

## 📝 Summary

**Quick Command:**

```bash
cd ~/neolight
bash scripts/backup_and_cleanup_docker.sh

```

**Result:**

- ✅ Useful data backed up to external drive
- ✅ Old containers removed
- ✅ ~5-10 GB disk space freed
- ✅ System continues working (Render deployment)

---

## 🎉 You're Ready

Run the complete workflow script to backup useful data and clean up old containers. Everything is safe and reversible (can restore from backup if needed).

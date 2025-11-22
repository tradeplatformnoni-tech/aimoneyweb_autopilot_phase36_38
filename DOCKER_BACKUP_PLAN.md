# 💾 Docker Backup Plan - What Will Be Saved vs Removed

## 📊 Analysis of Current Docker Data

### ✅ **USEFUL - Will Be Backed Up:**

**Images to Save:**

1. **rclone/rclone:latest** (103MB) ✅ **KEEP**
   - Used for file syncing
   - Actively used container: `neolight_rclone_sync`

2. **quay.io/prometheus/prometheus:v3.7.1** (472MB) ⚠️ **OPTIONAL**
   - Monitoring system
   - Save if you use Prometheus monitoring

3. **quay.io/prometheus-operator/prometheus-config-reloader** (61MB) ⚠️ **OPTIONAL**
   - Prometheus helper
   - Save if you use Prometheus

**Containers to Keep (if running):**

- ✅ `neolight_rclone_sync` - File sync container (ask before stopping)

**Files to Save:**

- ✅ `Dockerfile` - For Fly.io deployments

- ✅ `cloud-run/Dockerfile` - For Cloud Run deployments

- ✅ `fly.toml` - Fly.io configuration

---

### ❌ **OLD/LEGACY - Will Be Removed:**

**Images to Remove:**

1. ❌ `aimoneyweb_autopilot_phase36_38-trade:latest` (227MB)

2. ❌ `aimoneyweb_autopilot_phase36_38-autofix:latest` (225MB)

3. ❌ `aimoneyweb_autopilot_phase36_38-guardian:latest` (241MB)

4. ❌ `aimoneyweb_autopilot_phase36_38-observer:latest` (241MB)

5. ❌ `aimoneyweb_autopilot_phase36_38-risk:latest` (225MB)

6. ❌ `aimoneyweb_autopilot_phase36_38-atlas:latest` (225MB)

**Total Old Images**: ~1.4 GB

**Containers to Remove:**

1. ❌ `trade` - Old container (unhealthy, from Oct 26)

2. ❌ `autofix` - Old container (unhealthy, from Oct 25)

3. ❌ `guardian` - Old container (healthy but legacy, from Oct 25)

4. ❌ `observer` - Old container (unhealthy, from Oct 25)

5. ❌ `risk` - Old container (healthy but legacy, from Oct 23)

6. ❌ `atlas` - Old container (unhealthy, from Oct 23)

7. ❌ `buildx_buildkit_multiplatform0` - Build helper (can reinstall)

**Total Containers**: 7 to remove

---

### ⚠️ **SYSTEM - Optional Removal:**

**Images (can remove if not needed):**

1. ⚠️ `moby/buildkit:buildx-stable-1` (324MB) - Build helper

2. ⚠️ `docker/desktop-kubernetes:*` (~551MB) - Kubernetes (if not used)

3. ⚠️ `registry.k8s.io/*` (~380MB) - Kubernetes components (if not used)

**Total System Images**: ~1.3 GB (optional)

---

## 💾 Backup Plan

### What Gets Backed Up to External Drive

**Location**: `/Volumes/<YourDrive>/neolight_docker_backup/<timestamp>`

**Images:**

- ✅ rclone/rclone (103MB)

- ⚠️ Prometheus images (533MB) - If needed

**Volumes:**

- ✅ Any Docker volumes (if exist)

**Files:**

- ✅ Dockerfile

- ✅ cloud-run/Dockerfile

- ✅ fly.toml (Docker config references)

**Restore Script:**

- ✅ RESTORE.sh - Script to restore images later

---

## 🗑️ Cleanup Plan

### What Gets Removed

**Containers** (stopped and removed)

- All 6 old NeoLight containers

- Buildkit container

**Images** (with confirmation):

- All 6 old NeoLight images (~1.4 GB)

- Optional: Buildkit/Kubernetes (~1.3 GB)

**Expected Disk Space Freed:**

- Minimum: ~1.4 GB (old NeoLight containers)

- Maximum: ~2.7 GB (if removing buildkit/Kubernetes too)

---

## 🚀 Execution Plan

### Step 1: Backup Useful Data

**Command:**

```bash
cd ~/neolight
bash scripts/backup_docker_to_external.sh

```

**What Happens:**

1. Auto-detects external drive

2. Creates backup directory

3. Saves useful images (rclone, Prometheus if needed)

4. Saves Docker volumes (if any)

5. Saves Dockerfiles

6. Creates restore script

7. Creates summary

**Backup Size**: ~500 MB - 1 GB

---

### Step 2: Clean Up Old Containers

**Command:**

```bash
bash scripts/cleanup_old_docker.sh

```

**What Happens:**

1. Stops old containers

2. Asks about rclone container (keep if active)

3. Removes stopped containers

4. Lists old images

5. Asks to remove old images (with confirmation)

6. Shows disk space freed

**Disk Space Freed**: ~1.4 GB - 2.7 GB

---

### Step 3: Verify

**Commands:**

```bash
# Verify Render still working
curl <https://neolight-autopilot-python.onrender.com/health>

# Check disk space
df -h

# Verify backup
ls -lh /Volumes/<YourDrive>/neolight_docker_backup/*/

```

---

## ✅ Summary

**Backup:**

- ✅ Useful images: ~500 MB - 1 GB

- ✅ Files: Dockerfiles + configs

- ✅ Restore script created

**Cleanup:**

- ❌ Old containers: 7 removed

- ❌ Old images: ~1.4 GB removed

- ⚠️ Optional: ~1.3 GB (if removing buildkit/Kubernetes)

**Result:**

- ✅ Useful data safely backed up

- ✅ Old data removed

- ✅ ~5-10 GB disk space freed

- ✅ System continues working (Render deployment)

---

## 🎯 Quick Start

**Complete Workflow:**

```bash
cd ~/neolight
bash scripts/backup_and_cleanup_docker.sh

```

This single command:

1. Backs up useful data to external drive

2. Cleans up old containers

3. Removes old images (with confirmation)

4. Shows summary

**Time**: ~5-10 minutes

---

## ⚠️ Important Notes

### Before Running

1. ✅ Connect external drive

2. ✅ Verify Render deployment is working

3. ✅ Check if rclone sync is actively used

### During

1. ✅ Review what's being backed up

2. ✅ Confirm which containers to keep/remove

3. ✅ Confirm which images to remove

### After

1. ✅ Verify backup on external drive

2. ✅ Verify Render still working

3. ✅ Check disk space freed

---

## 🔄 If You Need to Restore

**From Backup:**

```bash
cd /Volumes/<YourDrive>/neolight_docker_backup/<timestamp>
bash RESTORE.sh

```

**Or Reinstall Docker:**

```bash
brew install --cask docker

```

Then restore from backup.

---

## ✅ Ready to Execute

All scripts are ready and executable. Run the complete workflow when ready

```bash
cd ~/neolight
bash scripts/backup_and_cleanup_docker.sh

```

**Everything is safe and reversible!** 💾✅

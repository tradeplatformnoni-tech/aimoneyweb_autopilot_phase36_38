# 💰 $0 Monthly Deployment Plan - Complete Strategy

**Goal:** Deploy NeoLight to cloud with $0 monthly cost  
**Strategy:** Scale-to-zero + Google Drive + External Drive + Cloudflare + Render

---

## 🎯 Architecture Overview

```
Local System (Primary)
    ↓
Google Drive (Sync - Free)
    ↓
Google Cloud Run (Scale-to-Zero - Free Tier)
    ↓
Cloudflare (CDN - Free Tier)
    ↓
Render (Backup - Free Tier)
    ↓
External Drive (Weekly Backup - Free)
```

---

## 💰 Cost Breakdown: $0/Month

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| **Google Cloud Run** | Scale-to-zero (min-instances=0) | $0 (free tier) |
| **Google Cloud Storage** | 1GB state | $0.02 (negligible) |
| **Cloud Build** | Free tier (2 builds/day) | $0 |
| **Cloudflare** | Free tier | $0 |
| **Render** | Free tier (standby) | $0 |
| **Google Drive** | Free (15GB) | $0 |
| **External Drive** | Local backup | $0 |
| **Total** | | **~$0/month** |

---

## 📋 Components

### 1. Google Cloud Run (Scale-to-Zero)
- **Configuration:** `min-instances=0` (scales to zero when idle)
- **Cost:** $0/month (within free tier)
- **How:** Only scales up on failover or manual activation
- **Free Tier Limits:**
  - 2 million requests/month
  - 360,000 GB-seconds memory
  - 180,000 vCPU-seconds

### 2. Google Drive (Sync)
- **Purpose:** Continuous state sync
- **Cost:** $0 (15GB free)
- **How:** rclone sync every 30 minutes
- **Script:** `scripts/rclone_sync.sh`

### 3. External Drive (Weekly Backup)
- **Purpose:** Weekly backup at night
- **Cost:** $0 (local storage)
- **How:** Cron job runs weekly at night
- **Location:** `/Volumes/Cheeee/NeoLight/`
- **Script:** `scripts/cleanup_disk_space.sh` (modified for weekly)

### 4. Cloudflare (CDN)
- **Purpose:** CDN, security, DDoS protection
- **Cost:** $0 (free tier)
- **How:** Workers & Pages → Create Worker

### 5. Render (Backup)
- **Purpose:** Optional backup deployment
- **Cost:** $0 (free tier, standby)
- **How:** Deploy but keep suspended

---

## 🔄 How It Works

### Normal Operation:
1. **Local System:** Runs on your Mac (primary)
2. **Google Drive:** Syncs state every 30 minutes (rclone)
3. **Google Cloud Run:** Scaled to 0 (free, no cost)
4. **Cloudflare:** Routes traffic (free tier)
5. **Render:** Suspended (standby, free)

### Weekly Backup (Night):
1. **Cron Job:** Runs weekly at night (e.g., Sunday 2 AM)
2. **External Drive:** Syncs state/data to `/Volumes/Cheeee/NeoLight/`
3. **Archive:** Old logs, snapshots moved to external drive
4. **Cleanup:** Local disk space freed

### Failover (If Local Fails):
1. **Monitor Detects:** Local system down
2. **Cloud Run Scales Up:** Automatically (10-30s cold start)
3. **State Sync:** Pulls from Google Drive
4. **Trading Continues:** On Cloud Run
5. **Cost:** Only during failover (minimal)

---

## 🚀 Setup Steps

### Step 1: Configure Google Cloud Run (Scale-to-Zero)

**Update `cloud-run/cloudbuild.yaml`:**
```yaml
# Change this:
- '--min-instances=0'  # Scale to zero (free tier)
- '--max-instances=1'
```

**Deploy:**
```bash
cd ~/neolight
export NL_BUCKET=$(grep NL_BUCKET ~/.zshrc | tail -1 | cut -d'=' -f2 | tr -d '"')
gcloud builds submit --config cloud-run/cloudbuild.yaml --substitutions _NL_BUCKET="$NL_BUCKET"
```

### Step 2: Set Up Google Drive Sync (Already Done)
- ✅ `scripts/rclone_sync.sh` - Syncs every 30 minutes
- ✅ `scripts/rclone_sync_loop.sh` - Continuous sync
- ✅ rclone remote: `neo_remote`
- ✅ Path: `NeoLight/`

### Step 3: Set Up Weekly External Drive Backup

**Create weekly backup script:**
```bash
# Create: scripts/weekly_external_drive_backup.sh
```

**Add cron job:**
```bash
# Edit crontab
crontab -e

# Add this line (runs every Sunday at 2 AM):
0 2 * * 0 /Users/oluwaseyeakinbola/neolight/scripts/weekly_external_drive_backup.sh >> /Users/oluwaseyeakinbola/neolight/logs/weekly_backup.log 2>&1
```

### Step 4: Deploy Cloudflare Worker
- Go to: https://dash.cloudflare.com
- Workers & Pages → Create Worker
- Copy code from `cloudflare_worker_code.js`
- Deploy

### Step 5: Configure Render (Optional Backup)
- Deploy to Render (free tier)
- Keep suspended (standby)
- Only activate if needed

---

## 📝 Weekly Backup Script

**File:** `scripts/weekly_external_drive_backup.sh`

```bash
#!/bin/bash
# Weekly External Drive Backup - Runs at Night

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTERNAL_DRIVE="/Volumes/Cheeee"
BACKUP_DIR="$EXTERNAL_DRIVE/NeoLight/weekly_backup_$(date +%Y%m%d)"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Sync state
rsync -av --delete "$ROOT/state/" "$BACKUP_DIR/state/"

# Sync snapshots
rsync -av --delete "$ROOT/snapshots/" "$BACKUP_DIR/snapshots/"

# Archive old logs (keep last 7 days)
find "$ROOT/logs" -type f -name "*.log" -mtime +7 -exec cp {} "$BACKUP_DIR/logs/" \;

# Cleanup old backups (keep last 4 weeks)
find "$EXTERNAL_DRIVE/NeoLight" -type d -name "weekly_backup_*" -mtime +28 -exec rm -rf {} \;

echo "✅ Weekly backup complete: $BACKUP_DIR"
```

---

## ✅ Verification Checklist

- [ ] Google Cloud Run: `min-instances=0` (scale-to-zero)
- [ ] Google Drive sync: Running every 30 minutes
- [ ] External drive backup: Cron job scheduled (weekly, night)
- [ ] Cloudflare Worker: Deployed
- [ ] Render: Suspended (standby)
- [ ] Cost: $0/month verified

---

## 🔍 Monitoring

### Check Costs:
```bash
# Google Cloud billing
gcloud billing accounts list
gcloud billing projects describe neolight-production

# Verify scale-to-zero
gcloud run services describe neolight-failover --region us-central1 --format="value(spec.template.spec.minInstances)"
# Should return: 0
```

### Check Syncs:
```bash
# Google Drive sync logs
tail -f ~/neolight/logs/drive_sync_*.log

# Weekly backup logs
tail -f ~/neolight/logs/weekly_backup.log
```

---

## 🎯 Summary

**This plan achieves $0/month by:**
1. ✅ Google Cloud Run: Scale-to-zero (free tier)
2. ✅ Google Drive: Free (15GB)
3. ✅ Cloudflare: Free tier
4. ✅ Render: Free tier (standby)
5. ✅ External Drive: Local (free)
6. ✅ Weekly backup: Automated cron job

**Total Cost: ~$0/month** (only $0.02 for Cloud Storage)

---

**🚀 Ready to implement this $0/month plan!**



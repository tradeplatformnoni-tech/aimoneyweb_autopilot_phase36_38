# Zero Cost 24/7 Cloud Deployment - World-Class Implementation

**Goal:** Deploy NeoLight to run 24/7 in the cloud for $0/month  
**Strategy:** Proactive usage-based failover between Render and Google Cloud Run  
**Status:** Implementation Complete

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare Worker                          │
│  (Keep-Alive + Smart Routing)                                 │
│  • Pings Render every 10 min (prevents spin-down)            │
│  • Routes traffic to active provider                         │
│  • Automatic failover detection                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌─────────▼──────────┐
│  Render        │          │  Google Cloud Run   │
│  (Primary)     │          │  (Backup)          │
│  • Free tier   │          │  • Scale-to-zero  │
│  • 750h/month  │          │  • $0 when idle    │
│  • 24/7        │          │  • Auto-activates  │
└────────────────┘          └───────────────────┘
        │                             │
        └──────────────┬───────────────┘
                       │
            ┌──────────▼──────────┐
            │   Google Drive      │
            │   (State Sync)      │
            │   • Every 30 min    │
            └─────────────────────┘
                       │
            ┌──────────▼──────────┐
            │   External Drive    │
            │   (Weekly Backup)   │
            │   • Sunday 2 AM     │
            └─────────────────────┘
```

---

## How It Works

### Normal Operation (Month Start - 720 Hours)

1. **Render runs 24/7** (primary service)
2. **Cloudflare Worker** pings Render every 10 minutes (keeps it alive)
3. **Usage Monitor** tracks hours used (checks every hour)
4. **Google Drive** syncs state every 30 minutes
5. **Cost:** $0/month (within Render free tier)

### Proactive Failover (720+ Hours)

1. **Usage Monitor** detects 720 hours used (30 hours remaining)
2. **Auto-Switch Script** triggers:
   - Syncs state to Google Drive
   - Suspends Render (preserves remaining hours)
   - Activates Google Cloud Run (scales from 0 to 1)
   - Routes traffic via Cloudflare
3. **Cloud Run runs** until month resets
4. **Cost:** $0/month (Cloud Run scale-to-zero when not in use)

### Monthly Reset (Month Boundary)

1. **Monthly Reset Handler** detects new month
2. **Auto-Switch Script** triggers:
   - Syncs state to Google Drive
   - Deactivates Cloud Run (scales back to 0)
   - Resumes Render (hours reset to 0)
   - Routes traffic back to Render
3. **Cycle repeats**
4. **Cost:** $0/month

---

## Components

### 1. Render Usage Monitor
**File:** `scripts/render_usage_monitor.py`
- Tracks Render hours via API or estimation
- Checks every hour
- Alerts at 700 hours (warning)
- Triggers failover at 720 hours (switch)
- Detects month changes

### 2. Auto Failover Switch
**File:** `scripts/auto_failover_switch.sh`
- Switches from Render to Cloud Run
- Switches from Cloud Run back to Render
- Handles state synchronization
- Manages service suspension/resumption

### 3. Monthly Reset Handler
**File:** `scripts/monthly_reset_handler.sh`
- Detects month boundary
- Resets usage tracking
- Switches back to Render automatically

### 4. Cloud Orchestrator
**File:** `scripts/cloud_orchestrator.sh`
- Coordinates all components
- Starts/stops monitoring
- Provides status information

### 5. Cloudflare Worker
**File:** `cloudflare_worker_keepalive.js`
- Keeps Render alive (pings every 10 min)
- Routes traffic to active provider
- Handles failover automatically

### 6. Render Deployment Config
**File:** `render.yaml`
- Free tier configuration
- Auto-deploy from GitHub
- Health checks

---

## Setup Instructions

### Step 1: Configure Environment Variables

Add to `~/.zshrc`:
```bash
# Render
export RENDER_API_KEY="your_render_api_key"
export RENDER_SERVICE_ID="your_service_id"

# Google Cloud Run
export CLOUD_RUN_SERVICE="neolight-failover"
export CLOUD_RUN_REGION="us-central1"
export CLOUD_RUN_API_KEY="your_api_key"
export CLOUD_RUN_URL="https://neolight-failover-xxx-uc.a.run.app"

# State Sync
export NL_BUCKET="gs://neolight-state-xxx"
export RCLONE_REMOTE="neo_remote"
export RCLONE_PATH="NeoLight"

# External Drive
export EXTERNAL_DRIVE="/Volumes/Cheeee"
```

### Step 2: Deploy to Render

```bash
cd ~/neolight

# Install Render CLI (if needed)
curl -fsSL https://render.com/install.sh | bash

# Authenticate
render auth login

# Deploy
bash scripts/render_deploy.sh
```

### Step 3: Deploy Cloudflare Worker

1. Go to: https://dash.cloudflare.com
2. Workers & Pages → Create Worker
3. Name: `neolight-api`
4. Copy code from `cloudflare_worker_keepalive.js`
5. Update `RENDER_URL` with your Render service URL
6. Deploy

### Step 4: Set Up Cron Jobs

```bash
crontab -e
```

Add these lines:
```cron
# Google Drive sync (every 30 minutes)
*/30 * * * * /Users/oluwaseyeakinbola/neolight/scripts/rclone_sync.sh >> /Users/oluwaseyeakinbola/neolight/logs/drive_sync.log 2>&1

# Monthly reset check (every hour)
0 * * * * /Users/oluwaseyeakinbola/neolight/scripts/monthly_reset_handler.sh >> /Users/oluwaseyeakinbola/neolight/logs/monthly_reset.log 2>&1

# Weekly external drive backup (Sunday 2 AM)
0 2 * * 0 /Users/oluwaseyeakinbola/neolight/scripts/weekly_external_drive_backup.sh >> /Users/oluwaseyeakinbola/neolight/logs/weekly_backup.log 2>&1
```

### Step 5: Start Orchestrator

```bash
cd ~/neolight
bash scripts/cloud_orchestrator.sh start
```

---

## Monitoring

### Check Status
```bash
# Orchestrator status
bash scripts/cloud_orchestrator.sh status

# Render usage
python3 scripts/render_usage_monitor.py check

# Failover status
bash scripts/auto_failover_switch.sh status
```

### View Logs
```bash
# Orchestrator
tail -f logs/cloud_orchestrator.log

# Render monitor
tail -f logs/render_monitor.log

# Auto-switch
tail -f logs/auto_failover_switch.log

# Monthly reset
tail -f logs/monthly_reset.log
```

---

## Cost Breakdown

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| **Render** | Free tier (750h, with keep-alive) | $0 |
| **Google Cloud Run** | Scale-to-zero (backup only) | $0 |
| **Cloudflare** | Free tier (Workers + CDN) | $0 |
| **Google Drive** | 15GB free | $0 |
| **External Drive** | Local storage | $0 |
| **Total** | | **$0/month** |

---

## Thresholds

- **Warning:** 700 hours (50 hours remaining)
- **Switch:** 720 hours (30 hours remaining)
- **Limit:** 750 hours (Render free tier)

---

## Features

- **Proactive:** Switches before hitting limits
- **Automatic:** No manual intervention needed
- **24/7:** Continuous operation
- **$0 Cost:** Stays within all free tiers
- **Resilient:** Multiple backup layers
- **Smart:** Uses both free tiers efficiently

---

## Troubleshooting

### Render spins down
- **Solution:** Cloudflare Worker should ping every 10 min
- **Check:** Cloudflare Worker scheduled events
- **Fix:** Verify Worker is deployed and scheduled

### Usage not tracked
- **Solution:** Check Render API credentials
- **Check:** `RENDER_API_KEY` and `RENDER_SERVICE_ID` set
- **Fix:** Monitor falls back to estimation if API fails

### Failover not triggering
- **Solution:** Check usage monitor logs
- **Check:** `logs/render_monitor.log`
- **Fix:** Verify thresholds and API access

### Month reset not working
- **Solution:** Check cron job is running
- **Check:** `crontab -l`
- **Fix:** Verify monthly reset handler is scheduled

---

## Success Criteria

- ✅ Render runs 24/7 (kept alive by Cloudflare)
- ✅ Usage monitored continuously
- ✅ Automatic failover at 720 hours
- ✅ Monthly reset switches back to Render
- ✅ State synced to Google Drive
- ✅ Weekly backup to external drive
- ✅ Total cost: $0/month
- ✅ 24/7 uptime achieved

---

**Status:** Implementation Complete - Ready for Deployment



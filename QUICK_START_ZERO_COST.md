# Quick Start - Zero Cost 24/7 Deployment

**Time:** 30-45 minutes  
**Result:** $0/month, 24/7 operation

---

## Prerequisites

- ✅ Google Cloud account (free tier)
- ✅ Cloudflare account (free tier)
- ✅ Render account (free tier)
- ✅ Google Drive configured (rclone)
- ✅ External drive mounted (`/Volumes/Cheeee`)

---

## Step 1: Configure Environment Variables (5 min)

Add to `~/.zshrc`:

```bash
# Render
export RENDER_API_KEY="your_render_api_key_here"
export RENDER_SERVICE_ID="your_service_id_here"

# Google Cloud Run (already configured)
export CLOUD_RUN_SERVICE="neolight-failover"
export CLOUD_RUN_REGION="us-central1"
export CLOUD_RUN_API_KEY="8dd0d2b708490523a1e3770cd14300e4b0df4a183d2250fe3f7391887db35ab2"
export CLOUD_RUN_URL="https://neolight-failover-dxhazco67q-uc.a.run.app"

# State Sync
export NL_BUCKET="gs://neolight-state-1763592775"
export RCLONE_REMOTE="neo_remote"
export RCLONE_PATH="NeoLight"

# External Drive
export EXTERNAL_DRIVE="/Volumes/Cheeee"
```

Reload:
```bash
source ~/.zshrc
```

---

## Step 2: Get Render API Key (5 min)

1. Go to: https://dashboard.render.com
2. Account Settings → API Keys
3. Create new API key
4. Copy and add to `RENDER_API_KEY`

After deploying to Render, get Service ID:
1. Go to your service
2. Copy Service ID from URL or Settings
3. Add to `RENDER_SERVICE_ID`

---

## Step 3: Deploy to Render (10 min)

```bash
cd ~/neolight

# Install Render CLI (if needed)
curl -fsSL https://render.com/install.sh | bash

# Authenticate
render auth login

# Deploy
bash scripts/render_deploy.sh
```

**After deployment:**
1. Go to Render dashboard
2. Add environment variables:
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
   - `RCLONE_REMOTE=neo_remote`
   - `RCLONE_PATH=NeoLight`
   - (Copy from your `.env` file)

---

## Step 4: Deploy Cloudflare Worker (10 min)

1. Go to: https://dash.cloudflare.com
2. Workers & Pages → Create Worker
3. Name: `neolight-api`
4. Copy code from `cloudflare_worker_keepalive.js`
5. **Update these values:**
   - `RENDER_URL`: Your Render service URL (e.g., `neolight-primary.onrender.com`)
   - `CLOUD_RUN_URL`: Already set
   - `CLOUD_RUN_API_KEY`: Already set
6. Click "Save and deploy"

**Set up scheduled events (for keep-alive):**
1. Go to Worker → Settings → Triggers
2. Add Cron Trigger: `*/10 * * * *` (every 10 minutes)
3. Save

---

## Step 5: Set Up Cron Jobs (5 min)

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

---

## Step 6: Start Orchestrator (2 min)

```bash
cd ~/neolight
bash scripts/cloud_orchestrator.sh start
```

This starts:
- Render usage monitor (tracks hours)
- Automatic failover system

---

## Step 7: Verify Everything (5 min)

```bash
# Check orchestrator status
bash scripts/cloud_orchestrator.sh status

# Check Render usage
python3 scripts/render_usage_monitor.py check

# Test Render
curl https://your-render-service.onrender.com/health

# Test Cloud Run (should be scaled to 0, will have cold start)
curl -H "X-API-Key: $CLOUD_RUN_API_KEY" "$CLOUD_RUN_URL/health"

# Test Cloudflare Worker
curl https://neolight-api.your-subdomain.workers.dev/health
```

---

## How It Works

1. **Render runs 24/7** (primary)
2. **Cloudflare pings Render** every 10 min (keeps alive)
3. **Monitor tracks usage** (checks every hour)
4. **At 720 hours:** Auto-switches to Cloud Run
5. **At month start:** Auto-switches back to Render
6. **State syncs** to Google Drive every 30 min
7. **Weekly backup** to external drive

---

## Monitoring

```bash
# View orchestrator logs
tail -f logs/cloud_orchestrator.log

# View Render monitor logs
tail -f logs/render_monitor.log

# View usage status
cat run/render_usage_status.json | jq .

# View failover status
bash scripts/auto_failover_switch.sh status
```

---

## Troubleshooting

**Render spins down:**
- Check Cloudflare Worker scheduled events
- Verify Worker is pinging `/health` endpoint

**Usage not tracked:**
- Check `RENDER_API_KEY` and `RENDER_SERVICE_ID`
- Monitor falls back to estimation if API fails

**Failover not working:**
- Check `logs/render_monitor.log`
- Verify thresholds (700h warning, 720h switch)

---

## Success!

Your system is now:
- ✅ Running 24/7 in the cloud
- ✅ Costing $0/month
- ✅ Automatically managing failover
- ✅ Syncing state continuously
- ✅ Backing up weekly

**Total setup time:** 30-45 minutes  
**Ongoing cost:** $0/month  
**Uptime:** 24/7

---

**Full documentation:** `ZERO_COST_24_7_DEPLOYMENT.md`



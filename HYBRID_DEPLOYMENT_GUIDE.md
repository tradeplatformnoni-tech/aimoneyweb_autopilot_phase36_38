# 🚀 NeoLight Hybrid Failover - Complete Deployment Guide

## Overview

This hybrid solution combines:
- **Claude's Security**: API key auth, Secret Manager, circuit breaker
- **Auto's Reliability**: Multi-endpoint health checks, process streaming, retry logic
- **Production-ready**: Graceful shutdown, error handling, monitoring

## 📋 Prerequisites

### Required Tools
```bash
# macOS
brew install --cask google-cloud-sdk
brew install jq

# Verify
gcloud version
gsutil --version
jq --version
```

### Required Accounts
- Google Cloud Account with billing enabled
- Alpaca API keys (Paper/Live trading)
- Telegram Bot (optional, for alerts)

---

## 🔧 Part 1: Google Cloud Setup

### Step 1.1: Authenticate and Configure
```bash
# Login
gcloud auth login

# Set account
gcloud config set account tradeplatformnoni@gmail.com

# Create project (if needed)
gcloud projects create neolight-hybrid --name="NeoLight Hybrid"

# Set active project
gcloud config set project neolight-hybrid

# Set region (Chicago = us-central1)
gcloud config set run/region us-central1

# Verify
gcloud config list
```

### Step 1.2: Enable Required Services
```bash
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    storage.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com
```

### Step 1.3: Create State Bucket
```bash
# Generate unique bucket name
export NL_BUCKET="gs://neolight-state-$(date +%s)"

# Create bucket in same region
gsutil mb -l us-central1 -b on "$NL_BUCKET"

# Verify
gsutil ls "$NL_BUCKET"

# Persist environment variable
echo "export NL_BUCKET=$NL_BUCKET" >> ~/.zshrc
source ~/.zshrc
```

### Step 1.4: Generate API Key for Security
```bash
# Generate secure random key
export CLOUD_RUN_API_KEY=$(openssl rand -hex 32)

# Display (save this securely!)
echo "Your API Key: $CLOUD_RUN_API_KEY"

# Persist
echo "export CLOUD_RUN_API_KEY=$CLOUD_RUN_API_KEY" >> ~/.zshrc
source ~/.zshrc
```

### Step 1.5: Store API Key in Secret Manager
```bash
# Create secret
echo -n "$CLOUD_RUN_API_KEY" | \
  gcloud secrets create neolight-api-key \
    --replication-policy="automatic" \
    --data-file=-

# Verify
gcloud secrets describe neolight-api-key

# Grant access to Cloud Run
PROJECT_NUMBER=$(gcloud projects describe neolight-hybrid --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding neolight-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 🚀 Part 2: Deploy to Cloud Run

### Step 2.1: Initial Deployment
```bash
cd ~/neolight

# Build and deploy (this takes 5-10 minutes)
gcloud builds submit \
  --config cloud-run/cloudbuild.yaml \
  --substitutions _NL_BUCKET="$NL_BUCKET"

# Monitor build progress
gcloud builds list --limit=1
```

### Step 2.2: Get Service URL
```bash
# Get URL
export CLOUD_RUN_SERVICE_URL=$(gcloud run services describe neolight-failover \
  --region us-central1 \
  --format 'value(status.url)')

# Display
echo "Cloud Run URL: $CLOUD_RUN_SERVICE_URL"

# Persist
echo "export CLOUD_RUN_SERVICE_URL=$CLOUD_RUN_SERVICE_URL" >> ~/.zshrc
source ~/.zshrc
```

### Step 2.3: Test Cloud Run Health
```bash
# Test health endpoint (should return JSON)
curl -s "$CLOUD_RUN_SERVICE_URL/health" | jq
```

Expected response:
```json
{
  "service": "NeoLight Cloud Supervisor",
  "status": "healthy",
  "smarttrader_status": "not_started",
  "trading_mode": "PAPER_TRADING_MODE",
  "uptime_seconds": 123.45,
  "last_activation": null,
  "metrics": {...},
  "state_info": {...}
}
```

---

## 🎮 Part 3: Local Setup and Testing

### Step 3.1: Initial State Sync
```bash
# Sync your current local state to GCS
cd ~/neolight
./scripts/sync_state_to_cloud.sh
```

### Step 3.2: Start Local SmartTrader
```bash
# Terminal 1: Start SmartTrader locally
cd ~/neolight
python3 trader/smart_trader.py
```

### Step 3.3: Start Failover Monitor
```bash
# Terminal 2: Start monitor
cd ~/neolight
./scripts/hybrid_failover_monitor.sh
```

Expected output:
```
🛰️ Hybrid monitor started (v2.1-hybrid)
   Local health: http://localhost:8100/health (fallback: http://localhost:5050/healthz)
   Cloud failover: https://neolight-failover-xxxxx-uc.a.run.app
   State bucket: gs://neolight-state-1234567890
   Check interval: 15s
   Circuit breaker threshold: 3
   API key authentication: ✅ Enabled
```

---

## 🧪 Part 4: Failover Testing

### Test 1: Network Failure Simulation
```bash
# Turn off Wi-Fi or disconnect ethernet

# Within 15-45 seconds, monitor should detect failure and trigger failover:
# ⚠️  WARNING: Local system unhealthy
# ☁️  Syncing state to gs://...
# ✅ SUCCESS: State synced
# 🌐 Triggering Cloud Run activation...
# ✅ SUCCESS: Cloud Run activated
```

### Test 2: Verify Cloud Run Activation
```bash
# Check Cloud Run status
curl -s "$CLOUD_RUN_SERVICE_URL/health" | jq .smarttrader_status

# Should show "running"
```

### Test 3: Return to Local
```bash
# Turn Wi-Fi back on

# Monitor should detect local is healthy again:
# ✅ SUCCESS: Local system healthy
```

### Test 4: Manual Cloud Deactivation
```bash
# Stop cloud SmartTrader
curl -X POST "$CLOUD_RUN_SERVICE_URL/deactivate" \
  -H "X-API-Key: $CLOUD_RUN_API_KEY"

# Response:
# {"status":"deactivated","timestamp":"2025-11-05T12:34:56.789Z"}
```

---

## 📊 Part 5: Monitoring and Maintenance

### View Cloud Run Logs
```bash
# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=neolight-failover" \
  --format=json

# View last 100 lines
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=neolight-failover" \
  --limit=100 \
  --format="table(timestamp,textPayload)"
```

### View Local Monitor Logs
```bash
tail -f ~/neolight/logs/hybrid_failover_monitor.log
```

### Check Metrics
```bash
# Cloud Run metrics (requires API key)
curl -s "$CLOUD_RUN_SERVICE_URL/metrics" \
  -H "X-API-Key: $CLOUD_RUN_API_KEY" | jq

# Local health
curl -s http://localhost:8100/health | jq
```

### Manual State Sync (Anytime)
```bash
cd ~/neolight
./scripts/sync_state_to_cloud.sh
```

---

## 🔄 Part 6: Updates and Redeployment

### Update Code
```bash
cd ~/neolight

# Edit your code
# ...

# Redeploy to Cloud Run
gcloud builds submit \
  --config cloud-run/cloudbuild.yaml \
  --substitutions _NL_BUCKET="$NL_BUCKET"
```

Zero-downtime deployment: Cloud Run automatically does rolling updates with `--min-instances=1`.

---

## 📱 Part 7: Telegram Alerts (Optional)

### Setup Telegram Bot
1. Create bot: Message @BotFather → `/newbot`
2. Get token: Save the API token
3. Get chat ID: Message @userinfobot

### Configure Monitor
```bash
# Add to ~/.zshrc
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="987654321"

# Reload
source ~/.zshrc

# Restart monitor to pick up new config
```

---

## 🛡️ Part 8: Security Hardening Checklist

- ✅ API key authentication enabled (`REQUIRE_AUTH=true`)
- ✅ Secrets in Secret Manager (not in code)
- ✅ Non-root container user (`neolight:1000`)
- ✅ State validation before activation
- ✅ Graceful shutdown handling
- ✅ Circuit breaker prevents spam
- ✅ Alert throttling (max 1 per 5 min)

---

## 💰 Part 9: Cost Optimization

### Current Setup Costs
| Component | Config | Monthly Cost (USD) |
|-----------|--------|-------------------|
| Cloud Run | Always on (1 min instance) | ~$7-10 |
| Cloud Storage | 1 GB state | ~$0.02 |
| Cloud Build | 1 build/week | Free tier |
| **Total** | | **~$7-12/month** |

### Cost Reduction Options
- Scale to zero (not recommended for failover - cold starts take 10-30s)
- Two-account rotation (deploy to second Google account)
- Manual activation (don't run monitor continuously)

---

## 🔥 Part 10: Troubleshooting

### Issue: Monitor says "Local unhealthy" but it's running
**Check**: Health endpoint
```bash
curl http://localhost:8100/health
curl http://localhost:5050/healthz
```
**Fix**: Ensure your dashboard has a `/health` or `/healthz` endpoint.

### Issue: Cloud Run activation fails
**Check logs**:
```bash
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```
**Common causes**:
- State sync failed → Check gsutil permissions
- API key mismatch → Verify `CLOUD_RUN_API_KEY`
- SmartTrader won't start → Check dependencies in `requirements.txt`

### Issue: State sync very slow
**Check bucket location**:
```bash
gsutil ls -L -b "$NL_BUCKET" | grep Location
```
Should be `us-central1` (same as Cloud Run).

### Issue: Circuit breaker stuck open
**Reset monitor**:
```bash
# Stop monitor (Ctrl+C)
# Restart monitor
./scripts/hybrid_failover_monitor.sh
```

---

## 🚨 Emergency Procedures

### Full System Failure
```bash
# 1. Activate cloud manually
curl -X POST "$CLOUD_RUN_SERVICE_URL/activate" \
  -H "X-API-Key: $CLOUD_RUN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"bucket\": \"$NL_BUCKET\", \"force\": true}"

# 2. Check status
curl "$CLOUD_RUN_SERVICE_URL/health" | jq

# 3. View logs
gcloud logging tail "resource.type=cloud_run_revision" --limit=100
```

### Rollback Cloud Run Deployment
```bash
# List revisions
gcloud run revisions list --service=neolight-failover --region=us-central1

# Rollback to previous
gcloud run services update-traffic neolight-failover \
  --to-revisions=neolight-failover-00001-abc=100 \
  --region=us-central1
```

### Restore from Backup
```bash
# List backups
gsutil ls "$NL_BUCKET/state"

# Download backup
gsutil -m rsync -r "$NL_BUCKET/state" ~/neolight/state_restore

# Apply backup
cp -r ~/neolight/state_restore/* ~/neolight/state/
```

---

## ✅ Production Readiness Checklist

### Pre-Launch
- [ ] All secrets in Secret Manager
- [ ] API keys rotated from defaults
- [ ] Health checks returning correctly
- [ ] State validated and backed up
- [ ] Failover tested successfully
- [ ] Logs readable and actionable
- [ ] Telegram alerts working (if enabled)
- [ ] External disk backup configured

### Post-Launch Monitoring
- [ ] Check logs daily for first week
- [ ] Test failover weekly
- [ ] Review Cloud Run costs monthly
- [ ] Update dependencies quarterly
- [ ] Rotate API keys annually

---

## 🎯 Key Features Summary

### Claude's Security
- ✅ API key authentication on `/activate`, `/deactivate`, `/metrics`
- ✅ Secret Manager integration
- ✅ Circuit breaker pattern (prevents activation spam)
- ✅ Alert throttling (max 1 per 5 minutes)

### Auto's Reliability
- ✅ Multi-endpoint health checks (`/health` → `/healthz` → process check)
- ✅ Process output streaming (real-time SmartTrader logs)
- ✅ Improved retry logic with exponential backoff
- ✅ State conflict prevention (lockfiles)
- ✅ Better error handling and recovery

### Both Combined
- ✅ Graceful shutdown handling
- ✅ Comprehensive logging
- ✅ Production-ready error handling
- ✅ Monitoring and metrics

---

**🎉 Your hybrid failover system is ready!**


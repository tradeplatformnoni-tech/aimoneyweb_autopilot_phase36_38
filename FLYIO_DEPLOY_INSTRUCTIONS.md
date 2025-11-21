# 🚀 Fly.io Deployment - Step-by-Step Instructions

## Prerequisites

1. **Install Fly.io CLI** (if not installed):
   ```bash
   curl -L https://fly.io/install.sh | sh
   export PATH="$HOME/.fly/bin:$PATH"
   ```

2. **Authenticate**:
   ```bash
   flyctl auth login
   ```

---

## Deployment Steps

### Step 1: Sync State to Cloud (Optional on First Deploy)

**Note:** Skip this step on first deployment (app doesn't exist yet). Do this after deployment.

```bash
cd ~/neolight
bash scripts/flyio_sync_state.sh to
```

---

### Step 2: Deploy Everything

Run the complete deployment script:

```bash
cd ~/neolight
bash scripts/flyio_deploy_complete.sh
```

Or deploy manually:

```bash
# Create app (if it doesn't exist)
flyctl apps create neolight-cloud

# Create volumes
flyctl volumes create neolight_state --region iad --size 10 --app neolight-cloud
flyctl volumes create neolight_runtime --region iad --size 5 --app neolight-cloud
flyctl volumes create neolight_logs --region iad --size 5 --app neolight-cloud

# Deploy
flyctl deploy --app neolight-cloud --config fly.toml
```

---

### Step 3: Set Secrets

**Option A: From .env file (if you have one):**
```bash
cd ~/neolight
flyctl secrets import --app neolight-cloud < .env
```

**Option B: Interactive script:**
```bash
cd ~/neolight
bash scripts/flyio_set_secrets.sh
```

**Option C: Set individually:**
```bash
flyctl secrets set ALPACA_API_KEY=your_key --app neolight-cloud
flyctl secrets set ALPACA_SECRET_KEY=your_secret --app neolight-cloud
```

---

## Verify Deployment

### Check Status
```bash
flyctl status --app neolight-cloud
```

### View Logs
```bash
flyctl logs --app neolight-cloud --follow
```

### Access Dashboard
```bash
open https://neolight-cloud.fly.dev
```

### SSH into Instance
```bash
flyctl ssh console --app neolight-cloud
```

Once inside:
```bash
# Check processes
ps aux | grep python

# View logs
tail -f /app/logs/guardian_flyio.log
tail -f /app/logs/smart_trader.log

# Check state
ls -la /app/state/
```

---

## Required Secrets

Make sure these are set:

### Required:
- `ALPACA_API_KEY` - Alpaca API key for paper trading
- `ALPACA_SECRET_KEY` - Alpaca secret key for paper trading

### Optional (but recommended):
- `SPORTRADAR_API_KEY` - For sports analytics
- `AUTODS_API_KEY` - For dropshipping
- `AUTODS_TOKEN` - For dropshipping
- `REDDIT_CLIENT_ID` / `REDDIT_SECRET` - For market intelligence
- `NEWS_API_KEY` - For news sentiment
- `FRED_API_KEY` - For economic data
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` - For alerts

---

## After Deployment

### Sync State (if you skipped Step 1)
```bash
cd ~/neolight
bash scripts/flyio_sync_state.sh to
```

### Monitor Services
```bash
# View all logs
flyctl logs --app neolight-cloud --follow

# Check specific service
flyctl logs --app neolight-cloud | grep guardian
flyctl logs --app neolight-cloud | grep smart_trader
```

### Restart if Needed
```bash
flyctl restart --app neolight-cloud
```

---

## When You Return (Bring Everything Back)

### Step 1: Sync State from Cloud
```bash
cd ~/neolight
bash scripts/flyio_sync_state.sh from
```

### Step 2: Stop Fly.io (Save Costs)
```bash
flyctl scale count 0 --app neolight-cloud
```

### Step 3: Start Local System
```bash
cd ~/neolight
bash neo_light_fix.sh
```

---

## Troubleshooting

### App Won't Start
```bash
# Check logs
flyctl logs --app neolight-cloud

# Check status
flyctl status --app neolight-cloud

# SSH and debug
flyctl ssh console --app neolight-cloud
```

### Services Not Running
```bash
# SSH into instance
flyctl ssh console --app neolight-cloud

# Check processes
ps aux | grep python

# Check logs
tail -f /app/logs/*.log

# Manually start guardian
cd /app && bash flyio_guardian.sh
```

### Out of Memory
```bash
# Increase memory
flyctl scale memory 4096 --app neolight-cloud
```

### Secrets Not Set
```bash
# List all secrets
flyctl secrets list --app neolight-cloud

# Set missing secrets
flyctl secrets set KEY=value --app neolight-cloud
```

---

## Quick Reference

### Deploy
```bash
bash scripts/flyio_deploy_complete.sh
```

### View Logs
```bash
flyctl logs --app neolight-cloud --follow
```

### Check Status
```bash
flyctl status --app neolight-cloud
```

### SSH Access
```bash
flyctl ssh console --app neolight-cloud
```

### Stop (Save Costs)
```bash
flyctl scale count 0 --app neolight-cloud
```

### Start
```bash
flyctl scale count 1 --app neolight-cloud
```

---

## Cost Management

### Estimated Costs
- **Basic (2 CPU, 2GB RAM)**: ~$30-40/month
- **Storage (20GB volumes)**: ~$3/month
- **Total**: ~$33-43/month for 24/7 operation

### Save Costs
```bash
# Stop when not needed (free)
flyctl scale count 0 --app neolight-cloud

# Start when needed
flyctl scale count 1 --app neolight-cloud
```

---

**Ready to deploy? Follow the steps above!** 🚀



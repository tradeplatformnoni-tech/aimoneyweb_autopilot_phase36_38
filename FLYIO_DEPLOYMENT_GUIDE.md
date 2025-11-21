# 🚀 NeoLight Fly.io Full Deployment Guide

## Overview

This guide will help you deploy your entire NeoLight system to Fly.io cloud for 24/7 automatic operation. Once deployed, your system will run continuously in the cloud without needing your local machine.

---

## Prerequisites

1. **Fly.io Account**: Sign up at https://fly.io
2. **Fly.io CLI**: Install with `curl -L https://fly.io/install.sh | sh`
3. **Authentication**: Run `flyctl auth login`

---

## Step 1: Prepare Environment Variables

### Create Secrets File

Create a file `.env.flyio` with all your API keys and secrets:

```bash
# Trading
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret

# Revenue Agents
SPORTRADAR_API_KEY=your_sportradar_key
AUTODS_API_KEY=your_autods_key
AUTODS_TOKEN=your_autods_token
EBAY_USERNAME=seakin67

# Market Intelligence (Optional)
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_SECRET=your_reddit_secret
NEWS_API_KEY=your_newsapi_key
FRED_API_KEY=your_fred_key
TWITTER_BEARER_TOKEN=your_twitter_token

# Telegram Alerts (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id

# Cloud Sync (Optional)
RCLONE_REMOTE=neo_remote
```

### Set Secrets in Fly.io

```bash
# Set all secrets at once
flyctl secrets import --app neolight-cloud < .env.flyio

# Or set individually
flyctl secrets set ALPACA_API_KEY=xxx --app neolight-cloud
flyctl secrets set ALPACA_SECRET_KEY=xxx --app neolight-cloud
# ... etc
```

---

## Step 2: Sync Local State to Fly.io (Before Deployment)

```bash
# Sync your current state/runtime to Fly.io
bash scripts/flyio_sync_state.sh to
```

This will upload:
- `state/` directory (all agent state, P&L history, etc.)
- `runtime/` directory (strategy weights, brain state, etc.)

---

## Step 3: Deploy to Fly.io

```bash
# Run the full deployment script
bash scripts/flyio_deploy_full.sh
```

This will:
1. Create the Fly.io app (`neolight-cloud`)
2. Create persistent volumes for state/runtime/logs
3. Build and deploy the Docker container
4. Set all environment variables from `.env.flyio`
5. Start all services automatically

---

## Step 4: Verify Deployment

### Check Status

```bash
flyctl status --app neolight-cloud
```

### View Logs

```bash
# All logs
flyctl logs --app neolight-cloud

# Specific service
flyctl logs --app neolight-cloud | grep guardian
```

### Access Dashboard

```bash
# Get the app URL
flyctl info --app neolight-cloud

# Or visit directly
open https://neolight-cloud.fly.dev
```

### SSH into Instance

```bash
flyctl ssh console --app neolight-cloud
```

Once inside:
```bash
# Check running processes
ps aux | grep python

# View logs
tail -f /app/logs/guardian_flyio.log
tail -f /app/logs/smart_trader.log

# Check state
ls -la /app/state/
cat /app/state/brain.json
```

---

## Step 5: Sync State Back to Local (When Returning)

When you get back to stable WiFi and want to bring everything back locally:

```bash
# Sync state FROM Fly.io to local
bash scripts/flyio_sync_state.sh from

# Stop Fly.io instance (to save costs)
flyctl scale count app=0 --app neolight-cloud

# Restart local system
bash neo_light_fix.sh
```

---

## Monitoring & Maintenance

### View Real-Time Logs

```bash
flyctl logs --app neolight-cloud --follow
```

### Restart Services

```bash
# Restart the entire app
flyctl restart --app neolight-cloud

# Or SSH in and restart individual services
flyctl ssh console --app neolight-cloud
# Then: pkill -f guardian; bash /app/neo_light_fix.sh &
```

### Scale Resources

```bash
# Increase memory
flyctl scale memory 4096 --app neolight-cloud

# Increase CPUs
flyctl scale count 2 --app neolight-cloud

# Scale to 0 (stop, save costs)
flyctl scale count 0 --app neolight-cloud
```

### Update Secrets

```bash
# Update a single secret
flyctl secrets set ALPACA_API_KEY=new_key --app neolight-cloud

# Update all secrets from file
flyctl secrets import --app neolight-cloud < .env.flyio
```

---

## Cost Management

### Estimated Costs

- **Basic (1 CPU, 2GB RAM)**: ~$15-20/month
- **Standard (2 CPU, 4GB RAM)**: ~$30-40/month
- **Storage (volumes)**: ~$0.15/GB/month
- **Data Transfer**: First 100GB free, then $0.02/GB

### Cost Optimization

1. **Scale down when not needed**: `flyctl scale count 0 --app neolight-cloud`
2. **Use smaller instance**: Adjust CPU/memory in `fly.toml`
3. **Monitor usage**: `flyctl dashboard` → View usage charts

---

## Troubleshooting

### App Won't Start

```bash
# Check logs
flyctl logs --app neolight-cloud

# Check status
flyctl status --app neolight-cloud

# SSH in and debug
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
cd /app && bash neo_light_fix.sh
```

### State Not Persisting

```bash
# Check volumes
flyctl volumes list --app neolight-cloud

# Verify mounts
flyctl ssh console --app neolight-cloud
ls -la /app/state/
ls -la /app/runtime/
```

### Out of Memory

```bash
# Increase memory
flyctl scale memory 4096 --app neolight-cloud

# Or reduce services (edit fly.toml)
```

---

## Quick Reference

### Deploy

```bash
bash scripts/flyio_deploy_full.sh
```

### Sync State To Cloud

```bash
bash scripts/flyio_sync_state.sh to
```

### Sync State From Cloud

```bash
bash scripts/flyio_sync_state.sh from
```

### View Logs

```bash
flyctl logs --app neolight-cloud --follow
```

### Stop (Save Costs)

```bash
flyctl scale count 0 --app neolight-cloud
```

### Start

```bash
flyctl scale count 1 --app neolight-cloud
```

### SSH Access

```bash
flyctl ssh console --app neolight-cloud
```

---

## Security Notes

1. **Never commit `.env.flyio` to git** - Add to `.gitignore`
2. **Use Fly.io secrets** - Don't hardcode API keys
3. **Rotate keys regularly** - Update secrets periodically
4. **Monitor access** - Check `flyctl dashboard` for activity

---

## Next Steps

1. ✅ Deploy to Fly.io: `bash scripts/flyio_deploy_full.sh`
2. ✅ Verify services: `flyctl status --app neolight-cloud`
3. ✅ Monitor logs: `flyctl logs --app neolight-cloud --follow`
4. ✅ Access dashboard: https://neolight-cloud.fly.dev
5. ✅ When returning: Sync state back and scale down

---

**Last Updated**: January 2025  
**Status**: Ready for Deployment



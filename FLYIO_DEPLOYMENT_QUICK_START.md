# 🚀 NeoLight Fly.io Quick Start Guide

## Deploy Everything to Fly.io Cloud (3 Commands)

### Step 1: Sync Your State to Cloud

```bash
# Upload your current state/runtime to Fly.io
bash scripts/flyio_sync_state.sh to
```

### Step 2: Deploy

```bash
# One-command deployment
bash FLYIO_QUICK_DEPLOY.sh
```

Or manually:
```bash
bash scripts/flyio_deploy_full.sh
```

### Step 3: Set Secrets

```bash
# Interactive script to set all API keys
bash scripts/flyio_set_secrets.sh
```

Or set from .env file:
```bash
flyctl secrets import --app neolight-cloud < .env
```

---

## That's It! Your System is Now Running in the Cloud

### Access Your System

- **Dashboard**: https://neolight-cloud.fly.dev
- **Status API**: https://neolight-cloud.fly.dev:8100/status
- **Logs**: `flyctl logs --app neolight-cloud --follow`

### When You Return (Bring Everything Back)

```bash
# Step 1: Sync state FROM cloud to local
bash scripts/flyio_sync_state.sh from

# Step 2: Stop Fly.io (to save costs)
flyctl scale count 0 --app neolight-cloud

# Step 3: Start local system
bash neo_light_fix.sh
```

---

## Quick Reference

### View Logs
```bash
flyctl logs --app neolight-cloud --follow
```

### Check Status
```bash
flyctl status --app neolight-cloud
```

### SSH into Instance
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

### Restart
```bash
flyctl restart --app neolight-cloud
```

---

## Required Secrets

Make sure to set these before deployment:

```bash
# Required for trading
flyctl secrets set ALPACA_API_KEY=xxx --app neolight-cloud
flyctl secrets set ALPACA_SECRET_KEY=xxx --app neolight-cloud

# Optional but recommended
flyctl secrets set SPORTRADAR_API_KEY=xxx --app neolight-cloud
flyctl secrets set AUTODS_API_KEY=xxx --app neolight-cloud
```

See `FLYIO_DEPLOYMENT_GUIDE.md` for complete list.

---

## Troubleshooting

### App Won't Start
```bash
flyctl logs --app neolight-cloud
flyctl ssh console --app neolight-cloud
```

### Services Not Running
```bash
flyctl ssh console --app neolight-cloud
ps aux | grep python
tail -f /app/logs/guardian_flyio.log
```

### Out of Memory
```bash
flyctl scale memory 4096 --app neolight-cloud
```

---

**Ready to deploy? Run: `bash FLYIO_QUICK_DEPLOY.sh`**



# 🚀 Deploy NeoLight to Fly.io - Ready to Execute

## Quick Deployment (All-in-One)

I've created an improved deployment script that handles all 3 steps automatically:

```bash
bash scripts/flyio_deploy_complete.sh
```

This script will:
1. ✅ Check prerequisites (flyctl, authentication)
2. ✅ Create Fly.io app if it doesn't exist
3. ✅ Create persistent volumes
4. ✅ Deploy the application
5. ✅ Set secrets from .env file (if it exists)

---

## Manual Steps (If Needed)

If you prefer to run steps manually:

### Step 1: Install flyctl (if not installed)
```bash
curl -L https://fly.io/install.sh | sh
export PATH="$HOME/.fly/bin:$PATH"
```

### Step 2: Authenticate
```bash
flyctl auth login
```

### Step 3: Deploy
```bash
bash scripts/flyio_deploy_complete.sh
```

### Step 4: Set Secrets (if .env doesn't exist)
```bash
bash scripts/flyio_set_secrets.sh
```

### Step 5: Sync State (after deployment)
```bash
bash scripts/flyio_sync_state.sh to
```

---

## Required Secrets

Make sure these are set (either in .env file or via secrets script):

### Required:
- `ALPACA_API_KEY` - For paper trading
- `ALPACA_SECRET_KEY` - For paper trading

### Optional:
- `SPORTRADAR_API_KEY` - Sports analytics
- `AUTODS_API_KEY` - Dropshipping
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` - Alerts

---

## After Deployment

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

### SSH Access
```bash
flyctl ssh console --app neolight-cloud
```

---

## Troubleshooting

### Deployment Fails
- Check authentication: `flyctl auth whoami`
- Check logs: `flyctl logs --app neolight-cloud`
- Verify fly.toml exists and is correct

### Services Not Starting
- SSH in: `flyctl ssh console --app neolight-cloud`
- Check logs: `tail -f /app/logs/guardian_flyio.log`
- Verify secrets are set: `flyctl secrets list --app neolight-cloud`

### Out of Memory
```bash
flyctl scale memory 4096 --app neolight-cloud
```

---

**Ready? Run: `bash scripts/flyio_deploy_complete.sh`**



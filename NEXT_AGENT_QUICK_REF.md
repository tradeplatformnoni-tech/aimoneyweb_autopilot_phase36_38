# Quick Reference for Next Agent

**Status:** Ready for final deployment steps  
**Time Remaining:** 15-20 minutes (mostly waiting for Render deployment)

---

## ✅ WHAT'S DONE

- ✅ All API credentials saved and verified (`~/.api_credentials`)
- ✅ Cloud Run deployed (scale-to-zero, $0/month backup)
- ✅ All deployment files pushed to GitHub (`render-deployment` branch)
- ✅ All automation scripts created and ready

---

## ⏳ WHAT'S NEXT

### Step 1: Create Render Service (MANUAL - 5 min)
**Why Manual:** Render API requires GitHub repo connection via dashboard first.

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect GitHub account (if not connected)
4. Select repository: `tradeplatformnoni-tech/aimoneyweb_autopilot_phase36_38`
5. Select branch: `render-deployment`
6. Render will auto-detect `render.yaml`
7. Click "Create Web Service"
8. Wait for first deployment (5-10 minutes)
9. **IMPORTANT:** Copy the service URL (e.g., `https://neolight-primary.onrender.com`)
10. **IMPORTANT:** Copy the service ID (from dashboard URL or service settings)

**After Creation:**
- Add environment variables in Render dashboard:
  - `ALPACA_API_KEY` (from `.env` or Secret Manager)
  - `ALPACA_SECRET_KEY` (from `.env` or Secret Manager)
  - `RCLONE_REMOTE` (if using cloud sync)
  - `RCLONE_PATH` (if using cloud sync)

### Step 2: Deploy Cloudflare Worker (2 min)
```bash
cd ~/neolight
source <(grep -v '^#' ~/.api_credentials | grep -v '^$' | sed 's/^/export /')
export RENDER_SERVICE_URL='<url_from_step_1>'
python3 scripts/auto_deploy_cloudflare.py
```

### Step 3: Start Orchestrator (1 min)
```bash
export RENDER_SERVICE_ID='<id_from_step_1>'
bash scripts/cloud_orchestrator.sh start
```

---

## 📁 FILES CREATED/MODIFIED

### Configuration
- `render.yaml` - Render service config
- `cloud-run/cloudbuild.yaml` - Cloud Run deployment
- `cloud-run/Dockerfile` - Container image
- `cloud-run/app.py` - Cloud Run supervisor
- `.gcloudignore` - Upload exclusions

### Scripts
- `scripts/auto_deploy_all.sh` - Master orchestrator
- `scripts/auto_deploy_render.py` - Render API deployment
- `scripts/auto_deploy_cloudflare.py` - Cloudflare Worker deployment
- `scripts/cloud_orchestrator.sh` - Cloud orchestrator
- `scripts/render_usage_monitor.py` - Usage monitoring
- `scripts/auto_failover_switch.sh` - Failover logic
- `scripts/monthly_reset_handler.sh` - Monthly reset
- `scripts/set_credentials.sh` - Credential setup

### Worker Code
- `cloudflare_worker_keepalive.js` - Cloudflare Worker

### Credentials
- `~/.api_credentials` - All API keys (Render, Cloudflare)

### Documentation
- `DEPLOYMENT_STATUS.md` - Complete status (full details)
- `NEXT_AGENT_QUICK_REF.md` - This file (quick reference)

---

## 🔑 LOAD CREDENTIALS

```bash
source <(grep -v '^#' ~/.api_credentials | grep -v '^$' | sed 's/^/export /')
```

Verify:
```bash
echo "Render: ${RENDER_API_KEY:0:10}..."
echo "Cloudflare Token: ${CLOUDFLARE_API_TOKEN:0:10}..."
echo "Account ID: $CLOUDFLARE_ACCOUNT_ID"
```

---

## ⚠️ CRITICAL NOTES

1. **Render API Limitation:** Cannot create services via API without GitHub repo connection. Must use dashboard first.
2. **GitHub Branch:** All deployment files are on `render-deployment` branch, not `main`.
3. **Cloud Run:** Already deployed and configured for scale-to-zero. No action needed.
4. **Environment Variables:** Must be set in Render dashboard after service creation.

---

## 📖 FULL DETAILS

See `DEPLOYMENT_STATUS.md` for:
- Complete architecture overview
- Troubleshooting guide
- Detailed file references
- All completed tasks breakdown

---

**Last Updated:** November 20, 2024

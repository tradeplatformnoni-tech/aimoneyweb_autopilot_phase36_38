# 🤖 Automated Deployment Guide

**Automate all manual steps using API scripts - No browser extensions needed!**

---

## Quick Start (3 Steps)

### Step 1: Get API Credentials (One-time setup)

**Render API Key:**
```bash
# 1. Go to: https://dashboard.render.com
# 2. Account Settings → API Keys
# 3. Create API Key (name: neolight-monitor)
# 4. Copy the key
export RENDER_API_KEY='your_render_api_key_here'
```

**Cloudflare API Token:**
```bash
# 1. Go to: https://dash.cloudflare.com/profile/api-tokens
# 2. Create Token → Edit Cloudflare Workers
# 3. Copy the token
export CLOUDFLARE_API_TOKEN='your_cloudflare_token_here'
```

**Cloudflare Account ID:**
```bash
# 1. Go to: https://dash.cloudflare.com
# 2. Right sidebar → Account ID
# 3. Copy the ID
export CLOUDFLARE_ACCOUNT_ID='your_account_id_here'
```

**Persist to shell:**
```bash
echo "export RENDER_API_KEY='your_key'" >> ~/.zshrc
echo "export CLOUDFLARE_API_TOKEN='your_token'" >> ~/.zshrc
echo "export CLOUDFLARE_ACCOUNT_ID='your_account_id'" >> ~/.zshrc
source ~/.zshrc
```

### Step 2: Run Automated Deployment

```bash
cd ~/neolight
bash scripts/auto_deploy_all.sh
```

**This will:**
- ✅ Deploy to Render (via API)
- ✅ Deploy Cloudflare Worker (via API)
- ✅ Start orchestrator
- ✅ Configure everything automatically

### Step 3: Verify

```bash
# Check orchestrator status
bash scripts/cloud_orchestrator.sh status

# Test Render service
curl https://neolight-primary.onrender.com/health

# Test Cloudflare Worker
curl https://neolight-api.YOUR_SUBDOMAIN.workers.dev/health
```

---

## Individual Scripts

If you prefer to run steps individually:

### Deploy Render Only

```bash
export RENDER_API_KEY='your_key'
python3 scripts/auto_deploy_render.py
```

**What it does:**
- Creates Render web service (free tier)
- Configures build/start commands
- Adds environment variables from `.env`
- Returns Service ID and URL

### Deploy Cloudflare Worker Only

```bash
export CLOUDFLARE_API_TOKEN='your_token'
export CLOUDFLARE_ACCOUNT_ID='your_account_id'
export RENDER_SERVICE_URL='neolight-primary.onrender.com'  # From Render deployment
python3 scripts/auto_deploy_cloudflare.py
```

**What it does:**
- Creates/updates Cloudflare Worker
- Updates Render URL in worker code
- Adds scheduled event (keep-alive every 10 min)
- Returns Worker URL

---

## What Gets Automated

### ✅ Fully Automated (via API)

1. **Render Service Creation**
   - Service configuration
   - Environment variables
   - Build/start commands
   - Health check setup

2. **Cloudflare Worker Deployment**
   - Worker code deployment
   - Render URL configuration
   - Scheduled event setup (cron)

3. **Orchestrator Startup**
   - Starts usage monitor
   - Starts sync loops
   - Verifies all components

### ⚠️ Still Manual (One-time)

1. **Get API Credentials** (5 minutes)
   - Render API key
   - Cloudflare API token
   - Cloudflare Account ID

2. **GitHub Repository Connection** (Optional)
   - Connect repo in Render dashboard for auto-deploy
   - Or use manual deployment

---

## Troubleshooting

### "RENDER_API_KEY not set"
```bash
# Get your API key from Render dashboard
export RENDER_API_KEY='your_key'
```

### "CLOUDFLARE_API_TOKEN not set"
```bash
# Get your token from Cloudflare dashboard
export CLOUDFLARE_API_TOKEN='your_token'
export CLOUDFLARE_ACCOUNT_ID='your_account_id'
```

### "Service already exists"
- The script will detect and use the existing service
- Or delete it in Render dashboard and re-run

### "Failed to deploy worker"
- Check Cloudflare API token has Workers permissions
- Verify Account ID is correct
- Check Cloudflare API status

### Python package missing
```bash
pip3 install requests
```

---

## Comparison: Manual vs Automated

| Step | Manual | Automated |
|------|--------|-----------|
| Get API credentials | 5 min | 5 min (one-time) |
| Deploy Render | 10-15 min | 2 min |
| Deploy Cloudflare | 5-10 min | 1 min |
| Start orchestrator | 2 min | 1 min |
| **Total** | **20-30 min** | **~10 min** |

**Benefits of automation:**
- ✅ Faster deployment
- ✅ Repeatable (can re-run anytime)
- ✅ Less error-prone
- ✅ No browser interaction needed
- ✅ Can be scripted/CI-CD

---

## Advanced: Full Automation Script

For complete automation, use the master script:

```bash
# Set all credentials
export RENDER_API_KEY='your_key'
export CLOUDFLARE_API_TOKEN='your_token'
export CLOUDFLARE_ACCOUNT_ID='your_account_id'

# Run everything
bash scripts/auto_deploy_all.sh
```

**Output:**
- Deploys Render service
- Deploys Cloudflare Worker
- Starts orchestrator
- Saves service info to `run/render_service_info.json`

---

## Next Steps After Deployment

1. **Verify Services:**
   ```bash
   bash scripts/cloud_orchestrator.sh status
   ```

2. **Test Endpoints:**
   ```bash
   # Render
   curl https://neolight-primary.onrender.com/health
   
   # Cloudflare Worker
   curl https://neolight-api.YOUR_SUBDOMAIN.workers.dev/health
   
   # Cloud Run (backup)
   curl -H "X-API-Key: $CLOUD_RUN_API_KEY" \
     "https://neolight-failover-dxhazco67q-uc.a.run.app/health"
   ```

3. **Monitor Logs:**
   ```bash
   tail -f logs/cloud_orchestrator.log
   tail -f logs/render_monitor.log
   ```

4. **Check Usage:**
   ```bash
   python3 scripts/render_usage_monitor.py check
   ```

---

## Files Created

After running automation:

- `run/render_service_info.json` - Render service details
- `logs/auto_deploy_all.log` - Deployment logs
- `logs/cloud_orchestrator.log` - Orchestrator logs
- `logs/render_monitor.log` - Usage monitor logs

---

## Support

If automation fails:

1. **Check logs:**
   ```bash
   tail -f logs/auto_deploy_all.log
   ```

2. **Run individual scripts:**
   ```bash
   python3 scripts/auto_deploy_render.py
   python3 scripts/auto_deploy_cloudflare.py
   ```

3. **Manual fallback:**
   - See `MANUAL_STEPS_GUIDE.md` for manual steps
   - Use browser dashboard if API fails

---

**Ready to deploy?** Run:
```bash
bash scripts/auto_deploy_all.sh
```

🎯 **Result:** Complete $0/month 24/7 deployment in ~10 minutes!



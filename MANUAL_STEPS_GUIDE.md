# Step-by-Step Manual Deployment Guide

**Time:** 20-30 minutes  
**Result:** Complete $0/month 24/7 deployment

---

## Step 1: Deploy to Render (10-15 minutes)

### 1.1: Open Render Dashboard
- Go to: https://dashboard.render.com
- You should see the dashboard (you already have it open)

### 1.2: Create New Web Service
1. Click the **"+ New"** button (top right)
2. Select **"Web Service"** from the dropdown

### 1.3: Connect Repository
**Option A: Connect GitHub (Recommended)**
1. Click **"Connect account"** or **"Connect GitHub"**
2. Authorize Render to access your GitHub
3. Select your repository: `neolight` (or your repo name)
4. Click **"Connect"**

**Option B: Use Public Git Repository**
1. Enter your repository URL
2. Render will clone and deploy

### 1.4: Configure Service Settings

**Basic Settings:**
- **Name:** `neolight-primary`
- **Region:** Choose closest to you (e.g., Oregon, Virginia)
- **Branch:** `main` (or your default branch)
- **Root Directory:** Leave empty (or `/` if needed)
- **Runtime:** `Python 3`
- **Plan:** **Free** (select Free tier)

**Build & Deploy:**
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python3 trader/smart_trader.py`

**Health Check:**
- **Health Check Path:** `/health`
- **Health Check Interval:** `30` seconds

### 1.5: Add Environment Variables

Click **"Add Environment Variable"** and add these:

**Required Variables:**
```
TRADING_MODE = PAPER_TRADING_MODE
PYTHONPATH = /opt/render/project/src
PORT = 8080
RENDER_MODE = true
```

**From your .env file (copy these):**
```
ALPACA_API_KEY = (your Alpaca API key)
ALPACA_SECRET_KEY = (your Alpaca secret key)
RCLONE_REMOTE = neo_remote
RCLONE_PATH = NeoLight
```

**Optional (if you have them):**
```
TELEGRAM_BOT_TOKEN = (if you want alerts)
TELEGRAM_CHAT_ID = (if you want alerts)
```

### 1.6: Deploy
1. Click **"Create Web Service"** at the bottom
2. Wait for deployment (5-10 minutes)
3. You'll see build logs in real-time
4. When complete, you'll see: **"Live"** status

### 1.7: Get Service Information

**After deployment:**

1. **Get Service URL:**
   - Look at the top of the service page
   - URL format: `https://neolight-primary.onrender.com`
   - **Copy this URL** - you'll need it for Cloudflare

2. **Get Service ID:**
   - Look at the URL in your browser
   - Format: `https://dashboard.render.com/web/YOUR_SERVICE_ID`
   - Or go to Settings → Service ID
   - **Copy the Service ID**

3. **Get API Key:**
   - Go to: Account Settings → API Keys
   - Click **"Create API Key"**
   - Name it: `neolight-monitor`
   - **Copy the API key** (you'll only see it once!)

### 1.8: Add to Environment Variables

Open terminal and run:

```bash
# Add Render credentials
export RENDER_SERVICE_ID="your_service_id_here"
export RENDER_API_KEY="your_api_key_here"

# Persist to .zshrc
echo "export RENDER_SERVICE_ID=\"your_service_id_here\"" >> ~/.zshrc
echo "export RENDER_API_KEY=\"your_api_key_here\"" >> ~/.zshrc

# Reload
source ~/.zshrc

# Verify
echo "Service ID: $RENDER_SERVICE_ID"
echo "API Key: ${RENDER_API_KEY:0:20}..."
```

**Replace:**
- `your_service_id_here` with your actual Service ID
- `your_api_key_here` with your actual API key

---

## Step 2: Deploy Cloudflare Worker (5-10 minutes)

### 2.1: Open Cloudflare Dashboard
- Go to: https://dash.cloudflare.com
- Login if needed

### 2.2: Create Worker
1. In left sidebar, click **"Workers & Pages"**
2. Click **"Create"** → **"Create Worker"**

### 2.3: Configure Worker
1. **Name:** `neolight-api`
2. Click **"Deploy"** (we'll add code next)

### 2.4: Add Code
1. In the Worker editor, **delete all default code**
2. Open: `~/neolight/cloudflare_worker_ready.js` in your editor
3. **Copy ALL the code** from that file
4. **Paste** into Cloudflare Worker editor

### 2.5: Update RENDER_URL
1. Find this line in the code:
   ```javascript
   const RENDER_URL = 'YOUR_RENDER_SERVICE_URL.onrender.com';
   ```
2. Replace `YOUR_RENDER_SERVICE_URL.onrender.com` with your actual Render URL
   - Example: `neolight-primary.onrender.com`
   - **Don't include** `https://` - just the domain
3. Find the same line in the `scheduled` function and update it there too

### 2.6: Deploy Worker
1. Click **"Save and deploy"** (top right)
2. Wait a few seconds for deployment
3. You'll see: **"Successfully deployed"**

### 2.7: Set Up Scheduled Event (Keep-Alive)

**This keeps Render alive every 10 minutes:**

1. In Worker page, click **"Settings"** tab
2. Scroll to **"Triggers"** section
3. Click **"Add Cron Trigger"**
4. Enter: `*/10 * * * *` (every 10 minutes)
5. Click **"Add Trigger"**
6. Click **"Save"**

**Verify:**
- You should see the cron trigger listed
- It will run every 10 minutes automatically

### 2.8: Test Worker
1. Copy your Worker URL (format: `https://neolight-api.YOUR_SUBDOMAIN.workers.dev`)
2. Test keep-alive:
   ```bash
   curl https://neolight-api.YOUR_SUBDOMAIN.workers.dev/keepalive
   ```
3. Should return JSON with status

---

## Step 3: Start Orchestrator (2 minutes)

### 3.1: Verify Render Credentials
```bash
# Check if credentials are set
echo "Service ID: $RENDER_SERVICE_ID"
echo "API Key: ${RENDER_API_KEY:0:20}..."
```

If not set, add them (see Step 1.8)

### 3.2: Start Orchestrator
```bash
cd ~/neolight
bash scripts/cloud_orchestrator.sh start
```

**Expected output:**
```
🚀 Starting Cloud Orchestrator...
Starting Render usage monitor...
✅ Render usage monitor started (PID: xxxxx)
✅ Cloud Orchestrator started (PID: xxxxx)
Orchestrator running. Monitoring Render usage and managing failover...
```

### 3.3: Verify It's Running
```bash
# Check status
bash scripts/cloud_orchestrator.sh status
```

**Should show:**
- ✅ Orchestrator: Running
- ✅ Render Monitor: Running
- Usage status information

### 3.4: View Logs (Optional)
```bash
# Orchestrator logs
tail -f logs/cloud_orchestrator.log

# Render monitor logs
tail -f logs/render_monitor.log
```

---

## Step 4: Verify Everything Works

### 4.1: Test Render Service
```bash
# Replace with your Render URL
curl https://neolight-primary.onrender.com/health
```

**Expected:** JSON response with status

### 4.2: Test Cloud Run (Backup)
```bash
export CLOUD_RUN_API_KEY=$(grep CLOUD_RUN_API_KEY ~/.zshrc | tail -1 | cut -d'=' -f2 | tr -d '"')
curl -H "X-API-Key: $CLOUD_RUN_API_KEY" \
  "https://neolight-failover-dxhazco67q-uc.a.run.app/health"
```

**Expected:** JSON response (may have cold start delay)

### 4.3: Test Cloudflare Worker
```bash
# Replace with your Worker URL
curl https://neolight-api.YOUR_SUBDOMAIN.workers.dev/health
```

**Expected:** Response from Render (routed through Worker)

### 4.4: Check Usage Monitor
```bash
python3 scripts/render_usage_monitor.py check
```

**Expected:** Shows current usage hours

---

## Troubleshooting

### Render Deployment Fails
- **Check build logs** in Render dashboard
- **Verify requirements.txt** exists
- **Check start command** is correct
- **Verify Python version** (should be 3.x)

### Cloudflare Worker Not Working
- **Check RENDER_URL** is correct (no https://)
- **Verify Worker is deployed** (not just saved)
- **Check scheduled event** is set up
- **Test keep-alive endpoint** manually

### Orchestrator Won't Start
- **Check Render credentials** are set
- **Verify scripts are executable:** `chmod +x scripts/*.sh`
- **Check logs:** `tail -f logs/cloud_orchestrator.log`
- **Verify Python dependencies:** `pip install requests`

### Usage Monitor Not Tracking
- **Check RENDER_API_KEY** is valid
- **Check RENDER_SERVICE_ID** is correct
- **Monitor falls back to estimation** if API fails (this is OK)

---

## Success Checklist

After completing all steps:

- [ ] Render service deployed and running
- [ ] Render Service ID added to environment
- [ ] Render API key added to environment
- [ ] Cloudflare Worker deployed
- [ ] Cloudflare Worker RENDER_URL updated
- [ ] Cloudflare scheduled event configured (every 10 min)
- [ ] Orchestrator started and running
- [ ] Usage monitor tracking hours
- [ ] All services responding to health checks

---

## Quick Reference Commands

```bash
# Check orchestrator status
bash scripts/cloud_orchestrator.sh status

# Start orchestrator
bash scripts/cloud_orchestrator.sh start

# Stop orchestrator
bash scripts/cloud_orchestrator.sh stop

# Check Render usage
python3 scripts/render_usage_monitor.py check

# Check failover status
bash scripts/auto_failover_switch.sh status

# View logs
tail -f logs/cloud_orchestrator.log
tail -f logs/render_monitor.log
```

---

## What Happens Next

Once everything is deployed:

1. **Render runs 24/7** (primary service)
2. **Cloudflare pings Render** every 10 min (keeps it alive)
3. **Monitor tracks usage** (checks every hour)
4. **At 720 hours:** Auto-switches to Cloud Run
5. **At month start:** Auto-switches back to Render
6. **State syncs** to Google Drive every 30 min
7. **Weekly backup** to external drive (Sunday 2 AM)

**Result:** $0/month with 24/7 operation! 🎉

---

**Need help?** Check the logs or see `ZERO_COST_24_7_DEPLOYMENT.md` for detailed troubleshooting.



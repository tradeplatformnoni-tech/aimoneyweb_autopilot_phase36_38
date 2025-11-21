# 🚀 24-Hour Cloud Deployment Plan - Step-by-Step Guide

**Date:** 2025-11-18  
**Platforms:** Google Cloud, Cloudflare, Render  
**Duration:** ~2-3 hours setup, then 24/7 operation

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:
- ✅ Google Cloud account (created)
- ✅ Cloudflare account (created)
- ✅ Render account (from previous project)
- ✅ Alpaca API keys (Paper Trading)
- ✅ All API keys ready (see Required Secrets section)

---

## 🎯 Deployment Strategy

**Primary:** Google Cloud Run (24/7 failover)  
**CDN/DNS:** Cloudflare (performance & security)  
**Backup:** Render (optional, clean up old projects first)

---

## 📦 PART 1: Google Cloud Setup (30-45 minutes)

### Step 1.1: Install Google Cloud SDK

```bash
# macOS
brew install --cask google-cloud-sdk

# Or download from: https://cloud.google.com/sdk/docs/install

# Verify installation
gcloud version
gsutil --version
```

### Step 1.2: Authenticate and Configure

```bash
# Login to Google Cloud
gcloud auth login

# Set your account (replace with your email)
gcloud config set account YOUR_EMAIL@gmail.com

# Create project (or use existing)
gcloud projects create neolight-production --name="NeoLight Production"

# Set active project
gcloud config set project neolight-production

# Set region (us-central1 = Chicago, low latency)
gcloud config set run/region us-central1

# Verify configuration
gcloud config list
```

### Step 1.3: Enable Required Services

```bash
# Enable all required Google Cloud services
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    storage.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    compute.googleapis.com

# Wait for services to enable (takes 1-2 minutes)
echo "Services enabling... check status:"
gcloud services list --enabled
```

### Step 1.4: Create State Storage Bucket

```bash
# Generate unique bucket name
export NL_BUCKET="gs://neolight-state-$(date +%s)"

# Create bucket in same region as Cloud Run
gsutil mb -l us-central1 -b on "$NL_BUCKET"

# Verify bucket created
gsutil ls "$NL_BUCKET"

# Persist environment variable
echo "export NL_BUCKET=$NL_BUCKET" >> ~/.zshrc
source ~/.zshrc

# Display bucket name (save this!)
echo "✅ State bucket: $NL_BUCKET"
```

### Step 1.5: Generate and Store API Key

```bash
# Generate secure random API key
export CLOUD_RUN_API_KEY=$(openssl rand -hex 32)

# Display and SAVE THIS KEY SECURELY
echo "🔑 Your API Key: $CLOUD_RUN_API_KEY"
echo "⚠️  SAVE THIS KEY - You'll need it for Cloudflare and monitoring!"

# Persist to shell
echo "export CLOUD_RUN_API_KEY=$CLOUD_RUN_API_KEY" >> ~/.zshrc
source ~/.zshrc

# Store in Google Secret Manager
echo -n "$CLOUD_RUN_API_KEY" | \
  gcloud secrets create neolight-api-key \
    --replication-policy="automatic" \
    --data-file=-

# Grant Cloud Run access to the secret
PROJECT_NUMBER=$(gcloud projects describe neolight-production --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding neolight-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Verify secret created
gcloud secrets describe neolight-api-key
```

### Step 1.6: Set Trading API Keys in Secret Manager

```bash
# Store Alpaca API keys (replace with your actual keys)
echo -n "YOUR_ALPACA_API_KEY" | \
  gcloud secrets create alpaca-api-key \
    --replication-policy="automatic" \
    --data-file=-

echo -n "YOUR_ALPACA_SECRET_KEY" | \
  gcloud secrets create alpaca-secret-key \
    --replication-policy="automatic" \
    --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding alpaca-api-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding alpaca-secret-key \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 🚀 PART 2: Deploy to Google Cloud Run (20-30 minutes)

### Step 2.1: Sync Local State to Cloud

```bash
cd ~/neolight

# Sync your current state to Google Cloud Storage
./scripts/sync_state_to_cloud.sh

# Or manually:
gsutil -m rsync -r state/ "$NL_BUCKET/state"
gsutil -m rsync -r runtime/ "$NL_BUCKET/runtime"

# Verify sync
gsutil ls -r "$NL_BUCKET"
```

### Step 2.2: Build and Deploy to Cloud Run

```bash
cd ~/neolight

# Deploy using Cloud Build (this takes 10-15 minutes)
gcloud builds submit \
  --config cloud-run/cloudbuild.yaml \
  --substitutions _NL_BUCKET="$NL_BUCKET"

# Monitor build progress
gcloud builds list --limit=1 --format="table(id,status,createTime)"
```

### Step 2.3: Get Cloud Run Service URL

```bash
# Get the deployed service URL
export CLOUD_RUN_SERVICE_URL=$(gcloud run services describe neolight-failover \
  --region us-central1 \
  --format 'value(status.url)')

# Display URL
echo "🌐 Cloud Run URL: $CLOUD_RUN_SERVICE_URL"

# Persist to shell
echo "export CLOUD_RUN_SERVICE_URL=$CLOUD_RUN_SERVICE_URL" >> ~/.zshrc
source ~/.zshrc

# Test health endpoint
curl -s "$CLOUD_RUN_SERVICE_URL/health" | jq .
```

**Expected Response:**
```json
{
  "service": "NeoLight Cloud Supervisor",
  "status": "healthy",
  "trading_mode": "PAPER_TRADING_MODE"
}
```

---

## ☁️ PART 3: Cloudflare Setup (15-20 minutes)

### Step 3.1: Add Domain to Cloudflare

1. **Login to Cloudflare Dashboard**
   - Go to: https://dash.cloudflare.com
   - Select your account

2. **Add Site (if you have a domain)**
   - Click "Add a Site"
   - Enter your domain (e.g., `neolight.yourdomain.com`)
   - Follow DNS setup instructions

3. **Or Use Cloudflare Workers (No Domain Needed)**
   - Go to Workers & Pages
   - Create a new Worker

### Step 3.2: Configure Cloudflare DNS

**Option A: If you have a domain:**

```bash
# In Cloudflare Dashboard:
# 1. Go to DNS → Records
# 2. Add CNAME record:
#    Name: neolight (or @ for root)
#    Target: neolight-failover-xxxxx-uc.a.run.app
#    Proxy: ✅ Proxied (orange cloud)
#    TTL: Auto
```

**Option B: Use Cloudflare Workers (Recommended for API):**

1. Go to Workers & Pages → Create Worker
2. Name: `neolight-api`
3. Add this code:

```javascript
export default {
  async fetch(request) {
    const CLOUD_RUN_URL = 'YOUR_CLOUD_RUN_SERVICE_URL';
    const API_KEY = 'YOUR_CLOUD_RUN_API_KEY';
    
    // Forward request to Cloud Run
    const url = new URL(request.url);
    const targetUrl = `${CLOUD_RUN_URL}${url.pathname}${url.search}`;
    
    const modifiedRequest = new Request(targetUrl, {
      method: request.method,
      headers: {
        ...Object.fromEntries(request.headers),
        'X-API-Key': API_KEY,
        'X-Forwarded-For': request.headers.get('CF-Connecting-IP'),
      },
      body: request.body,
    });
    
    return fetch(modifiedRequest);
  }
}
```

4. Deploy the Worker
5. Your API will be available at: `https://neolight-api.YOUR_SUBDOMAIN.workers.dev`

### Step 3.3: Configure Cloudflare Security

1. **Enable Security Features:**
   - Go to Security → WAF
   - Enable "Cloudflare Managed Ruleset"
   - Enable "OWASP Core Ruleset"

2. **Set Rate Limiting:**
   - Go to Security → Rate Limiting
   - Create rule: 100 requests per minute per IP

3. **Enable Bot Fight Mode:**
   - Go to Security → Bots
   - Enable "Bot Fight Mode"

### Step 3.4: Test Cloudflare Integration

```bash
# Test through Cloudflare (replace with your Cloudflare URL)
curl -s "https://neolight-api.YOUR_SUBDOMAIN.workers.dev/health" | jq .

# Or if using DNS:
curl -s "https://neolight.yourdomain.com/health" | jq .
```

---

## 🧹 PART 4: Clean Up Render (10-15 minutes)

### Step 4.1: List Render Services

1. **Login to Render Dashboard**
   - Go to: https://dashboard.render.com
   - Login with your account

2. **View All Services**
   - Go to "Services" tab
   - List all running services

### Step 4.2: Clean Up Old Projects

**Option A: Delete Unused Services (Recommended)**

1. For each old/unused service:
   - Click on service
   - Go to "Settings" → "Delete Service"
   - Confirm deletion

**Option B: Suspend Services (Keep for Later)**

1. For each service you want to keep:
   - Click on service
   - Go to "Settings" → "Suspend Service"
   - Service stops but data is preserved

### Step 4.3: Deploy NeoLight to Render (Optional Backup)

**Only if you want Render as a backup:**

1. **Create New Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repo (or use Docker)
   - Name: `neolight-backup`

2. **Configure:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python3 trader/smart_trader.py`
   - Environment: `Python 3`
   - Plan: Free tier (or paid if needed)

3. **Set Environment Variables:**
   - Add all secrets from your `.env` file
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
   - etc.

4. **Deploy:**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)

---

## ✅ PART 5: Verification & Testing (15-20 minutes)

### Step 5.1: Test Google Cloud Run

```bash
# Test health endpoint
curl -s "$CLOUD_RUN_SERVICE_URL/health" | jq .

# Test with API key
curl -s "$CLOUD_RUN_SERVICE_URL/metrics" \
  -H "X-API-Key: $CLOUD_RUN_API_KEY" | jq .

# Check logs
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=neolight-failover" \
  --format=json
```

### Step 5.2: Test Cloudflare Integration

```bash
# Test through Cloudflare
curl -s "https://YOUR_CLOUDFLARE_URL/health" | jq .

# Test rate limiting (should work)
for i in {1..5}; do
  curl -s "https://YOUR_CLOUDFLARE_URL/health" | jq .status
  sleep 1
done
```

### Step 5.3: Test Trading System

```bash
# Activate SmartTrader on Cloud Run
curl -X POST "$CLOUD_RUN_SERVICE_URL/activate" \
  -H "X-API-Key: $CLOUD_RUN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"bucket\": \"$NL_BUCKET\", \"force\": true}"

# Check status
curl -s "$CLOUD_RUN_SERVICE_URL/health" | jq .smarttrader_status

# Should show "running"
```

### Step 5.4: Monitor Logs

```bash
# Google Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=50 \
  --format="table(timestamp,textPayload)"

# Local monitor logs (if running)
tail -f ~/neolight/logs/hybrid_failover_monitor.log
```

---

## 🔄 PART 6: Set Up Local Monitor (Optional, 10 minutes)

### Step 6.1: Start Local Failover Monitor

```bash
cd ~/neolight

# Start monitor (watches local system, activates cloud if local fails)
./scripts/hybrid_failover_monitor.sh
```

**Expected Output:**
```
🛰️ Hybrid monitor started (v2.1-hybrid)
   Local health: http://localhost:8100/health
   Cloud failover: https://neolight-failover-xxxxx-uc.a.run.app
   State bucket: gs://neolight-state-1234567890
   Check interval: 15s
```

### Step 6.2: Test Failover

```bash
# Simulate local failure (stop local SmartTrader)
# Monitor should detect and activate Cloud Run within 15-45 seconds

# Check Cloud Run status
curl -s "$CLOUD_RUN_SERVICE_URL/health" | jq .smarttrader_status
```

---

## 📊 PART 7: Monitoring Dashboard Setup (10 minutes)

### Step 7.1: Access Cloud Run Dashboard

```bash
# Open Cloud Run console
open "https://console.cloud.google.com/run?project=neolight-production"

# Or view service directly
open "$CLOUD_RUN_SERVICE_URL"
```

### Step 7.2: Set Up Cloudflare Analytics

1. Go to Cloudflare Dashboard
2. Select your site/worker
3. Go to "Analytics" → "Web Analytics"
4. Enable analytics to track traffic

### Step 7.3: Set Up Alerts (Optional)

```bash
# Create Google Cloud alert for failures
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="NeoLight Cloud Run Failure" \
  --condition-threshold-value=1 \
  --condition-threshold-duration=300s
```

---

## 🎯 PART 8: Final Checklist

### Pre-Launch Verification

- [ ] Google Cloud Run deployed and healthy
- [ ] Cloudflare configured and routing traffic
- [ ] Render cleaned up (or backup deployed)
- [ ] API keys stored in Secret Manager
- [ ] State bucket created and synced
- [ ] Health endpoints responding
- [ ] Logs accessible and readable
- [ ] Trading system can activate on Cloud Run
- [ ] Cloudflare security rules enabled
- [ ] Monitor script tested (if using)

### Post-Launch Monitoring

- [ ] Check logs daily for first week
- [ ] Test failover weekly
- [ ] Review Cloud Run costs monthly
- [ ] Monitor Cloudflare analytics
- [ ] Verify trading system is running

---

## 💰 Cost Estimates

### Google Cloud Run
- **Always-on (1 min instance)**: ~$7-10/month
- **Cloud Storage (1GB)**: ~$0.02/month
- **Cloud Build**: Free tier (2 builds/day)
- **Total**: ~$7-12/month

### Cloudflare
- **Free tier**: $0/month (includes CDN, DNS, basic security)
- **Pro tier** (optional): $20/month (advanced features)

### Render
- **Free tier**: $0/month (limited hours)
- **Starter tier**: $7/month (if using as backup)

**Total Estimated Cost: $7-32/month** (depending on tier choices)

---

## 🚨 Troubleshooting

### Issue: Cloud Run deployment fails

```bash
# Check build logs
gcloud builds list --limit=5

# View specific build
gcloud builds log BUILD_ID

# Common fixes:
# - Check Dockerfile exists
# - Verify cloudbuild.yaml syntax
# - Ensure services are enabled
```

### Issue: Cloudflare not routing to Cloud Run

```bash
# Check DNS settings in Cloudflare
# Verify CNAME target matches Cloud Run URL
# Ensure proxy is enabled (orange cloud)

# Test direct Cloud Run access
curl "$CLOUD_RUN_SERVICE_URL/health"
```

### Issue: API key authentication fails

```bash
# Verify secret exists
gcloud secrets describe neolight-api-key

# Check API key matches
echo $CLOUD_RUN_API_KEY

# Test with correct header
curl -H "X-API-Key: $CLOUD_RUN_API_KEY" "$CLOUD_RUN_SERVICE_URL/metrics"
```

### Issue: State sync fails

```bash
# Check bucket permissions
gsutil ls "$NL_BUCKET"

# Verify bucket location
gsutil ls -L -b "$NL_BUCKET" | grep Location

# Re-sync state
./scripts/sync_state_to_cloud.sh
```

---

## 📞 Emergency Procedures

### Full System Failure

```bash
# 1. Activate Cloud Run manually
curl -X POST "$CLOUD_RUN_SERVICE_URL/activate" \
  -H "X-API-Key: $CLOUD_RUN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"bucket\": \"$NL_BUCKET\", \"force\": true}"

# 2. Check status
curl "$CLOUD_RUN_SERVICE_URL/health" | jq

# 3. View logs
gcloud logging tail "resource.type=cloud_run_revision" --limit=100
```

### Rollback Deployment

```bash
# List revisions
gcloud run revisions list --service=neolight-failover --region=us-central1

# Rollback to previous
gcloud run services update-traffic neolight-failover \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-central1
```

---

## ✅ Success Criteria

Your deployment is successful when:

1. ✅ Cloud Run service is running and healthy
2. ✅ Health endpoint returns `{"status": "healthy"}`
3. ✅ Cloudflare is routing traffic correctly
4. ✅ SmartTrader can activate on Cloud Run
5. ✅ State syncs between local and cloud
6. ✅ Logs are accessible and readable
7. ✅ API key authentication works
8. ✅ System runs 24/7 without manual intervention

---

## 🎉 Next Steps After Deployment

1. **Monitor for 24 hours** - Watch logs and metrics
2. **Test failover** - Simulate local failure, verify cloud activation
3. **Optimize costs** - Review usage, adjust instance sizes if needed
4. **Set up alerts** - Configure notifications for failures
5. **Document customizations** - Note any changes made during deployment

---

## 📚 Reference Files

- `HYBRID_DEPLOYMENT_GUIDE.md` - Detailed Google Cloud setup
- `FLYIO_DEPLOYMENT_GUIDE.md` - Alternative Fly.io deployment
- `cloud-run/cloudbuild.yaml` - Cloud Build configuration
- `cloud-run/Dockerfile` - Container definition
- `scripts/sync_state_to_cloud.sh` - State sync script
- `scripts/hybrid_failover_monitor.sh` - Failover monitor

---

**🚀 Your system is now deployed and running 24/7 in the cloud!**

**Total Setup Time:** ~2-3 hours  
**Ongoing Operation:** Fully automated, 24/7  
**Monitoring:** Cloud Run logs, Cloudflare analytics


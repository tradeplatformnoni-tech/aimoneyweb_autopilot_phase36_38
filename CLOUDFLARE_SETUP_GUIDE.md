# ☁️ Cloudflare Setup Guide - Step by Step

**Purpose:** Set up Cloudflare to proxy requests to your Cloud Run service  
**Time:** 15-20 minutes  
**Requires:** Cloudflare account (you already have this)

---

## Prerequisites

Before starting, you need:
- ✅ Cloudflare account (ready)
- ✅ Cloud Run service URL (will get after deployment)
- ✅ Cloud Run API key (already saved in ~/.zshrc)

---

## Step 1: Get Your Cloud Run Details

### Wait for Deployment to Complete

```bash
# Check if deployment is done
gcloud builds list --limit=1 --format="value(status)" --project neolight-production

# When status is "SUCCESS", get the service URL:
export CLOUD_RUN_SERVICE_URL=$(gcloud run services describe neolight-failover \
  --region us-central1 \
  --format 'value(status.url)')

echo "Cloud Run URL: $CLOUD_RUN_SERVICE_URL"

# Get your API key
export CLOUD_RUN_API_KEY=$(grep CLOUD_RUN_API_KEY ~/.zshrc | tail -1 | cut -d'=' -f2 | tr -d '"')
echo "API Key: $CLOUD_RUN_API_KEY"
```

**Save these values - you'll need them for Cloudflare!**

---

## Step 2: Login to Cloudflare

1. **Open Cloudflare Dashboard**
   ```bash
   open https://dash.cloudflare.com
   ```

2. **Login** with your account

3. **Select your account** (if you have multiple)

---

## Step 3: Create Cloudflare Worker

### Option A: Using Cloudflare Dashboard (Recommended)

1. **Go to Workers & Pages**
   - Click "Workers & Pages" in left sidebar
   - Or go to: https://dash.cloudflare.com → Workers & Pages

2. **Create Worker**
   - Click "Create application"
   - Click "Create Worker"

3. **Configure Worker**
   - **Name:** `neolight-api` (or any name you prefer)
   - **Description:** "NeoLight Trading System API Proxy"

4. **Add Code**

   Replace the default code with this:

   ```javascript
   export default {
     async fetch(request, env, ctx) {
       // Replace with your actual Cloud Run URL
       const CLOUD_RUN_URL = 'YOUR_CLOUD_RUN_SERVICE_URL_HERE';
       
       // Replace with your actual API key
       const API_KEY = 'YOUR_CLOUD_RUN_API_KEY_HERE';
       
       // Get the request path and query
       const url = new URL(request.url);
       const targetUrl = `${CLOUD_RUN_URL}${url.pathname}${url.search}`;
       
       // Create modified request with API key
       const modifiedRequest = new Request(targetUrl, {
         method: request.method,
         headers: {
           ...Object.fromEntries(request.headers),
           'X-API-Key': API_KEY,
           'X-Forwarded-For': request.headers.get('CF-Connecting-IP') || '',
           'X-Real-IP': request.headers.get('CF-Connecting-IP') || '',
         },
         body: request.body,
       });
       
       // Forward request to Cloud Run
       try {
         const response = await fetch(modifiedRequest);
         
         // Create new response with CORS headers
         const newResponse = new Response(response.body, {
           status: response.status,
           statusText: response.statusText,
           headers: {
             ...Object.fromEntries(response.headers),
             'Access-Control-Allow-Origin': '*',
             'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
             'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
           },
         });
         
         return newResponse;
       } catch (error) {
         return new Response(JSON.stringify({ 
           error: 'Failed to connect to Cloud Run',
           message: error.message 
         }), {
           status: 502,
           headers: { 'Content-Type': 'application/json' },
         });
       }
     }
   };
   ```

5. **Replace Placeholders**
   - Replace `YOUR_CLOUD_RUN_SERVICE_URL_HERE` with your actual Cloud Run URL
   - Replace `YOUR_CLOUD_RUN_API_KEY_HERE` with your actual API key

6. **Deploy**
   - Click "Save and deploy"
   - Wait for deployment (takes a few seconds)

7. **Get Your Worker URL**
   - After deployment, you'll see: `https://neolight-api.YOUR_SUBDOMAIN.workers.dev`
   - **Save this URL!**

---

## Step 4: Test Cloudflare Worker

```bash
# Test health endpoint through Cloudflare
curl -s "https://neolight-api.YOUR_SUBDOMAIN.workers.dev/health" | jq .

# Should return:
# {
#   "service": "NeoLight Cloud Supervisor",
#   "status": "healthy",
#   ...
# }
```

---

## Step 5: Configure Cloudflare Security (Optional but Recommended)

### Enable WAF (Web Application Firewall)

1. **Go to Security → WAF**
2. **Enable:**
   - ✅ Cloudflare Managed Ruleset
   - ✅ OWASP Core Ruleset

### Set Rate Limiting

1. **Go to Security → Rate Limiting**
2. **Create Rule:**
   - **Name:** "NeoLight API Rate Limit"
   - **Requests:** 100 per minute
   - **Action:** Block

### Enable Bot Fight Mode

1. **Go to Security → Bots**
2. **Enable:** Bot Fight Mode

---

## Step 6: (Optional) Use Custom Domain

If you have a domain:

1. **Add Domain to Cloudflare**
   - Go to "Add a Site"
   - Enter your domain
   - Follow DNS setup

2. **Create CNAME Record**
   - Go to DNS → Records
   - Add CNAME:
     - **Name:** `api` (or `neolight`)
     - **Target:** `neolight-api.YOUR_SUBDOMAIN.workers.dev`
     - **Proxy:** ✅ Proxied (orange cloud)

3. **Update Worker Route**
   - Go to Workers & Pages → Your Worker
   - Add route: `api.yourdomain.com/*`

---

## Step 7: Monitor and Test

### Test Endpoints

```bash
# Health check
curl "https://neolight-api.YOUR_SUBDOMAIN.workers.dev/health"

# Metrics (requires API key in header)
curl -H "X-API-Key: YOUR_KEY" \
  "https://neolight-api.YOUR_SUBDOMAIN.workers.dev/metrics"
```

### Monitor Analytics

1. **Go to Workers & Pages → Your Worker**
2. **Click "Analytics"** to see:
   - Request count
   - Error rate
   - Response times

---

## Troubleshooting

### Issue: 502 Bad Gateway

**Cause:** Cloud Run service not responding  
**Fix:**
```bash
# Check Cloud Run status
gcloud run services describe neolight-failover --region us-central1

# Check Cloud Run logs
gcloud logging tail "resource.type=cloud_run_revision"
```

### Issue: 401 Unauthorized

**Cause:** API key mismatch  
**Fix:** Verify API key in Worker code matches your Cloud Run API key

### Issue: CORS Errors

**Cause:** Missing CORS headers  
**Fix:** Worker code already includes CORS headers - verify they're present

---

## Quick Reference

**Your URLs:**
- Cloud Run: `https://neolight-failover-XXXXX-uc.a.run.app`
- Cloudflare Worker: `https://neolight-api.YOUR_SUBDOMAIN.workers.dev`
- (Optional) Custom Domain: `https://api.yourdomain.com`

**Test Commands:**
```bash
# Direct Cloud Run
curl "$CLOUD_RUN_SERVICE_URL/health"

# Through Cloudflare
curl "https://neolight-api.YOUR_SUBDOMAIN.workers.dev/health"
```

---

## ✅ Setup Complete!

Your Cloudflare Worker is now:
- ✅ Proxying requests to Cloud Run
- ✅ Adding API key authentication
- ✅ Providing CORS headers
- ✅ Protected by Cloudflare security

**Next:** Test the endpoints and monitor analytics!


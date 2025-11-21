# ☁️ Cloudflare Worker - Quick Deploy Guide

**Time:** 5-10 minutes  
**Your API Key:** Already included in the code below

---

## Step-by-Step Instructions

### Step 1: Open Cloudflare Dashboard
✅ Should be opening automatically  
Or go to: https://dash.cloudflare.com

### Step 2: Create Worker

1. Click **"Workers & Pages"** in left sidebar
2. Click **"Create application"**
3. Click **"Create Worker"**

### Step 3: Configure Worker

1. **Name:** `neolight-api` (or any name you prefer)
2. **Description:** "NeoLight Trading System API Proxy"

### Step 4: Paste Code

1. **Delete** the default code in the editor
2. **Copy** the code from `cloudflare_worker_code.js` (shown below)
3. **Paste** into the Cloudflare Worker editor

**The code already has:**
- ✅ Your Cloud Run URL
- ✅ Your API key (pre-configured)

### Step 5: Deploy

1. Click **"Save and deploy"** button
2. Wait a few seconds for deployment
3. You'll see: `https://neolight-api.YOUR_SUBDOMAIN.workers.dev`

### Step 6: Test

After deployment, test with:

```bash
# Replace YOUR_SUBDOMAIN with your actual subdomain
curl "https://neolight-api.YOUR_SUBDOMAIN.workers.dev/health"
```

---

## Your Worker Code (Ready to Copy)

```javascript
// Cloudflare Worker Code for NeoLight API Proxy
// Your API key is already included!

export default {
  async fetch(request, env, ctx) {
    // Your Cloud Run configuration
    const CLOUD_RUN_URL = 'https://neolight-failover-dxhazco67q-uc.a.run.app';
    const API_KEY = '8dd0d2b708490523a1e3770cd14300e4b0df4a183d2250fe3f7391887db35ab2';
    
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

---

## After Deployment

### Get Your Worker URL

After deploying, Cloudflare will show you a URL like:
```
https://neolight-api.YOUR_SUBDOMAIN.workers.dev
```

**Save this URL!** You'll use it to access your API.

### Test Endpoints

```bash
# Health check
curl "https://neolight-api.YOUR_SUBDOMAIN.workers.dev/health"

# Should return JSON with service status
```

### Monitor Analytics

1. Go to Workers & Pages → Your Worker
2. Click **"Analytics"** to see:
   - Request count
   - Error rate
   - Response times

---

## Troubleshooting

### Issue: 502 Bad Gateway
**Cause:** Cloud Run service not responding  
**Fix:** Check Cloud Run logs:
```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=neolight-failover"
```

### Issue: CORS Errors
**Status:** Code already includes CORS headers - should work

### Issue: 403 Forbidden
**Cause:** API key mismatch  
**Fix:** Verify API key in Worker code matches your Cloud Run API key

---

## ✅ Setup Complete!

Once deployed, your API will be accessible through Cloudflare at:
```
https://neolight-api.YOUR_SUBDOMAIN.workers.dev
```

**Benefits:**
- ✅ CDN caching
- ✅ DDoS protection
- ✅ Global distribution
- ✅ Analytics
- ✅ Security features

---

**Ready? Go to Cloudflare dashboard and create your Worker!**


// Cloudflare Worker - Keep-Alive + Smart Routing (Service Worker Format)
// ==============================================
// World-Class Proactive Failover System
// - Keeps Render alive (pings every 10 minutes)
// - Routes traffic to active provider (Render or Cloud Run)
// - Automatic failover detection
// - CORS and security headers

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const RENDER_URL = 'neolight-autopilot-python.onrender.com';
  const CLOUD_RUN_URL = 'https://neolight-failover-dxhazco67q-uc.a.run.app';
  const CLOUD_RUN_API_KEY = '8dd0d2b708490523a1e3770cd14300e4b0df4a183d2250fe3f7391887db35ab2';
  
  const url = new URL(request.url);
  const path = url.pathname;
  
  // Keep-alive endpoint (ping Render every 10 minutes)
  if (path === '/keepalive' || path === '/ping') {
    try {
      const renderResponse = await fetch(`https://${RENDER_URL}/health`, {
        method: 'GET',
        headers: {
          'User-Agent': 'Cloudflare-KeepAlive/1.0'
        }
      });
      
      return new Response(JSON.stringify({
        status: 'ok',
        render_status: renderResponse.status,
        timestamp: new Date().toISOString(),
        message: 'Keep-alive ping sent'
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (error) {
      return new Response(JSON.stringify({
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString()
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
  
  // Determine active provider (check status file or default to Render)
  // For now, default to Render (primary)
  const ACTIVE_PROVIDER = 'render'; // This should be updated by orchestrator
  
  let targetUrl;
  let headers = {};
  
  // Copy request headers
  request.headers.forEach((value, key) => {
    headers[key] = value;
  });
  
  headers['X-Forwarded-For'] = request.headers.get('CF-Connecting-IP') || '';
  headers['X-Real-IP'] = request.headers.get('CF-Connecting-IP') || '';
  
  if (ACTIVE_PROVIDER === 'render') {
    // Route to Render
    targetUrl = `https://${RENDER_URL}${path}${url.search}`;
  } else {
    // Route to Cloud Run (add API key)
    targetUrl = `${CLOUD_RUN_URL}${path}${url.search}`;
    headers['X-API-Key'] = CLOUD_RUN_API_KEY;
  }
  
  // Forward request to active provider
  try {
    const response = await fetch(targetUrl, {
      method: request.method,
      headers: headers,
      body: request.body
    });
    
    // Create response with CORS headers
    const newHeaders = new Headers(response.headers);
    newHeaders.set('Access-Control-Allow-Origin', '*');
    newHeaders.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    newHeaders.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key');
    
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders
    });
  } catch (error) {
    // If primary fails, try failover
    if (ACTIVE_PROVIDER === 'render') {
      // Try Cloud Run as backup
      try {
        const backupUrl = `${CLOUD_RUN_URL}${path}${url.search}`;
        const backupHeaders = {};
        request.headers.forEach((value, key) => {
          backupHeaders[key] = value;
        });
        backupHeaders['X-API-Key'] = CLOUD_RUN_API_KEY;
        
        const backupResponse = await fetch(backupUrl, {
          method: request.method,
          headers: backupHeaders,
          body: request.body
        });
        
        const backupHeadersNew = new Headers(backupResponse.headers);
        backupHeadersNew.set('Access-Control-Allow-Origin', '*');
        
        return new Response(backupResponse.body, {
          status: backupResponse.status,
          headers: backupHeadersNew
        });
      } catch (backupError) {
        return new Response(JSON.stringify({
          error: 'Both providers unavailable',
          primary_error: error.message,
          backup_error: backupError.message
        }), {
          status: 502,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }
    
    return new Response(JSON.stringify({
      error: 'Failed to connect to provider',
      message: error.message
    }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Scheduled event for keep-alive (runs every 10 minutes)
addEventListener('scheduled', event => {
  event.waitUntil(handleScheduled(event));
});

async function handleScheduled(event) {
  const RENDER_URL = 'neolight-autopilot-python.onrender.com';
  
  try {
    await fetch(`https://${RENDER_URL}/health`, {
      method: 'GET',
      headers: {
        'User-Agent': 'Cloudflare-KeepAlive-Scheduled/1.0'
      }
    });
    
    console.log(`Keep-alive ping sent at ${new Date().toISOString()}`);
  } catch (error) {
    console.error(`Keep-alive ping failed: ${error.message}`);
  }
}


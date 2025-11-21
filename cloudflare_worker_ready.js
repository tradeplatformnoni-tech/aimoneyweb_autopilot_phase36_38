// Cloudflare Worker - Keep-Alive + Smart Routing
// ==============================================
// READY TO DEPLOY - Update RENDER_URL below

export default {
  async fetch(request, env, ctx) {
    // UPDATE THIS with your Render service URL after deployment
    const RENDER_URL = 'YOUR_RENDER_SERVICE_URL.onrender.com';
    const CLOUD_RUN_URL = 'https://neolight-failover-dxhazco67q-uc.a.run.app';
    const CLOUD_RUN_API_KEY = '8dd0d2b708490523a1e3770cd14300e4b0df4a183d2250fe3f7391887db35ab2';
    
    const url = new URL(request.url);
    const path = url.pathname;
    
    // Keep-alive endpoint
    if (path === '/keepalive' || path === '/ping') {
      try {
        const renderResponse = await fetch(`https://${RENDER_URL}/health`, {
          method: 'GET',
          headers: { 'User-Agent': 'Cloudflare-KeepAlive/1.0' },
          signal: AbortSignal.timeout(5000)
        });
        return new Response(JSON.stringify({
          status: 'ok',
          render_status: renderResponse.status,
          timestamp: new Date().toISOString()
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        return new Response(JSON.stringify({
          status: 'error',
          error: error.message
        }), { status: 500, headers: { 'Content-Type': 'application/json' } });
      }
    }
    
    // Route to active provider (default: Render)
    const ACTIVE_PROVIDER = 'render';
    let targetUrl;
    let headers = {
      ...Object.fromEntries(request.headers),
      'X-Forwarded-For': request.headers.get('CF-Connecting-IP') || '',
    };
    
    if (ACTIVE_PROVIDER === 'render') {
      targetUrl = `https://${RENDER_URL}${path}${url.search}`;
    } else {
      targetUrl = `${CLOUD_RUN_URL}${path}${url.search}`;
      headers['X-API-Key'] = CLOUD_RUN_API_KEY;
    }
    
    try {
      const response = await fetch(targetUrl, {
        method: request.method,
        headers: headers,
        body: request.body,
        signal: AbortSignal.timeout(30000)
      });
      
      return new Response(response.body, {
        status: response.status,
        headers: {
          ...Object.fromEntries(response.headers),
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        },
      });
    } catch (error) {
      return new Response(JSON.stringify({
        error: 'Failed to connect',
        message: error.message
      }), { status: 502, headers: { 'Content-Type': 'application/json' } });
    }
  },
  
  async scheduled(event, env, ctx) {
    const RENDER_URL = 'YOUR_RENDER_SERVICE_URL.onrender.com';
    try {
      await fetch(`https://${RENDER_URL}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000)
      });
      console.log(`Keep-alive ping: ${new Date().toISOString()}`);
    } catch (error) {
      console.error(`Keep-alive failed: ${error.message}`);
    }
  }
};

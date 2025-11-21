// Cloudflare Worker Code for NeoLight API Proxy
// Replace YOUR_CLOUD_RUN_SERVICE_URL_HERE and YOUR_CLOUD_RUN_API_KEY_HERE with your actual values

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


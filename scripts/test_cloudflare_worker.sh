#!/usr/bin/env bash
# Test Cloudflare Worker after deployment

echo "=== Testing Cloudflare Worker ==="
echo ""

read -p "Enter your Cloudflare Worker URL (e.g., https://neolight-api.xxx.workers.dev): " WORKER_URL

if [[ -z "$WORKER_URL" ]]; then
    echo "❌ No URL provided"
    exit 1
fi

echo ""
echo "Testing health endpoint..."
echo ""

# Test health
HEALTH_RESPONSE=$(curl -s "$WORKER_URL/health")
echo "Response:"
echo "$HEALTH_RESPONSE" | jq . 2>/dev/null || echo "$HEALTH_RESPONSE"

echo ""
echo "✅ Test complete!"

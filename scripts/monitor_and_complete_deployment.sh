#!/bin/bash
# Monitor Render deployment and automatically complete setup when ready

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SERVICE_ID="${RENDER_SERVICE_ID:-srv-d4fm045rnu6s73e7ehb0}"
SERVICE_URL="${RENDER_SERVICE_URL:-https://neolight-autopilot-python.onrender.com}"

# Load credentials
source <(grep -v '^#' "$ROOT/.api_credentials" | grep -v '^$' | sed 's/^/export /')

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo "═══════════════════════════════════════════════════════════════"
echo "⏳ Monitoring Render Deployment"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check deployment status
python3 << PYTHON_SCRIPT
import os
import requests
import time
import sys

RENDER_API_KEY = os.getenv('RENDER_API_KEY')
SERVICE_ID = '$SERVICE_ID'
RENDER_API_BASE = 'https://api.render.com/v1'

headers = {
    'Accept': 'application/json',
    'Authorization': f'Bearer {RENDER_API_KEY}'
}

max_attempts = 20
for attempt in range(max_attempts):
    response = requests.get(
        f'{RENDER_API_BASE}/services/{SERVICE_ID}/deploys',
        headers=headers,
        params={'limit': 1}
    )
    
    if response.status_code == 200:
        deploys = response.json()
        if deploys:
            deploy = deploys[0].get('deploy', {})
            status = deploy.get('status', 'unknown')
            
            if status == 'live':
                print("✅ DEPLOYMENT SUCCESSFUL!")
                sys.exit(0)
            elif status in ['build_failed', 'update_failed']:
                print(f"❌ Deployment failed: {status}")
                sys.exit(1)
            else:
                if attempt < max_attempts - 1:
                    time.sleep(15)
    
if attempt == max_attempts - 1:
    print("⏳ Deployment still in progress (timeout)")
    sys.exit(2)
PYTHON_SCRIPT

DEPLOYMENT_STATUS=$?

if [ $DEPLOYMENT_STATUS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    echo ""
    echo "Running complete setup..."
    bash "$ROOT/scripts/complete_deployment_setup.sh"
elif [ $DEPLOYMENT_STATUS -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}❌ Deployment failed - check dashboard logs${NC}"
    exit 1
else
    echo ""
    echo -e "${YELLOW}⏳ Deployment still in progress${NC}"
    echo "Run this script again later, or check dashboard manually"
    exit 2
fi


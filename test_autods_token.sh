#!/bin/bash
# Test AutoDS Token Connection

set -e

TOKEN="a2b1c3bf-d143-4516-905f-cf4bcf365dc0"

cd ~/neolight

echo "============================================================"
echo "🔑 Testing AutoDS Token Connection"
echo "============================================================"
echo ""
echo "Token: ${TOKEN:0:20}..."
echo ""

# Export token
export AUTODS_TOKEN="$TOKEN"
export DROPSHIP_PLATFORM="ebay"
export EBAY_USERNAME="seakin67"

echo "1. Testing direct connection..."
echo ""
python3 -c "
import sys
sys.path.insert(0, '.')
from agents.autods_integration import test_autods_connection

if test_autods_connection():
    print('✅ TOKEN WORKS! Connection successful!')
else:
    print('❌ Connection failed')
" || {
    echo "❌ Test failed"
    exit 1
}

echo ""
echo "2. Testing with agent..."
echo ""
python3 -c "
import sys
sys.path.insert(0, '.')
import os
os.environ['AUTODS_TOKEN'] = '$TOKEN'
os.environ['DROPSHIP_PLATFORM'] = 'ebay'

from agents.dropship_agent import AUTODS_AVAILABLE, AUTODS_AUTH, PREFERRED_PLATFORM

print(f'   AUTODS_AVAILABLE: {AUTODS_AVAILABLE}')
print(f'   AUTODS_AUTH: {AUTODS_AUTH[:20] if AUTODS_AUTH else \"None\"}...')
print(f'   PREFERRED_PLATFORM: {PREFERRED_PLATFORM}')

if AUTODS_AVAILABLE and AUTODS_AUTH:
    print('✅ Agent can access token!')
else:
    print('❌ Agent cannot access token')
"

echo ""
echo "3. Testing full integration test..."
echo ""
python3 agents/autods_integration.py 2>&1 | grep -E "(✅|❌|⚠️|Token|Connection|Account)" | head -10

echo ""
echo "============================================================"
echo "✅ Token Test Complete!"
echo "============================================================"
echo ""
echo "If you see ✅ messages above, your token is working!"
echo ""


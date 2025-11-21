#!/usr/bin/env python3
"""
Get Render build logs and error details
"""
import os
import sys
import requests
import json

# Load credentials
CREDENTIALS_FILE = os.path.expanduser("~/neolight/.api_credentials")
if os.path.exists(CREDENTIALS_FILE):
    with open(CREDENTIALS_FILE, 'r') as f:
        for line in f:
            if line.startswith("RENDER_API_KEY="):
                os.environ["RENDER_API_KEY"] = line.split("'")[1] if "'" in line else line.split("=")[1].strip()

RENDER_API_KEY = os.getenv('RENDER_API_KEY')
RENDER_SERVICE_ID = os.getenv('RENDER_SERVICE_ID', 'srv-d4fm045rnu6s73e7ehb0')
RENDER_API_BASE = 'https://api.render.com/v1'

if not RENDER_API_KEY:
    print("❌ ERROR: RENDER_API_KEY not set")
    sys.exit(1)

headers = {
    'Authorization': f'Bearer {RENDER_API_KEY}',
    'Accept': 'application/json'
}

def get_latest_deploy():
    """Get latest deployment with details"""
    try:
        url = f'{RENDER_API_BASE}/services/{RENDER_SERVICE_ID}/deploys'
        response = requests.get(url, headers=headers, timeout=10, params={'limit': 1})
        response.raise_for_status()
        data = response.json()
        deploys = data if isinstance(data, list) else data.get('deploys', [])
        if deploys and len(deploys) > 0:
            deploy = deploys[0]
            return deploy.get('deploy', deploy)
        return None
    except Exception as e:
        print(f"❌ Error fetching deployment: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"   Response: {e.response.text}")
            except:
                pass
        return None

def get_build_logs(deploy_id):
    """Get build logs for a deployment"""
    try:
        url = f'{RENDER_API_BASE}/deploys/{deploy_id}/build_logs'
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"⚠️  Could not fetch build logs: {e}")
        return None

print("═══════════════════════════════════════════════════════════════")
print("🔍 RENDER BUILD FAILURE DIAGNOSIS")
print("═══════════════════════════════════════════════════════════════")
print()

deploy = get_latest_deploy()
if deploy:
    print("📋 DEPLOYMENT DETAILS:")
    print(f"   ID: {deploy.get('id', 'N/A')}")
    print(f"   Status: {deploy.get('status', 'N/A')}")
    print(f"   Created: {deploy.get('createdAt', 'N/A')}")
    print(f"   Finished: {deploy.get('finishedAt', 'N/A')}")
    
    if 'commit' in deploy:
        commit = deploy['commit']
        print(f"   Commit: {commit.get('id', 'N/A')[:8]} - {commit.get('message', 'N/A')[:60]}")
    
    if 'build' in deploy:
        build = deploy['build']
        print(f"   Build ID: {build.get('id', 'N/A')}")
        
        # Try to get build logs
        build_id = build.get('id')
        if build_id:
            print()
            print("📜 BUILD LOGS:")
            logs = get_build_logs(build_id)
            if logs:
                # Show last 50 lines (most relevant)
                log_lines = logs.split('\n')
                print("   (Last 50 lines of build output)")
                print("   " + "─" * 70)
                for line in log_lines[-50:]:
                    print(f"   {line}")
                print("   " + "─" * 70)
            else:
                print("   ⚠️  Build logs not available via API")
                print("   Check dashboard: https://dashboard.render.com/web/{}/events".format(RENDER_SERVICE_ID))
    
    print()
    print("═══════════════════════════════════════════════════════════════")
    print()
    print("💡 TROUBLESHOOTING TIPS:")
    print()
    print("1. Check dashboard for full logs:")
    print(f"   https://dashboard.render.com/web/{RENDER_SERVICE_ID}/events")
    print()
    print("2. Verify Python version in dashboard:")
    print("   Settings → Runtime → Python Version (should be 3.11)")
    print()
    print("3. Common issues:")
    print("   - pythonVersion field in render.yaml may not be supported")
    print("   - Set Python version manually in dashboard")
    print("   - Check if requirements_render.txt is in root")
    print("   - Verify render_app_simple.py exists")
    print()
else:
    print("❌ Could not fetch deployment details")
    print("   Check dashboard: https://dashboard.render.com/web/{}/events".format(RENDER_SERVICE_ID))


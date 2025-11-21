#!/usr/bin/env python3
"""
Quick script to check Render deployment status
"""
import os
import sys
import json
import requests
from datetime import datetime

# Load credentials
CREDENTIALS_FILE = os.path.expanduser("~/neolight/.api_credentials")
if os.path.exists(CREDENTIALS_FILE):
    with open(CREDENTIALS_FILE, 'r') as f:
        for line in f:
            if line.startswith("RENDER_API_KEY="):
                os.environ["RENDER_API_KEY"] = line.split("'")[1] if "'" in line else line.split("=")[1].strip()

RENDER_API_KEY = os.getenv('RENDER_API_KEY')
RENDER_SERVICE_ID = os.getenv('RENDER_SERVICE_ID', 'srv-d4fm045rnu6s73e7ehb0')  # Default to new service
RENDER_API_BASE = 'https://api.render.com/v1'

if not RENDER_API_KEY:
    print("❌ ERROR: RENDER_API_KEY not set")
    print("   Source credentials: source <(grep -v '^#' ~/neolight/.api_credentials | grep -v '^$' | sed 's/^/export /')")
    sys.exit(1)

headers = {
    'Authorization': f'Bearer {RENDER_API_KEY}',
    'Accept': 'application/json'
}

def get_service_info():
    """Get service information"""
    try:
        url = f'{RENDER_API_BASE}/services/{RENDER_SERVICE_ID}'
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Render API returns service in 'service' key
        return data.get('service', data)
    except Exception as e:
        print(f"❌ Error fetching service info: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"   Response: {e.response.text}")
            except:
                pass
        return None

def get_latest_deploy():
    """Get latest deployment"""
    try:
        url = f'{RENDER_API_BASE}/services/{RENDER_SERVICE_ID}/deploys'
        response = requests.get(url, headers=headers, timeout=10, params={'limit': 1})
        response.raise_for_status()
        data = response.json()
        # Render API may return as list or wrapped in 'deploys'
        deploys = data if isinstance(data, list) else data.get('deploys', [])
        if deploys and len(deploys) > 0:
            deploy = deploys[0]
            # May be wrapped in 'deploy' key
            return deploy.get('deploy', deploy)
        return None
    except Exception as e:
        print(f"❌ Error fetching deployments: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"   Response: {e.response.text}")
            except:
                pass
        return None

def format_status(status):
    """Format status with emoji"""
    status_map = {
        'live': '✅ LIVE',
        'build_in_progress': '🔨 BUILDING',
        'update_in_progress': '🔄 UPDATING',
        'build_failed': '❌ BUILD FAILED',
        'update_failed': '❌ UPDATE FAILED',
        'canceled': '⚠️ CANCELED',
        'deactivated': '⏸️ DEACTIVATED',
    }
    return status_map.get(status, f'❓ {status.upper()}')

def format_time(timestamp):
    """Format timestamp"""
    if not timestamp:
        return 'N/A'
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return timestamp

print("═══════════════════════════════════════════════════════════════")
print("📊 RENDER DEPLOYMENT STATUS CHECK")
print("═══════════════════════════════════════════════════════════════")
print(f"Service ID: {RENDER_SERVICE_ID}")
print()

# Get service info
service = get_service_info()
if service:
    print("📋 SERVICE INFO:")
    print(f"   Name: {service.get('name', 'N/A')}")
    print(f"   Type: {service.get('type', 'N/A')}")
    print(f"   Region: {service.get('region', 'N/A')}")
    print(f"   Plan: {service.get('planId', service.get('plan', 'N/A'))}")
    if 'serviceDetails' in service:
        details = service['serviceDetails']
        if 'url' in details:
            print(f"   URL: {details['url']}")
    elif 'url' in service:
        print(f"   URL: {service['url']}")
    print()

# Get latest deployment
deploy = get_latest_deploy()
if deploy:
    print("🚀 LATEST DEPLOYMENT:")
    status = deploy.get('status', 'unknown')
    print(f"   Status: {format_status(status)}")
    print(f"   Created: {format_time(deploy.get('createdAt'))}")
    print(f"   Finished: {format_time(deploy.get('finishedAt'))}")
    
    if 'commit' in deploy:
        commit = deploy['commit']
        print(f"   Commit: {commit.get('id', 'N/A')[:8]} - {commit.get('message', 'N/A')[:50]}")
    
    if 'build' in deploy:
        build = deploy['build']
        print(f"   Build ID: {build.get('id', 'N/A')}")
        if 'logs' in build:
            print(f"   Build Logs: {build['logs']}")
    
    print()
    
    # Show build progress if building
    if status in ['build_in_progress', 'update_in_progress']:
        print("⏳ Deployment in progress...")
        print("   Check dashboard for live logs:")
        print(f"   https://dashboard.render.com/web/{RENDER_SERVICE_ID}")
    elif status == 'live':
        print("✅ Deployment successful!")
        if service and 'service' in service and 'serviceDetails' in service['service']:
            url = service['service']['serviceDetails'].get('url')
            if url:
                print(f"   Test: curl {url}/health")
    elif status in ['build_failed', 'update_failed']:
        print("❌ Deployment failed!")
        print("   Check logs in dashboard:")
        print(f"   https://dashboard.render.com/web/{RENDER_SERVICE_ID}/events")
else:
    print("⚠️  No deployments found")

print()
print("═══════════════════════════════════════════════════════════════")


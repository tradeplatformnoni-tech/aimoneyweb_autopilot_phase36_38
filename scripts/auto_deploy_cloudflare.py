#!/usr/bin/env python3
"""
Automated Cloudflare Worker Deployment via API
Deploys NeoLight API proxy to Cloudflare Workers
"""
import os
import sys
import json
import requests
from pathlib import Path

# Configuration
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
ROOT = Path(__file__).parent.parent

def get_headers():
    if not CLOUDFLARE_API_TOKEN:
        raise ValueError("CLOUDFLARE_API_TOKEN environment variable not set")
    return {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/javascript"
    }

def get_worker_code(render_url):
    """Get the Cloudflare Worker code with Render URL filled in"""
    worker_file = ROOT / "cloudflare_worker_ready.js"
    if not worker_file.exists():
        raise FileNotFoundError(f"Worker code file not found: {worker_file}")
    
    with open(worker_file) as f:
        code = f.read()
    
    # Replace RENDER_URL placeholder
    code = code.replace("YOUR_RENDER_SERVICE_URL.onrender.com", render_url)
    code = code.replace("'YOUR_RENDER_SERVICE_URL.onrender.com'", f"'{render_url}'")
    
    return code

def create_or_update_worker(worker_name, code):
    """Create or update Cloudflare Worker"""
    headers = get_headers()
    
    if not CLOUDFLARE_ACCOUNT_ID:
        raise ValueError("CLOUDFLARE_ACCOUNT_ID environment variable not set")
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{worker_name}"
    
    print(f"🚀 Deploying Cloudflare Worker '{worker_name}'...")
    
    # Try to update first (if exists)
    response = requests.put(
        url,
        headers=headers,
        data=code
    )
    
    if response.status_code == 200:
        print(f"✅ Worker updated successfully")
        return True
    
    # If update fails, try to create
    if response.status_code == 404:
        print(f"  Worker doesn't exist, creating new one...")
        # For creation, we need to use a different endpoint
        create_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts"
        response = requests.put(
            create_url,
            headers=headers,
            data=code,
            params={"name": worker_name}
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Worker created successfully")
            return True
    
    # Error
    error = response.text
    print(f"❌ Failed to deploy worker: {error}")
    raise Exception(f"Failed to deploy worker: {error}")

def add_scheduled_event(worker_name, cron_expression="*/10 * * * *"):
    """Add scheduled event (cron trigger) to worker"""
    
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    if not CLOUDFLARE_ACCOUNT_ID:
        raise ValueError("CLOUDFLARE_ACCOUNT_ID environment variable not set")
    
    # Create scheduled event
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{worker_name}/schedules"
    
    payload = {
        "cron": cron_expression
    }
    
    print(f"📅 Adding scheduled event (every 10 minutes)...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code in [200, 201]:
        print(f"✅ Scheduled event added")
        return True
    elif response.status_code == 409:
        print(f"  ℹ️  Scheduled event already exists")
        return True
    else:
        error = response.text
        print(f"⚠️  Warning: Failed to add scheduled event: {error}")
        print(f"  You can add it manually in Cloudflare dashboard")
        return False

def main():
    print("=" * 60)
    print("🚀 Automated Cloudflare Worker Deployment")
    print("=" * 60)
    print()
    
    # Check API credentials
    if not CLOUDFLARE_API_TOKEN:
        print("❌ ERROR: CLOUDFLARE_API_TOKEN not set")
        print()
        print("To get your API token:")
        print("  1. Go to: https://dash.cloudflare.com/profile/api-tokens")
        print("  2. Create Token → Edit Cloudflare Workers")
        print("  3. Run: export CLOUDFLARE_API_TOKEN='your_token_here'")
        sys.exit(1)
    
    if not CLOUDFLARE_ACCOUNT_ID:
        print("❌ ERROR: CLOUDFLARE_ACCOUNT_ID not set")
        print()
        print("To get your Account ID:")
        print("  1. Go to: https://dash.cloudflare.com")
        print("  2. Select your account")
        print("  3. Right sidebar → Account ID")
        print("  4. Run: export CLOUDFLARE_ACCOUNT_ID='your_account_id'")
        sys.exit(1)
    
    # Get Render URL
    render_url = os.getenv("RENDER_SERVICE_URL")
    if not render_url:
        # Try to read from service info file
        service_info_file = ROOT / "run" / "render_service_info.json"
        if service_info_file.exists():
            with open(service_info_file) as f:
                service_info = json.load(f)
                render_url = service_info.get("service_url", "").replace("https://", "").replace("http://", "")
        
        if not render_url:
            print("⚠️  RENDER_SERVICE_URL not set")
            print("   Please provide your Render service URL (without https://)")
            render_url = input("Render service URL (e.g., neolight-primary.onrender.com): ").strip()
    
    if not render_url:
        print("❌ ERROR: Render service URL is required")
        sys.exit(1)
    
    # Remove https:// if present
    render_url = render_url.replace("https://", "").replace("http://", "")
    
    worker_name = "neolight-api"
    
    try:
        # Get worker code
        print(f"📄 Reading worker code...")
        code = get_worker_code(render_url)
        print(f"  ✅ Code prepared (Render URL: {render_url})")
        
        # Deploy worker
        print()
        create_or_update_worker(worker_name, code)
        
        # Add scheduled event
        print()
        add_scheduled_event(worker_name)
        
        # Output results
        print()
        print("=" * 60)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 60)
        print()
        print(f"Worker Name: {worker_name}")
        print(f"Worker URL: https://{worker_name}.YOUR_SUBDOMAIN.workers.dev")
        print(f"Render URL: {render_url}")
        print()
        print("📋 Next Steps:")
        print("  1. Test the worker:")
        print(f"     curl https://{worker_name}.YOUR_SUBDOMAIN.workers.dev/health")
        print("  2. Start orchestrator: bash scripts/cloud_orchestrator.sh start")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ DEPLOYMENT FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check your CLOUDFLARE_API_TOKEN is valid")
        print("  2. Verify CLOUDFLARE_ACCOUNT_ID is correct")
        print("  3. Ensure you have Workers permissions")
        sys.exit(1)

if __name__ == "__main__":
    main()


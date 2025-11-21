#!/usr/bin/env python3
"""
Automated Cloudflare Worker Deployment
Deploys NeoLight keep-alive worker to Cloudflare
"""
import os
import sys
import json
import requests
from pathlib import Path

# Configuration
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
RENDER_SERVICE_URL = os.getenv("RENDER_SERVICE_URL", "").replace("https://", "").replace("http://", "").rstrip("/")
ROOT = Path(__file__).parent.parent
WORKER_NAME = "neolight-keepalive"
WORKER_FILE = ROOT / "cloudflare_worker_keepalive_sw.js"  # Use service worker format

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"

def get_headers():
    if not CLOUDFLARE_API_TOKEN:
        raise ValueError("CLOUDFLARE_API_TOKEN environment variable not set")
    return {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/javascript"
    }

def read_worker_code():
    """Read and prepare worker code"""
    if not WORKER_FILE.exists():
        raise FileNotFoundError(f"Worker file not found: {WORKER_FILE}")
    
    with open(WORKER_FILE, 'r') as f:
        code = f.read()
    
    # Replace placeholder with actual Render URL
    if RENDER_SERVICE_URL:
        code = code.replace("YOUR_RENDER_SERVICE_URL.onrender.com", RENDER_SERVICE_URL)
        print(f"✅ Updated Render URL to: {RENDER_SERVICE_URL}")
    else:
        print("⚠️  WARNING: RENDER_SERVICE_URL not set. Worker will use placeholder URL.")
        print("   Set it with: export RENDER_SERVICE_URL='https://your-service.onrender.com'")
    
    return code

def check_existing_worker():
    """Check if worker already exists"""
    headers = get_headers()
    response = requests.get(
        f"{CLOUDFLARE_API_BASE}/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{WORKER_NAME}",
        headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    )
    return response.status_code == 200

def deploy_worker():
    """Deploy worker to Cloudflare"""
    if not CLOUDFLARE_ACCOUNT_ID:
        raise ValueError("CLOUDFLARE_ACCOUNT_ID environment variable not set")
    
    worker_code = read_worker_code()
    
    # Cloudflare Workers API - use simple PUT for service worker format
    print(f"🚀 Deploying worker '{WORKER_NAME}'...")
    
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/javascript"
    }
    
    response = requests.put(
        f"{CLOUDFLARE_API_BASE}/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{WORKER_NAME}",
        headers=headers,
        data=worker_code
    )
    
    if response.status_code not in [200, 201]:
        error = response.text
        print(f"❌ Failed to deploy worker: {error}")
        raise Exception(f"Failed to deploy worker: {error}")
    
    print(f"✅ Worker deployed successfully")
    
    # Get worker route (URL)
    route_response = requests.get(
        f"{CLOUDFLARE_API_BASE}/accounts/{CLOUDFLARE_ACCOUNT_ID}/workers/scripts/{WORKER_NAME}/routes",
        headers={"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    )
    
    worker_url = f"https://{WORKER_NAME}.{CLOUDFLARE_ACCOUNT_ID}.workers.dev"
    
    return worker_url

def main():
    print("=" * 60)
    print("🚀 Automated Cloudflare Worker Deployment")
    print("=" * 60)
    print()
    
    # Check credentials
    if not CLOUDFLARE_API_TOKEN:
        print("❌ ERROR: CLOUDFLARE_API_TOKEN not set")
        print()
        print("To get your API token:")
        print("  1. Go to: https://dash.cloudflare.com/profile/api-tokens")
        print("  2. Create API Token with 'Workers:Edit' permission")
        print("  3. Run: export CLOUDFLARE_API_TOKEN='your_token_here'")
        sys.exit(1)
    
    if not CLOUDFLARE_ACCOUNT_ID:
        print("❌ ERROR: CLOUDFLARE_ACCOUNT_ID not set")
        print()
        print("To get your Account ID:")
        print("  1. Go to: https://dash.cloudflare.com")
        print("  2. Select your account")
        print("  3. Copy Account ID from right sidebar")
        print("  4. Run: export CLOUDFLARE_ACCOUNT_ID='your_account_id'")
        sys.exit(1)
    
    # Check if Render URL is set
    if not RENDER_SERVICE_URL:
        print("⚠️  WARNING: RENDER_SERVICE_URL not set")
        print("   Worker will be deployed but will use placeholder URL")
        print("   Set it with: export RENDER_SERVICE_URL='https://your-service.onrender.com'")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Deployment cancelled")
            sys.exit(0)
    
    try:
        # Deploy worker
        worker_url = deploy_worker()
        
        # Output results
        print()
        print("=" * 60)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 60)
        print()
        print(f"Worker Name: {WORKER_NAME}")
        print(f"Worker URL: {worker_url}")
        print()
        print("📋 Test your worker:")
        print(f"  curl {worker_url}/keepalive")
        print(f"  curl {worker_url}/health")
        print()
        print("📋 Next Steps:")
        print("  1. Test the keep-alive endpoint:")
        print(f"     curl {worker_url}/keepalive")
        print("  2. Start orchestrator:")
        print("     bash scripts/cloud_orchestrator.sh start")
        print()
        
        # Save to file
        output_file = ROOT / "run" / "cloudflare_worker_info.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump({
                "worker_name": WORKER_NAME,
                "worker_url": worker_url,
                "render_service_url": RENDER_SERVICE_URL or "NOT_SET"
            }, f, indent=2)
        print(f"💾 Worker info saved to: {output_file}")
        
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
        print("  3. Ensure token has 'Workers:Edit' permission")
        print("  4. Check Cloudflare API status: https://www.cloudflarestatus.com")
        sys.exit(1)

if __name__ == "__main__":
    main()

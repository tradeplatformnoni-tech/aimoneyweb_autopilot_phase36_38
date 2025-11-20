#!/usr/bin/env python3
"""
Automated Render Deployment via API
Deploys NeoLight to Render using Render API
"""
import os
import sys
import json
import requests
import time
from pathlib import Path

# Configuration
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_API_BASE = "https://api.render.com/v1"
ROOT = Path(__file__).parent.parent

def get_headers():
    if not RENDER_API_KEY:
        raise ValueError("RENDER_API_KEY environment variable not set")
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {RENDER_API_KEY}",
        "Content-Type": "application/json"
    }

def get_owner_id():
    """Get the owner ID (user or team)"""
    headers = get_headers()
    response = requests.get(f"{RENDER_API_BASE}/owners", headers=headers)
    response.raise_for_status()
    owners = response.json()
    if not owners:
        raise ValueError("No owners found. Please check your API key.")
    # Use first owner (usually the user)
    return owners[0]["owner"]["id"]

def check_existing_service(service_name):
    """Check if service already exists"""
    headers = get_headers()
    owner_id = get_owner_id()
    response = requests.get(
        f"{RENDER_API_BASE}/services",
        headers=headers,
        params={"ownerId": owner_id}
    )
    response.raise_for_status()
    services = response.json()
    for service in services:
        if service.get("service", {}).get("name") == service_name:
            return service["service"]["id"]
    return None

def create_render_service(service_name, repo_url=None):
    """Create a new Render web service"""
    headers = get_headers()
    owner_id = get_owner_id()
    
    # Check if service exists
    existing_id = check_existing_service(service_name)
    if existing_id:
        print(f"✅ Service '{service_name}' already exists (ID: {existing_id})")
        return existing_id
    
    # Service configuration
    service_config = {
        "type": "web_service",
        "name": service_name,
        "ownerId": owner_id,
        "planId": "free",  # Free tier
        "region": "oregon",  # us-west-2
        "serviceDetails": {
            "runtime": "python",
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "python3 trader/smart_trader.py",
            "healthCheckPath": "/health",
            "envVars": [
                {"key": "TRADING_MODE", "value": "PAPER_TRADING_MODE"},
                {"key": "PYTHONPATH", "value": "/opt/render/project/src"},
                {"key": "PORT", "value": "8080"},
                {"key": "RENDER_MODE", "value": "true"},
            ]
        }
    }
    
    # Add repo if provided
    if repo_url:
        service_config["repo"] = repo_url
    
    print(f"🚀 Creating Render service '{service_name}'...")
    response = requests.post(
        f"{RENDER_API_BASE}/services",
        headers=headers,
        json=service_config
    )
    
    if response.status_code == 201:
        service = response.json()["service"]
        service_id = service["id"]
        print(f"✅ Service created successfully (ID: {service_id})")
        return service_id
    else:
        error = response.text
        print(f"❌ Failed to create service: {error}")
        if "already exists" in error.lower():
            # Try to find existing service
            existing_id = check_existing_service(service_name)
            if existing_id:
                print(f"✅ Found existing service (ID: {existing_id})")
                return existing_id
        raise Exception(f"Failed to create service: {error}")

def add_env_vars(service_id, env_vars):
    """Add environment variables to service"""
    headers = get_headers()
    
    for key, value in env_vars.items():
        print(f"  Setting {key}...")
        response = requests.post(
            f"{RENDER_API_BASE}/services/{service_id}/env-vars",
            headers=headers,
            json={"key": key, "value": value}
        )
        if response.status_code not in [200, 201]:
            print(f"  ⚠️  Warning: Failed to set {key}: {response.text}")

def get_service_info(service_id):
    """Get service information including URL"""
    headers = get_headers()
    response = requests.get(
        f"{RENDER_API_BASE}/services/{service_id}",
        headers=headers
    )
    response.raise_for_status()
    return response.json()["service"]

def main():
    print("=" * 60)
    print("🚀 Automated Render Deployment")
    print("=" * 60)
    print()
    
    # Check API key
    if not RENDER_API_KEY:
        print("❌ ERROR: RENDER_API_KEY not set")
        print()
        print("To get your API key:")
        print("  1. Go to: https://dashboard.render.com")
        print("  2. Account Settings → API Keys")
        print("  3. Create API Key")
        print("  4. Run: export RENDER_API_KEY='your_key_here'")
        sys.exit(1)
    
    # Service name
    service_name = "neolight-primary"
    
    # Environment variables from .env file
    env_vars = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        print(f"📄 Reading environment variables from .env...")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Only include relevant vars
                    if key in ["ALPACA_API_KEY", "ALPACA_SECRET_KEY", "RCLONE_REMOTE", "RCLONE_PATH"]:
                        env_vars[key] = value
        print(f"  ✅ Found {len(env_vars)} environment variables")
    else:
        print("⚠️  .env file not found. You'll need to add env vars manually in Render dashboard.")
    
    try:
        # Create service
        service_id = create_render_service(service_name)
        
        # Add environment variables
        if env_vars:
            print()
            print("📝 Adding environment variables...")
            add_env_vars(service_id, env_vars)
        
        # Get service info
        print()
        print("📊 Getting service information...")
        service_info = get_service_info(service_id)
        
        # Output results
        print()
        print("=" * 60)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 60)
        print()
        print(f"Service ID: {service_id}")
        print(f"Service Name: {service_info.get('name', service_name)}")
        print(f"Service URL: {service_info.get('serviceDetails', {}).get('url', 'N/A')}")
        print()
        print("📋 Next Steps:")
        print("  1. Add this to your environment:")
        print(f"     export RENDER_SERVICE_ID=\"{service_id}\"")
        print("  2. Connect your GitHub repo in Render dashboard:")
        print("     https://dashboard.render.com")
        print("  3. Deploy Cloudflare Worker")
        print("  4. Start orchestrator: bash scripts/cloud_orchestrator.sh start")
        print()
        
        # Save to file
        output_file = ROOT / "run" / "render_service_info.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump({
                "service_id": service_id,
                "service_name": service_name,
                "service_url": service_info.get("serviceDetails", {}).get("url", ""),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, indent=2)
        print(f"💾 Service info saved to: {output_file}")
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ DEPLOYMENT FAILED")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check your RENDER_API_KEY is valid")
        print("  2. Verify you have permission to create services")
        print("  3. Check Render API status: https://status.render.com")
        sys.exit(1)

if __name__ == "__main__":
    main()



#!/usr/bin/env python3
"""
Monitor Self-Healing System - Free Monitoring Solution
=======================================================
Checks if self-healing system is working using observability endpoints
"""

import os
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

RENDER_URL = os.getenv("RENDER_URL", "https://neolight-autopilot-python.onrender.com")

def check_self_healing_components():
    """Check if self-healing components are working (FREE)."""
    print("🔍 Checking self-healing system...")
    print("")
    
    all_healthy = True
    
    # Check observability endpoints (free, already working)
    endpoints = {
        "Summary": "/observability/summary",
        "Predictions": "/observability/predictions",
        "Anomalies": "/observability/anomalies",
        "Metrics": "/observability/metrics",
    }
    
    for name, endpoint in endpoints.items():
        try:
            response = requests.get(f"{RENDER_URL}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {name}: Working (200 OK)")
                data = response.json()
                
                # Check if there's actual data
                if isinstance(data, dict):
                    if name == "Predictions" and data.get("high_risk"):
                        print(f"   Found {len(data.get('high_risk', {}))} high-risk predictions")
                    elif name == "Anomalies" and data.get("active", 0) > 0:
                        print(f"   Found {data.get('active', 0)} active anomalies")
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            all_healthy = False
    
    return all_healthy

def check_agent_health():
    """Check overall agent health (FREE)."""
    try:
        response = requests.get(f"{RENDER_URL}/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            agents_running = data.get("agents_running", 0)
            agents_total = data.get("agents_total", 0)
            
            print(f"")
            print(f"📊 System Health:")
            print(f"   Agents Running: {agents_running}/{agents_total}")
            
            if agents_running == agents_total:
                print(f"✅ All agents running!")
                return True
            else:
                print(f"⚠️  Some agents not running")
                return False
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Monitoring Self-Healing System")
    print("=" * 50)
    print("")
    
    component_check = check_self_healing_components()
    health_check = check_agent_health()
    
    print("")
    print("=" * 50)
    if component_check and health_check:
        print("✅ Self-healing system is working!")
        sys.exit(0)
    else:
        print("⚠️  Some components may need attention")
        sys.exit(1)


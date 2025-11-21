#!/usr/bin/env python3
"""
Performance Monitor - Free Monitoring Solution
===============================================
Monitors system performance using Prometheus metrics (free)
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

def check_prometheus_metrics():
    """Check Prometheus metrics endpoint (FREE)."""
    try:
        response = requests.get(f"{RENDER_URL}/metrics", timeout=10)
        
        if response.status_code == 200:
            metrics_text = response.text
            
            # Parse basic metrics
            metrics = {}
            for line in metrics_text.split('\n'):
                if line and not line.startswith('#'):
                    if ' ' in line:
                        name, value = line.rsplit(' ', 1)
                        try:
                            metrics[name] = float(value)
                        except ValueError:
                            continue
            
            print("📊 Performance Metrics:")
            if metrics:
                for name, value in list(metrics.items())[:10]:  # Show first 10
                    print(f"   {name}: {value}")
                print(f"   ... ({len(metrics)} total metrics)")
                return True
            else:
                print("   ⚠️  No metrics found (may be empty)")
                return True
        else:
            print(f"❌ Metrics endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error fetching metrics: {e}")
        return False

def check_response_times():
    """Check API endpoint response times (FREE)."""
    endpoints = [
        "/health",
        "/agents",
        "/observability/summary",
        "/api/trades",
    ]
    
    print("")
    print("⏱️  Response Times:")
    all_good = True
    
    for endpoint in endpoints:
        try:
            start = time.time()
            response = requests.get(f"{RENDER_URL}{endpoint}", timeout=10)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"   {status} {endpoint}: {elapsed:.0f}ms")
            
            if elapsed > 5000:  # 5 seconds
                print(f"      ⚠️  Slow response!")
                all_good = False
        except Exception as e:
            print(f"   ❌ {endpoint}: Error - {e}")
            all_good = False
    
    return all_good

if __name__ == "__main__":
    print("🔍 Performance Monitoring")
    print("=" * 50)
    print("")
    
    metrics_check = check_prometheus_metrics()
    response_check = check_response_times()
    
    print("")
    print("=" * 50)
    if metrics_check and response_check:
        print("✅ Performance monitoring successful!")
        sys.exit(0)
    else:
        print("⚠️  Some performance issues detected")
        sys.exit(1)


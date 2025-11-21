#!/usr/bin/env python3
"""
Trigger a test PAPER trade manually
This script forces a buy trade for testing purposes
"""

import json
import os
import sys
from pathlib import Path

import requests

# Add project root to path
ROOT = Path(os.path.expanduser("~/neolight"))
sys.path.insert(0, str(ROOT))


def trigger_test_trade():
    """Trigger a test PAPER trade by modifying signal thresholds temporarily"""

    print("🧪 Triggering Test PAPER Trade")
    print("=" * 50)
    print("")

    # Check if SmartTrader is running
    import subprocess

    result = subprocess.run(["pgrep", "-f", "smart_trader.py"], capture_output=True, text=True)
    if not result.stdout.strip():
        print("❌ SmartTrader is not running!")
        print("   Start it first: cd trader && python3 smart_trader.py")
        return False

    pid = result.stdout.strip().split("\n")[0]
    print(f"✅ SmartTrader running (PID: {pid})")

    # Check mode
    mode_file = ROOT / "state" / "trading_mode.json"
    if mode_file.exists():
        with open(mode_file) as f:
            mode_data = json.load(f)
        current_mode = mode_data.get("mode", "UNKNOWN")
        print(f"✅ Mode: {current_mode}")

        if current_mode != "PAPER_TRADING_MODE":
            print(f"⚠️  Warning: Mode is {current_mode}, not PAPER_TRADING_MODE")
    else:
        print("⚠️  Mode file not found")

    print("")
    print("📊 Strategy: Temporarily lowering RSI thresholds to trigger trade")
    print("")
    print("Option 1: Modify smart_trader.py temporarily")
    print("   This will lower RSI buy threshold from 45 to 60 (more aggressive)")
    print("   This makes it easier to trigger a BUY signal")
    print("")
    print("Option 2: Send test trade via API (if dashboard has endpoint)")
    print("")

    choice = input("Choose option (1 or 2, or 'q' to quit): ").strip()

    if choice == "1":
        print("")
        print("🔧 Modifying RSI thresholds temporarily...")

        # Read smart_trader.py
        trader_file = ROOT / "trader" / "smart_trader.py"
        if not trader_file.exists():
            print(f"❌ File not found: {trader_file}")
            return False

        with open(trader_file) as f:
            content = f.read()

        # Create backup
        backup_file = trader_file.with_suffix(".py.backup_test")
        with open(backup_file, "w") as f:
            f.write(content)
        print(f"✅ Backup created: {backup_file.name}")

        # Modify RSI thresholds temporarily
        # Find RSI buy condition (typically rsi < 45 or similar)
        # We'll make it more aggressive: rsi < 60

        modified = content

        # Look for RSI buy conditions in generate_signal
        # Common pattern: rsi < 45 or rsi_val < 45
        import re

        # Pattern 1: rsi < 45 or rsi_val < 45 -> change to < 60
        modified = re.sub(r"(rsi|rsi_val)\s*<\s*45", r"\1 < 60", modified)

        # Pattern 2: BUY_SIGNAL_RSI_THRESHOLD = 45 -> change to 60
        modified = re.sub(
            r"BUY_SIGNAL_RSI_THRESHOLD\s*=\s*45", "BUY_SIGNAL_RSI_THRESHOLD = 60", modified
        )

        # Write modified file
        with open(trader_file, "w") as f:
            f.write(modified)

        print("✅ Modified RSI buy threshold to 60 (more aggressive)")
        print("")
        print("⚠️  IMPORTANT: Restart SmartTrader for changes to take effect")
        print("")
        print("Commands:")
        print("  1. pkill -f smart_trader.py")
        print("  2. cd ~/neolight/trader")
        print(
            "  3. ALPACA_API_KEY=... ALPACA_API_SECRET=... NEOLIGHT_USE_ALPACA_QUOTES=true python3 smart_trader.py"
        )
        print("")
        print("After testing, restore backup:")
        print(f"  cp {backup_file} {trader_file}")

        return True

    elif choice == "2":
        print("")
        print("🔧 Checking for API endpoint...")

        # Try dashboard API
        try:
            dashboard_url = os.getenv("NEOLIGHT_DASHBOARD_URL", "http://localhost:8100")
            response = requests.get(f"{dashboard_url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Dashboard accessible: {dashboard_url}")
                print("")
                print("Note: API endpoint for manual trades not yet implemented")
                print("   Use Option 1 instead")
            else:
                print(f"⚠️  Dashboard returned: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Dashboard not accessible: {e}")
            print("   Use Option 1 instead")

        return False

    else:
        print("Cancelled")
        return False


if __name__ == "__main__":
    trigger_test_trade()

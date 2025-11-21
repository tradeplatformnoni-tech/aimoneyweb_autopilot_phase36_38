#!/usr/bin/env python3
"""
Trading Agent Diagnostics - Analyzes why trading agent isn't profitable
"""

import csv
import json
from pathlib import Path

ROOT = Path.home() / "neolight"
STATE = ROOT / "state"
LOGS = ROOT / "logs"
RUNTIME = ROOT / "runtime"


def analyze_pnl():
    """Analyze P&L history."""
    pnl_file = STATE / "pnl_history.csv"
    if not pnl_file.exists():
        print("❌ No PnL history found")
        return

    data = []
    with open(pnl_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)

    if not data:
        print("❌ PnL file is empty")
        return

    print(f"✅ Found {len(data)} PnL records")

    # Calculate statistics
    pnls = [float(d.get("pnl_pct", 0) or 0) for d in data if d.get("pnl_pct")]
    equities = [float(d.get("equity", 0) or 0) for d in data if d.get("equity")]

    if pnls:
        total_return = (
            equities[-1] / equities[0] - 1 if len(equities) > 1 and equities[0] > 0 else 0
        )
        avg_pnl = sum(pnls) / len(pnls)
        win_rate = len([p for p in pnls if p > 0]) / len(pnls)

        print("\n📊 Performance Analysis:")
        print(f"   Total Return: {total_return:.2%}")
        print(f"   Average Daily PnL: {avg_pnl:.4%}")
        print(f"   Win Rate: {win_rate:.2%}")
        print(f"   Starting Equity: ${equities[0]:,.2f}")
        print(f"   Current Equity: ${equities[-1]:,.2f}" if equities else "N/A")
    else:
        print("⚠️  No PnL data to analyze")


def check_trader_logs():
    """Check trader logs for errors."""
    log_file = LOGS / "smart_trader.log"
    if not log_file.exists():
        print("❌ No trader log found")
        return

    with open(log_file) as f:
        lines = f.readlines()

    print("\n📋 Trader Log Analysis (last 10 lines):")
    for line in lines[-10:]:
        print(f"   {line.rstrip()}")


def check_allocations():
    """Check if allocations are being used."""
    alloc_file = RUNTIME / "allocations_override.json"
    if alloc_file.exists():
        data = json.loads(alloc_file.read_text())
        print("\n✅ Allocations file exists:")
        print(f"   {json.dumps(data, indent=2)}")
    else:
        print("\n❌ No allocations file found - trader may not have signals")


def check_brain():
    """Check orchestrator brain state."""
    brain_file = RUNTIME / "atlas_brain.json"
    if brain_file.exists():
        data = json.loads(brain_file.read_text())
        print("\n🧠 Brain State:")
        print(f"   Risk Scaler: {data.get('risk_scaler', 'N/A')}")
        print(f"   Confidence: {data.get('confidence', 'N/A')}")
        print(f"   Updated: {data.get('updated', 'N/A')}")
    else:
        print("\n❌ No brain file found")


def diagnose_issues():
    """Main diagnostic function."""
    print("=" * 60)
    print("🔍 Trading Agent Diagnostics")
    print("=" * 60)

    analyze_pnl()
    check_allocations()
    check_brain()
    check_trader_logs()

    print("\n" + "=" * 60)
    print("💡 Recommendations:")
    print("=" * 60)
    print("1. Check if smart_trader.py has actual trading logic (not just sleep)")
    print("2. Verify allocations_override.json exists and has valid weights")
    print("3. Ensure orchestrator is updating risk_scaler and confidence")
    print("4. Check if broker (Alpaca/paper) is configured correctly")
    print("5. Verify market data feeds are working")
    print("=" * 60)


if __name__ == "__main__":
    diagnose_issues()

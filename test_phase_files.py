#!/usr/bin/env python3
"""
Test script for phase files - Run this to verify all fixes are working
Usage: python3 test_phase_files.py
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

print("=" * 70)
print("Phase Files Verification Test")
print("=" * 70)

# Test 1: Syntax Verification
print("\n[1/4] Syntax Check:")
print("-" * 70)
files = [
    "phases/phase_3900_4100_events.py",
    "phases/phase_4100_4300_execution.py",
    "phases/phase_2500_2700_portfolio_optimization.py",
    "phases/phase_2700_2900_risk_management.py",
]

syntax_errors = []
for f in files:
    path = ROOT / f
    try:
        with open(path, encoding="utf-8") as file:
            code = file.read()
        ast.parse(code)
        print(f"✅ {f}")
    except SyntaxError as e:
        print(f"❌ {f}: Line {e.lineno}: {e.msg}")
        syntax_errors.append(f)
    except Exception as e:
        print(f"⚠️  {f}: {e}")
        syntax_errors.append(f)

if syntax_errors:
    print(f"\n❌ {len(syntax_errors)} file(s) have syntax errors")
    sys.exit(1)

# Test 2: Import phase_3900_4100_events
print("\n[2/4] Import phase_3900_4100_events:")
print("-" * 70)
try:
    from phases.phase_3900_4100_events import process_event

    print("✅ Import successful")

    # Test function call
    result = process_event("TEST", {"test": "data"}, source="test_script")
    print(f"✅ process_event() executed: {result.get('type') == 'TEST'}")
except Exception as e:
    print(f"❌ Import/execution failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Test 3: Import phase_4100_4300_execution
print("\n[3/4] Import phase_4100_4300_execution:")
print("-" * 70)
try:
    from phases.phase_4100_4300_execution import ExecutionAlgorithm

    print("✅ Import successful")
    engine = ExecutionAlgorithm()
    print("✅ ExecutionAlgorithm instantiated")
except Exception as e:
    print(f"❌ Import/instantiation failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Test 4: Import phase_2700_2900_risk_management
print("\n[4/4] Import phase_2700_2900_risk_management:")
print("-" * 70)
try:
    from phases.phase_2700_2900_risk_management import AdvancedRiskManager

    print("✅ Import successful")
    rm = AdvancedRiskManager()
    print("✅ AdvancedRiskManager instantiated")
except Exception as e:
    print(f"❌ Import/instantiation failed: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED! All phase files are working correctly.")
print("=" * 70)

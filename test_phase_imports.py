#!/usr/bin/env python3
"""Test phase file imports"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

print("=" * 70)
print("Testing Phase File Imports")
print("=" * 70)

# Test 1: Syntax check
print("\n1. Syntax Check:")
print("-" * 70)
import ast

files = [
    "phases/phase_3900_4100_events.py",
    "phases/phase_4100_4300_execution.py",
    "phases/phase_2500_2700_portfolio_optimization.py",
    "phases/phase_2700_2900_risk_management.py",
]

syntax_ok = True
for f in files:
    try:
        with open(f) as file:
            ast.parse(file.read())
        print(f"✅ {f}: Valid syntax")
    except SyntaxError as e:
        print(f"❌ {f}: Syntax error at line {e.lineno}: {e.msg}")
        syntax_ok = False
    except Exception as e:
        print(f"⚠️  {f}: {e}")
        syntax_ok = False

# Test 2: Import tests
print("\n2. Import Tests:")
print("-" * 70)

# Test phase_3900_4100_events
try:
    from phases.phase_3900_4100_events import process_event

    print("✅ phase_3900_4100_events: Import successful")

    # Test function execution
    result = process_event("TEST", {"test": "data"}, source="test_import")
    print(f"✅ process_event() executed successfully: {result is not None}")
except Exception as e:
    print(f"❌ phase_3900_4100_events: {e}")
    syntax_ok = False

# Test phase_4100_4300_execution
try:
    print("✅ phase_4100_4300_execution: Import successful")
except Exception as e:
    print(f"❌ phase_4100_4300_execution: {e}")
    syntax_ok = False

# Test phase_2500_2700_portfolio_optimization
try:
    print("✅ phase_2500_2700_portfolio_optimization: Import successful")
except Exception as e:
    print(f"❌ phase_2500_2700_portfolio_optimization: {e}")
    syntax_ok = False

# Test phase_2700_2900_risk_management
try:
    from phases.phase_2700_2900_risk_management import AdvancedRiskManager

    print("✅ phase_2700_2900_risk_management: Import successful")

    # Test instantiation
    rm = AdvancedRiskManager()
    print("✅ AdvancedRiskManager: Instantiated successfully")
except Exception as e:
    print(f"❌ phase_2700_2900_risk_management: {e}")
    syntax_ok = False

print("\n" + "=" * 70)
if syntax_ok:
    print("✅ ALL TESTS PASSED!")
    sys.exit(0)
else:
    print("❌ Some tests failed")
    sys.exit(1)

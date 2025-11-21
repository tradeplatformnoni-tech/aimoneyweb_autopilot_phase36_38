#!/usr/bin/env python3
"""Verify phase files syntax"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent
files = [
    "phases/phase_3900_4100_events.py",
    "phases/phase_4100_4300_execution.py",
    "phases/phase_2500_2700_portfolio_optimization.py",
    "phases/phase_2700_2900_risk_management.py",
]

print("=" * 70)
print("Phase Files Syntax Verification")
print("=" * 70)

errors = []
for f in files:
    path = ROOT / f
    if not path.exists():
        print(f"❌ {f}: File not found")
        errors.append(f)
        continue

    try:
        with open(path, encoding="utf-8") as file:
            code = file.read()
        ast.parse(code)
        print(f"✅ {f}")
    except SyntaxError as e:
        print(f"❌ {f}: Line {e.lineno}: {e.msg}")
        if e.text:
            print(f"   Code: {e.text.strip()}")
        errors.append(f)
    except Exception as e:
        print(f"⚠️  {f}: {type(e).__name__}: {e}")
        errors.append(f)

print("=" * 70)
if errors:
    print(f"❌ {len(errors)} file(s) have errors")
    sys.exit(1)
else:
    print(f"✅ All {len(files)} files have valid syntax!")
    sys.exit(0)

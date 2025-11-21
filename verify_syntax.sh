#!/bin/bash
# Clean syntax verification script (bypasses shell environment issues)
cd "$(dirname "$0")"

python3 << 'PYTHON_SCRIPT'
import ast
import sys

files = [
    'phases/phase_3900_4100_events.py',
    'phases/phase_4100_4300_execution.py',
    'phases/phase_2500_2700_portfolio_optimization.py',
    'phases/phase_2700_2900_risk_management.py'
]

print("=" * 70)
print("Phase Files Syntax Verification")
print("=" * 70)

errors = []
for f in files:
    try:
        with open(f) as file:
            ast.parse(file.read())
        print(f"✅ {f}")
    except SyntaxError as e:
        print(f"❌ {f}: Line {e.lineno}: {e.msg}")
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
PYTHON_SCRIPT


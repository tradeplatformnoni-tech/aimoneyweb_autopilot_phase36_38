#!/usr/bin/env python3
"""Direct phase check that bypasses shell issues."""

import os
import sys

# Set up paths
os.chdir(os.path.expanduser("~/neolight"))
sys.path.insert(0, os.path.expanduser("~/neolight"))

# Import and run the check script
from check_and_enable_phases import main

if __name__ == "__main__":
    try:
        missing = main()
        if missing:
            print(f"\n⚠️  {len(missing)} phases need to be started")
            sys.exit(1)
        else:
            print("\n✅ All phases are running")
            sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)

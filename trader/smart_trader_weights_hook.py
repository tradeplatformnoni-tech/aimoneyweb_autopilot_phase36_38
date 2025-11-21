#!/usr/bin/env python3
import json
import os
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
RUNTIME = ROOT / "runtime"
ALLOC = RUNTIME / "allocations_override.json"


def load_weights() -> dict:
    if ALLOC.exists():
        try:
            data = json.loads(ALLOC.read_text())
            alloc = data.get("allocations", {})
            if alloc:
                total = sum(alloc.values())
                norm = {k: v / total for k, v in alloc.items()}
                print("🎯 Imported strategy weights:", norm)
                return norm
        except Exception as e:
            print("⚠️ Failed to load weights:", e)
    return {}


if __name__ == "__main__":
    load_weights()

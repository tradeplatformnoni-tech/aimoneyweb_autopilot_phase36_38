#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
RUNTIME = ROOT / "runtime"
STATE = ROOT / "state"
RUNTIME.mkdir(exist_ok=True, parents=True)

SRC = RUNTIME / "strategy_weights.json"  # written by Strategy Lab
OUT = RUNTIME / "allocations_override.json"  # what trader/intel can read


def normalize(weights: dict) -> dict:
    # keep only positives, sum1, cap per-asset 0.35, min 0.02
    filt = {k: max(0.0, float(v)) for k, v in weights.items()}
    s = sum(filt.values())
    if s <= 0:
        return {}
    norm = {k: v / s for k, v in filt.items()}
    # soft caps
    norm = {k: max(0.02, min(0.35, v)) for k, v in norm.items()}
    s2 = sum(norm.values())
    return {k: v / s2 for k, v in norm.items()}


def main():
    last = ""
    # Check for portfolio optimizer allocations (Phase 2500-2700)
    alloc_file = STATE / "allocations.json"
    # Check for RL strategy weights (Phase 3700-3900)
    rl_weights_file = RUNTIME / "rl_strategy_weights.json"

    while True:
        # Priority 0: Check RL strategy weights (if available) - Phase 3700-3900
        if rl_weights_file.exists():
            try:
                rl_data = json.loads(rl_weights_file.read_text())
                rl_weights = rl_data.get("weights", {})
                if rl_weights and rl_data.get("model_loaded", False):
                    # RL weights are strategy weights, convert to symbol allocations if needed
                    # For now, use as-is (strategies will use these weights)
                    alloc = normalize(rl_weights)
                    if alloc:
                        OUT.write_text(
                            json.dumps(
                                {
                                    "allocations": alloc,
                                    "source": "rl_inference",
                                    "timestamp": rl_data.get("timestamp", ""),
                                    "metadata": rl_data.get("metadata", {}),
                                },
                                indent=2,
                            )
                        )
                        print(
                            "✅ allocations_override.json updated from RL inference:",
                            alloc,
                            flush=True,
                        )
                        time.sleep(5)
                        continue
            except Exception as e:
                print(f"⚠️ RL weights parse error: {e}", flush=True)

        # Priority 1: Check portfolio optimizer allocations (if available)
        if alloc_file.exists():
            try:
                opt_data = json.loads(alloc_file.read_text())
                opt_weights = opt_data.get("weights", {})
                if opt_weights:
                    alloc = normalize(opt_weights)
                    if alloc:
                        OUT.write_text(
                            json.dumps(
                                {
                                    "allocations": alloc,
                                    "source": "portfolio_optimizer",
                                    "method": opt_data.get("method", "sharpe"),
                                    "timestamp": opt_data.get("timestamp", ""),
                                },
                                indent=2,
                            )
                        )
                        print(
                            "✅ allocations_override.json updated from optimizer:",
                            alloc,
                            flush=True,
                        )
                        time.sleep(5)
                        continue
            except Exception as e:
                print(f"⚠️ portfolio optimizer parse error: {e}", flush=True)

        # Priority 2: Check strategy lab weights (fallback)
        if SRC.exists():
            txt = SRC.read_text()
            if txt != last:
                last = txt
                try:
                    data = json.loads(txt)
                    weights = data.get("weights") if "weights" in data else data
                    alloc = normalize(weights or {})
                    if alloc:
                        OUT.write_text(
                            json.dumps({"allocations": alloc, "source": "strategy_lab"}, indent=2)
                        )
                        print(
                            "✅ allocations_override.json updated from strategy_lab:",
                            alloc,
                            flush=True,
                        )
                except Exception as e:
                    print("⚠️ weights_bridge parse error:", e, flush=True)
        time.sleep(5)


if __name__ == "__main__":
    main()

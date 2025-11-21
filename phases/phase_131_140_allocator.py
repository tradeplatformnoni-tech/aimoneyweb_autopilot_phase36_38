#!/usr/bin/env python3
import datetime as dt
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
RUNTIME.mkdir(exist_ok=True)
LOGS = ROOT / "logs"
LOGS.mkdir(exist_ok=True)
STATE = RUNTIME / "atlas_learning.json"
GUARD = RUNTIME / "risk_gate.json"
ALLOC = RUNTIME / "allocator_plan.json"
LOG = LOGS / "allocator.log"

SYMBOLS = ["BTC/USD", "ETH/USD", "USDT/USD"]


def log(msg):
    line = f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}\n"
    with open(LOG, "a") as f:
        f.write(line)
    print(line, end="", flush=True)


def jload(p, default=None):
    try:
        return json.loads(pathlib.Path(p).read_text())
    except:
        return default


def jdump(p, obj):
    pathlib.Path(p).write_text(json.dumps(obj, indent=2))


def main():
    log("📐 Allocator online")
    while True:
        time.sleep(15)
        st = jload(STATE, {})
        rg = jload(GUARD, {})

        rf = float(st.get("risk_factor", 1.0))
        max_pct = float(rg.get("max_pct_risk", 0.008))  # from governor
        phase = rg.get("phase", "NORMAL")
        halt = jload(ROOT / "runtime/drawdown_state.json", {}).get("halt", False)

        # Base weights: conservative tilt to majors; adapt slightly by risk factor
        base = {"BTC/USD": 0.5, "ETH/USD": 0.4, "USDT/USD": 0.1}
        # Slightly tilt to BTC when risk>1, to USDT when risk<1
        adj = (rf - 1.0) * 0.1
        base["BTC/USD"] = max(0.3, min(0.6, base["BTC/USD"] + adj))
        base["USDT/USD"] = max(0.05, min(0.2, base["USDT/USD"] - adj))
        base["ETH/USD"] = 1.0 - base["BTC/USD"] - base["USDT/USD"]

        # If halted, allocate all to USDT (flat)
        if halt:
            plan = {s: (0.0 if s != "USDT/USD" else 1.0) for s in SYMBOLS}
            px = {"max_pct_risk": 0.0, "phase": "HALTED", "weights": plan}
        else:
            px = {"max_pct_risk": round(max_pct, 6), "phase": phase, "weights": base}

        jdump(ALLOC, px)
        log(f"🧭 Phase={px['phase']} risk={px['max_pct_risk']} weights={px['weights']}")


if __name__ == "__main__":
    main()

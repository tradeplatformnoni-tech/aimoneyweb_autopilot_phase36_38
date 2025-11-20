#!/usr/bin/env python3
import datetime as dt
import json
import os
import pathlib
import random
import time
import traceback

ROOT = os.path.expanduser("~/neolight")
ROOT_PATH = pathlib.Path(ROOT)
STATE = ROOT_PATH / "state"
RUNTIME = ROOT_PATH / "runtime"
LOGS = ROOT_PATH / "logs"
STATE.mkdir(parents=True, exist_ok=True)
RUNTIME.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

INTERVAL_SECONDS = int(os.getenv("NEOLIGHT_ORCH_INTERVAL", "300"))


def update_brain_once() -> dict:
    brain = {
        "risk_scaler": round(random.uniform(0.4, 1.2), 3),
        "confidence": round(random.uniform(0.05, 0.9), 3),
        "updated": dt.datetime.utcnow().isoformat() + "Z",
    }
    (RUNTIME / "atlas_brain.json").write_text(json.dumps(brain, indent=2))
    # lightweight summary for dashboard/diagnostics
    summary = {
        "ts": brain["updated"],
        "note": "orchestrator heartbeat",
        "risk_scaler": brain["risk_scaler"],
        "confidence": brain["confidence"],
    }
    (STATE / "intelligence_summary.json").write_text(json.dumps(summary, indent=2))
    print("🧠 Orchestrator updated brain:", brain, flush=True)
    return brain


def main() -> None:
    print(
        f"[orchestrator] service loop start @ {dt.datetime.utcnow().isoformat()}Z; interval={INTERVAL_SECONDS}s",
        flush=True,
    )
    while True:
        try:
            update_brain_once()
        except Exception as e:
            # Fail fast but keep the service alive; Guardian will see logs
            err = f"[orchestrator] update failed: {e}"
            print(err, flush=True)
            traceback.print_exc()
        time.sleep(max(5, INTERVAL_SECONDS))


if __name__ == "__main__":
    main()

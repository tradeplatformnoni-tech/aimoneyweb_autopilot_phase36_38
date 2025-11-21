#!/usr/bin/env bash
# ⚙️ NeoLight Trader AutoFix v2 — Fully automated repair and enhancement

set -Eeuo pipefail
ROOT="$HOME/neolight"
TRADER="$ROOT/trader/smart_trader.py"
STATE_DIR="$ROOT/state"
STATE_FILE="$STATE_DIR/trader_state.json"
RCLONE_SCRIPT="$ROOT/scripts/rclone_sync_state.sh"
GUARDIAN="$ROOT/neo_light_fix.sh"

echo "🧩 Starting SmartTrader AutoFix..."

# --- Backup existing file -----------------------------------------------------
if [[ -f "$TRADER" ]]; then
  cp "$TRADER" "${TRADER}.bak_$(date +%Y%m%d_%H%M%S)"
  echo "🗂 Backup created: ${TRADER}.bak_*"
fi

# --- Insert Self-Healing + Heartbeat + Daily Reset ---------------------------
python3 - <<'PY'
from pathlib import Path
import datetime as dt, textwrap

trader = Path('~/neolight/trader/smart_trader.py').expanduser()
src = trader.read_text()

# Define the fix block
block = textwrap.dedent('''\
# ======================================================================
# 🧠 SmartTrader Core Loop — Resilient, Self-Healing, and Daily-Adaptive
# ======================================================================

while not stop_flag["stop"]:
    try:
        # --- Self-Healing State Guard ----------------------------------
        if "daily" not in state or not isinstance(state["daily"], dict):
            state["daily"] = {}
        if "date" not in state["daily"]:
            state["daily"]["date"] = dt.date.today().isoformat()
        if "equity" not in state["daily"]:
            state["daily"]["equity"] = 100000.0
        if "pnl" not in state["daily"]:
            state["daily"]["pnl"] = 0.0
        if "alerts" not in state:
            state["alerts"] = {"drawdown_sent": False}
        if "streak" not in state:
            state["streak"] = {"wins": 0, "losses": 0, "last_result": None}
        if "pyramids" not in locals():
            pyramids = {s: 0 for s in SYMBOLS}
        if "broker" not in locals():
            class DummyBroker: 
                def fetch_portfolio_value(self): return 100000.0
            broker = DummyBroker()

        # --- Daily reset block ----------------------------------------
        if state["daily"]["date"] != dt.date.today().isoformat():
            pv0 = broker.fetch_portfolio_value() if hasattr(broker, "fetch_portfolio_value") else state["daily"]["equity"]
            state["daily"] = {
                "date": dt.date.today().isoformat(),
                "start_equity": pv0,
                "pnl_pct": 0.0,
                "equity": pv0
            }
            state["streak"] = {"wins": 0, "losses": 0, "last_result": None}
            state["alerts"]["drawdown_sent"] = False
            pyramids.update({s: 0 for s in SYMBOLS})
            log("🔁 New trading day → reset daily stats & pyramids.")

        # --- Main trade cycle -----------------------------------------
        trade_cycle(broker, SYMBOLS, state, config, pyramids)

        # --- Heartbeat & persistence -----------------------------------
        global loop_counter
        loop_counter = locals().get("loop_counter", 0) + 1
        if loop_counter % 60 == 0:
            log(f"💹 Heartbeat {dt.datetime.now().isoformat()} equity={state['daily'].get('equity', 'NA')}")
            save_state(state, STATE_FILE)
            import subprocess, os
            subprocess.Popen(
                ["bash", os.path.expanduser("~/neolight/scripts/rclone_sync_state.sh")],
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )

        time.sleep(1)

    except KeyboardInterrupt:
        log("🛑 Manual shutdown requested.")
        stop_flag["stop"] = True
    except Exception as e:
        import traceback, time
        log(f"💥 Loop error: {e}")
        traceback.print_exc()
        time.sleep(3)
        continue

log("👋 Trader stopped gracefully. Saving final state...")
save_state(state, STATE_FILE)
import subprocess, os
subprocess.Popen(
    ["bash", os.path.expanduser("~/neolight/scripts/rclone_sync_state.sh")],
    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
)
''')

# Patch or append loop
if "while not stop_flag" in src:
    lines = src.splitlines()
    start = [i for i,l in enumerate(lines) if "while not stop_flag" in l]
    if start:
        i = start[0]
        src = "\n".join(lines[:i]) + "\n" + block + "\n"
    else:
        src += "\n" + block
else:
    src += "\n" + block

trader.write_text(src)
print("✅ Trader loop replaced with resilient version.")
PY

# --- Create state dir/file if missing ---------------------------------------
mkdir -p "$STATE_DIR"
python3 - <<'PY'
import os, json, datetime as dt, pathlib
state_path = pathlib.Path('~/neolight/state/trader_state.json').expanduser()
if not state_path.exists() or state_path.stat().st_size == 0:
    state = {
        "daily": {"date": dt.date.today().isoformat(), "equity": 100000.0, "pnl": 0.0},
        "positions": {},
        "pnl_history": [],
        "alerts": {"drawdown_sent": False}
    }
    state_path.write_text(json.dumps(state, indent=2))
    print(f"✅ Created {state_path}")
else:
    print(f"ℹ️ State file OK: {state_path}")
PY

# --- Setup rclone sync state helper ----------------------------------------
mkdir -p "$ROOT/scripts"
cat > "$RCLONE_SCRIPT" <<'BASH'
#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/neolight"
rclone copy "$ROOT/state" neo_remote:neolight/state -v --create-empty-src-dirs || true
BASH
chmod +x "$RCLONE_SCRIPT"
echo "✅ Created $RCLONE_SCRIPT"

# --- Add Guardian heartbeat check ------------------------------------------
if ! grep -q "check_heartbeat()" "$GUARDIAN" 2>/dev/null; then
cat >> "$GUARDIAN" <<'BASH'

# ─── Trader Heartbeat Check ────────────────────────────────────────────────
check_heartbeat(){
  local LOG="$HOME/neolight/logs/trader_stdout.log"
  if [[ ! -f "$LOG" ]]; then warn "No trader log yet"; return; fi
  if ! tail -n 500 "$LOG" | grep -q "💹 Heartbeat"; then
    warn "No heartbeat detected — restarting SmartTrader"
    nohup python3 "$HOME/neolight/trader/smart_trader.py" >> "$LOG" 2>&1 &
  else
    ok "💹 Trader heartbeat detected — healthy"
  fi
}
check_heartbeat
BASH
echo "✅ Guardian heartbeat check added."
fi

echo "🎯 SmartTrader AutoFix completed successfully."


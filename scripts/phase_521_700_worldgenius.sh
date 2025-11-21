#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$HOME/neolight"
VENV="$ROOT/venv"
LOGS="$ROOT/logs"
DASH="$ROOT/dashboard"
AGENTS="$ROOT/agents"
PHASES="$ROOT/phases"
SCRIPTS="$ROOT/scripts"
STATE="$ROOT/state"
RUNTIME="$ROOT/runtime"
mkdir -p "$LOGS" "$DASH" "$AGENTS" "$PHASES" "$SCRIPTS" "$STATE" "$RUNTIME"

# --- venv ----------------------------------------------------------------
if [[ ! -x "$VENV/bin/python3" ]]; then
  python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
PY="$VENV/bin/python3"
PIP="$VENV/bin/pip"

echo "🧩 Installing/validating dependencies…"
REQS=(fastapi uvicorn plotly pandas numpy yfinance requests pillow dask polars gTTS playsound3 httpx tenacity)
for pkg in "${REQS[@]}"; do
  python - <<PY || $PIP install -q "$pkg"
import importlib, sys
name = sys.argv[1]
try:
  importlib.import_module(name.split('[')[0])
except Exception:
  raise SystemExit(1)
PY
done

# --- Tiny helper: find_free_port -----------------------------------------
cat > "$SCRIPTS/find_free_port.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
start="${1:-8090}"
end="${2:-8099}"
for p in $(seq "$start" "$end"); do
  if ! lsof -i :"$p" >/dev/null 2>&1; then
    echo "$p"
    exit 0
  fi
done
echo "NOFREE" && exit 1
SH
chmod +x "$SCRIPTS/find_free_port.sh"

# --- Dashboard V2.5 (auto-port + /healthz + StrategyLab + benchmark) ----
cat > "$DASH/dashboard_v2_live.py" <<'PY'
#!/usr/bin/env python3
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import os, socket, json
from pathlib import Path
import pandas as pd
import plotly.express as px
import uvicorn

ROOT = os.path.expanduser("~/neolight")
STATE = Path(ROOT) / "state"
RUNTIME = Path(ROOT) / "runtime"
STATE.mkdir(parents=True, exist_ok=True)
RUNTIME.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="NeoLight Dashboard V2.5")

def find_free_port(start=8090, end=8099):
    for p in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError(f"No free port in {start}-{end}")

def chosen_port():
    env_port = os.environ.get("NEOLIGHT_DASH_PORT")
    if env_port and env_port.isdigit():
        return int(env_port)
    return find_free_port(8090, 8099)

@app.get("/healthz")
def healthz():
    return {"ok": True}

INDEX_HTML = """
<html><head><title>NeoLight Dashboard V2.5</title></head>
<body style="background:#0b0f17;color:#d7e1f8;font-family:Inter,system-ui,Arial;">
  <h1>NeoLight — Live Intelligence</h1>
  <div style="margin:8px 0;padding:6px 10px;background:#121826;border:1px solid #1c2333;border-radius:8px;">
    <b>Panels:</b>
    <a style="color:#7dd3fc" href="/chart?file=performance_metrics.csv">Performance</a> •
    <a style="color:#7dd3fc" href="/chart?file=pnl_history.csv">PnL</a> •
    <a style="color:#7dd3fc" href="/brain">Atlas Brain</a> •
    <a style="color:#7dd3fc" href="/strategy_lab">Strategy Lab</a> •
    <a style="color:#7dd3fc" href="/equity_vs_spy">Equity vs SPY</a> •
    <a style="color:#7dd3fc" href="/healthz">Health</a>
  </div>
</body></html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return INDEX_HTML

@app.get("/chart")
def chart(file: str):
    f = STATE / file
    if not f.exists():
        return JSONResponse({"error": "missing "+file}, status_code=404)
    df = pd.read_csv(f)
    x = 'date' if 'date' in df.columns else ('Date' if 'Date' in df.columns else df.columns[0])
    y = [c for c in df.columns if c.lower() not in ('date','timestamp')]
    if not y:
        return JSONResponse({"error":"no numeric cols"}, status_code=400)
    fig = px.line(df, x=x, y=y, title=file)
    return HTMLResponse(fig.to_html(include_plotlyjs='cdn'))

@app.get("/brain")
def brain():
    p = RUNTIME/"atlas_brain.json"
    return JSONResponse(json.loads(p.read_text()) if p.exists() else {"error":"no brain"})

@app.get("/strategy_lab")
def strategy_lab():
    f = STATE / "deep_research_rank.csv"
    if not f.exists():
        return JSONResponse({"error":"no deep_research_rank.csv"}, status_code=404)
    try:
        df = pd.read_csv(f)
    except Exception as e:
        return JSONResponse({"error": f"read fail: {e}"}, status_code=500)
    # show top 10
    df = df.head(10)
    html = df.to_html(index=False)
    return HTMLResponse(f"<html><body style='background:#0b0f17;color:#d7e1f8;font-family:Inter,system-ui,Arial;'>{html}</body></html>")

@app.get("/equity_vs_spy")
def equity_vs_spy():
    pnl = STATE / "pnl_history.csv"
    if not pnl.exists():
        return JSONResponse({"error":"no pnl_history.csv"}, status_code=404)
    df = pd.read_csv(pnl)
    # Expect 'date' and 'wealth' columns from your replay
    x = 'date' if 'date' in df.columns else ( 'Date' if 'Date' in df.columns else df.columns[0] )
    y = [c for c in df.columns if c.lower() not in ('date','timestamp')]
    import yfinance as yf
    import pandas as pd
    try:
        spy = yf.download("SPY", period="1y", interval="1d", auto_adjust=True, progress=False).reset_index()
        spy = spy.rename(columns={"Date":"date","Close":"SPY"})
        # build our equity series if available (wealth or cumulative pnl proxy)
        if "wealth" in df.columns:
            ours = df[[x,"wealth"]].rename(columns={x:"date"})
        else:
            ours = df[[x, y[0]]].rename(columns={x:"date", y[0]:"ours"})
        merged = pd.merge(ours, spy[["date","SPY"]], on="date", how="inner")
        fig = px.line(merged, x="date", y=[c for c in merged.columns if c!="date"], title="Equity vs SPY")
        return HTMLResponse(fig.to_html(include_plotlyjs='cdn'))
    except Exception as e:
        return JSONResponse({"error": f"benchmark failed: {e}"}, status_code=500)

if __name__ == "__main__":
    port = int(os.environ.get("NEOLIGHT_DASH_PORT") or 0) or chosen_port()
    print(f"🌐 Launching NeoLight Dashboard V2.5 → http://127.0.0.1:{port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port)
PY
chmod +x "$DASH/dashboard_v2_live.py"

# --- Guardian hook: start_dashboard + health check -----------------------
if ! grep -q "start_dashboard()" "$ROOT/neo_light_fix.sh" 2>/dev/null; then
  awk '1; /intervene\(\)/ && c==0 {c=1} END{}' "$ROOT/neo_light_fix.sh" >/dev/null 2>&1 || true
fi

# append helper only if missing
if ! grep -q "start_dashboard()" "$ROOT/neo_light_fix.sh"; then
  cat >> "$ROOT/neo_light_fix.sh" <<'SH'

# --- Auto-start Dashboard V2.5 with health check ------------------------
start_dashboard() {
  local logf="$LOG_DIR/dashboard_v2_$(date +%Y%m%d_%H%M%S).log"
  local port
  if [[ -n "${NEOLIGHT_DASH_PORT:-}" ]]; then
    port="$NEOLIGHT_DASH_PORT"
  else
    port="$("$SCRIPTS_DIR/find_free_port.sh" 8090 8099 || echo 8099)"
  fi
  warn "▶️  Starting Dashboard V2.5 on port ${port}…"
  NEOLIGHT_DASH_PORT="$port" nohup "$ROOT/venv/bin/python3" "$DASH_DIR/dashboard_v2_live.py" >> "$logf" 2>&1 &
  # quick /healthz probe
  for i in {1..10}; do
    sleep 1
    if curl -fsS "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1; then
      ok "🟢 Dashboard healthy at http://127.0.0.1:${port}"
      return 0
    fi
  done
  err "🔴 Dashboard failed /healthz. See $logf"
  return 1
}
SH
fi

# make intervene() call start_dashboard if dashboard not healthy
if ! grep -q "start_dashboard ||" "$ROOT/neo_light_fix.sh"; then
  sed -i '' '/# Dashboard V2/{n;n; a\
  # Ensure healthy\
  if ! curl -fsS "http:\/\/127.0.0.1:${NEOLIGHT_DASH_PORT:-8090}\/healthz" >/dev\/null 2>\&1; then\
    start_dashboard || send_alert "Dashboard failed to start — check logs."\
  fi\
' "$ROOT/neo_light_fix.sh" || true
fi

# --- Strategy Lab input file stub (if none) ------------------------------
if [[ ! -f "$STATE/deep_research_rank.csv" ]]; then
  cat > "$STATE/deep_research_rank.csv" <<'CSV'
symbol,return_%,vol_%,sharpe
SPY,8.2,14.1,0.58
QQQ,11.4,18.2,0.63
GLD,5.1,10.2,0.50
BTC-USD,40.0,75.0,0.53
ETH-USD,60.0,110.0,0.55
CSV
fi

# --- Knowledge Integrator (stubs; env-driven) ----------------------------
cat > "$AGENTS/knowledge_integrator.py" <<'PY'
#!/usr/bin/env python3
"""
Env-driven stubs for fetching headlines/signals from Twitter/Reddit/GitHub.
If keys are missing, we no-op gracefully and just print a message.
"""
import os, json, time
from pathlib import Path

ROOT = os.path.expanduser("~/neolight")
STATE = Path(ROOT)/"state"
OUT = STATE/"knowledge_snap.json"

def main():
    payload = {"ts": time.time(), "sources": {}}

    # Twitter/X (stub)
    if os.getenv("TWITTER_BEARER_TOKEN"):
        payload["sources"]["twitter"] = ["(stub) parsed twitter items"]
    else:
        payload["sources"]["twitter"] = "no key"

    # Reddit (stub)
    if os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_SECRET"):
        payload["sources"]["reddit"] = ["(stub) parsed reddit items"]
    else:
        payload["sources"]["reddit"] = "no key"

    # GitHub (stub)
    if os.getenv("GITHUB_TOKEN"):
        payload["sources"]["github"] = ["(stub) repo signals"]
    else:
        payload["sources"]["github"] = "no key"

    OUT.write_text(json.dumps(payload, indent=2))
    print("🔎 Knowledge Integrator refreshed →", OUT)

if __name__ == "__main__":
    main()
PY
chmod +x "$AGENTS/knowledge_integrator.py"

# --- Cursor IDE Integration ---------------------------------------------
cat > "$ROOT/.cursorrules" <<'TXT'
# NeoLight Guardrails (Cursor)
- Project goal: Fully autonomous, self-healing trading research + execution mesh.
- Critical files:
  - phases/*  : phase scripts
  - agents/*  : brain/orchestrator/watchers
  - trader/*  : SmartTrader loop and broker interfaces
  - dashboard/*: live FastAPI dashboard
  - scripts/* : guardians, schedulers, auto-heal
- Coding standards:
  - Python 3.12+, no type|None (use Optional[T]).
  - Fail fast, log errors to logs/*.log.
  - Never break idempotency: scripts must be re-runnable.
- Commit intent:
  - Small PR-sized changes; keep diffs readable.
- Tests (lightweight):
  - At minimum, `python -m py_compile` passes for changed Python files.
TXT

# Hook that Guardian can call later if you want auto-repair via Cursor/DeepSeek
cat > "$SCRIPTS/code_fix_hook.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
# placeholder hook; wire into your model/agent of choice later.
# if DEEPSEEK_API_KEY or OPENAI_API_KEY exists, you can curl a repair endpoint here.
echo "[code_fix_hook] Would call LLM fixer here (env-driven)."
exit 0
SH
chmod +x "$SCRIPTS/code_fix_hook.sh"

# --- Scheduler (every 4h run orchestrator + knowledge integrator) -------
cat > "$SCRIPTS/schedule_all.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ROOT="${HOME}/neolight"
PY="${ROOT}/venv/bin/python3"
LOG="${ROOT}/logs/schedule_stdout.log"
while true; do
  NOW="$(date '+%F %T')"
  echo "[$NOW] 🔁 Intelligence tick…" >> "$LOG" 2>&1
  nohup "$PY" "$ROOT/agents/intelligence_orchestrator.py" >> "$ROOT/logs/intel_orchestrator.log" 2>&1 || true
  nohup "$PY" "$ROOT/agents/knowledge_integrator.py"    >> "$ROOT/logs/knowledge_integrator.log" 2>&1 || true
  sleep 14400  # 4 hours
done
SH
chmod +x "$SCRIPTS/schedule_all.sh"

echo "✅ Phase 521–700 WorldGenius upgrade complete."
echo "Next:"
echo "1) Launch/refresh Guardian:"
echo "   nohup bash ~/neolight/neo_light_fix.sh >> ~/neolight/logs/guardian_stdout.log 2>&1 & disown; tail -f ~/neolight/logs/guardian_stdout.log"
echo "2) Or run dashboard now:"
echo "   NEOLIGHT_DASH_PORT=8090 $PY ~/neolight/dashboard/dashboard_v2_live.py"
echo "3) Start scheduler (optional):"
echo "   nohup bash ~/neolight/scripts/schedule_all.sh >> ~/neolight/logs/schedule_stdout.log 2>&1 &"

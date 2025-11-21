#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${HOME}/neolight"
DASH="${ROOT}/dashboard"
SCRIPTS="${ROOT}/scripts"
LOGS="${ROOT}/logs"
VENVPY="${ROOT}/venv/bin/python3"
mkdir -p "$DASH" "$SCRIPTS" "$LOGS"

echo "🧠 NeoLight — WorldClass AutoScript Upgrade starting…"

# -----------------------------
# 1) Free-port finder helper
# -----------------------------
cat > "${SCRIPTS}/find_free_port.sh" <<'SH'
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
chmod +x "${SCRIPTS}/find_free_port.sh"

# -----------------------------
# 2) Dashboard V2 rewrite (idempotent, backup first)
#    - /healthz endpoint
#    - port auto-resolver (env or 8090→8099)
#    - Brain Confidence chip
# -----------------------------
DASH_FILE="${DASH}/dashboard_v2_live.py"
[[ -f "$DASH_FILE" ]] && cp "$DASH_FILE" "${DASH_FILE}.bak_$(date +%Y%m%d_%H%M%S)"

cat > "$DASH_FILE" <<'PY'
#!/usr/bin/env python3
import os, json, socket
from pathlib import Path
import pandas as pd
import plotly.express as px
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

ROOT = os.path.expanduser("~/neolight")
STATE = Path(ROOT)/"state"
RUNTIME = Path(ROOT)/"runtime"
STATE.mkdir(parents=True, exist_ok=True)
RUNTIME.mkdir(parents=True, exist_ok=True)

app = FastAPI()

def find_free_port(start=8090, end=8099):
    for p in range(start, end+1):
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

def read_brain():
    p = RUNTIME/"atlas_brain.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}

@app.get("/", response_class=HTMLResponse)
def home():
    brain = read_brain()
    conf = brain.get("confidence")
    scaler = brain.get("risk_scaler")
    chip = ""
    if conf is not None and scaler is not None:
        chip = f'''
        <div style="display:inline-block;padding:6px 10px;border-radius:12px;background:#111827;color:#a7f3d0;
                    border:1px solid #064e3b;margin-left:10px;">
          🧠 Brain: confidence <b>{conf:.3f}</b> · scaler <b>{scaler:.3f}</b>
        </div>'''
    return f"""
    <html>
    <head>
      <title>NeoLight Dashboard V2</title>
      <meta http-equiv="refresh" content="20" />
    </head>
    <body style="background:#0b0f17;color:#d7e1f8;font-family:Inter,system-ui,Arial;">
      <div style="display:flex;align-items:center;gap:10px;">
        <h1 style="margin:14px 0;">NeoLight — Live Metrics</h1>
        {chip}
      </div>
      <p>
        <a style="color:#93c5fd" href="/chart?file=performance_metrics.csv">Performance</a> ·
        <a style="color:#93c5fd" href="/chart?file=pnl_history.csv">PnL</a> ·
        <a style="color:#93c5fd" href="/brain">Atlas Brain (raw)</a>
      </p>
    </body></html>"""

@app.get("/chart")
def chart(file: str):
    f = STATE / file
    if not f.exists():
        return JSONResponse({"error": f"missing {file}"}, status_code=404)
    try:
        df = pd.read_csv(f)
    except Exception as e:
        return JSONResponse({"error": f"failed to read {file}: {e}"}, status_code=500)
    x = None
    for k in ("date","Date","timestamp","Timestamp"):
        if k in df.columns:
            x = k; break
    if not x:
        x = df.columns[0]
    y = [c for c in df.columns if c.lower() not in ('date','timestamp')]
    if not y:
        return JSONResponse({"error": "no numeric columns"}, status_code=400)
    fig = px.line(df, x=x, y=y, title=file)
    return HTMLResponse(fig.to_html(include_plotlyjs='cdn'))

@app.get("/brain")
def brain():
    p = Path(ROOT)/"runtime"/"atlas_brain.json"
    return JSONResponse(json.loads(p.read_text()) if p.exists() else {"error":"no brain"})

if __name__ == "__main__":
    port = chosen_port()
    print(f"🌐 Launching NeoLight Dashboard V2 → http://127.0.0.1:{port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port)
PY
chmod +x "$DASH_FILE"

# -----------------------------
# 3) Patch Guardian (neo_light_fix.sh)
#    - add rotate_one_log
#    - add start_dashboard() with health check + port resolver
#    - ensure intervene() calls it (idempotent injection)
# -----------------------------
GUARD="${ROOT}/neo_light_fix.sh"
[[ -f "$GUARD" ]] || { echo "❌ Missing ${GUARD}. Aborting."; exit 1; }
cp "$GUARD" "${GUARD}.bak_$(date +%Y%m%d_%H%M%S)"

inject_rotate='
rotate_one_log() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  local sz
  sz=$(du -m "$f" 2>/dev/null | awk "{print \$1}")
  [[ "${sz:-0}" -gt "${MAX_LOG_SIZE_MB:-100}" ]] && mv "$f" "${f}.1" || true
}
'

inject_start_dash='
start_dashboard() {
  local logf="${LOG_DIR}/dashboard_v2_$(date +%Y%m%d_%H%M%S).log"
  rotate_one_log "$logf" || true
  local port
  if [[ -n "${NEOLIGHT_DASH_PORT:-}" ]]; then
    port="$NEOLIGHT_DASH_PORT"
  else
    port="$("${SCRIPTS_DIR}/find_free_port.sh" 8090 8099 || echo 8099)"
  fi
  warn "▶️  Starting Dashboard V2 on port ${port}…"
  NEOLIGHT_DASH_PORT="$port" nohup "${ROOT}/venv/bin/python3" "${DASH_DIR}/dashboard_v2_live.py" >> "$logf" 2>&1 &
  for i in {1..10}; do
    sleep 1
    if curl -fsS "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1; then
      ok "🟢 Dashboard healthy at http://127.0.0.1:${port}"
      return 0
    fi
  done
  err "🔴 Dashboard did not pass health check. See $logf"
  return 1
}
'

# Add rotate_one_log if missing
if ! grep -q "rotate_one_log()" "$GUARD"; then
  awk -v inj="$inject_rotate" 'NR==1{print; print inj; next}1' "$GUARD" > "${GUARD}.tmp" && mv "${GUARD}.tmp" "$GUARD"
fi

# Add start_dashboard if missing
if ! grep -q "start_dashboard()" "$GUARD"; then
  awk -v inj="$inject_start_dash" '/# --- Diagnose & Intervene/{print; print inj; next}1' "$GUARD" > "${GUARD}.tmp" && mv "${GUARD}.tmp" "$GUARD"
fi

# Ensure intervene() ensures dashboard health
if ! grep -q "start_dashboard" "$GUARD"; then
  awk -v DASHDIR="${DASH}" -v LOGDIR="${LOGS}" '
    /intervene\(\)\s*{/ {print; in_fn=1; next}
    in_fn && /ensure_running "dashboard_v2"/ {
      print
      print ""
      print "  # Ensure dashboard is actually healthy (healthz) — auto-start if needed"
      print "  if ! curl -fsS \"http://127.0.0.1:${NEOLIGHT_DASH_PORT:-8090}/healthz\" >/dev/null 2>&1; then"
      print "    start_dashboard || send_alert \"Dashboard failed to start — check logs.\""
      print "  fi"
      in_fn=0
      next
    }
    {print}
  ' "$GUARD" > "${GUARD}.tmp" && mv "${GUARD}.tmp" "$GUARD"
fi

chmod +x "$GUARD"

# -----------------------------
# 4) Quick deps heal (FastAPI etc.)
# -----------------------------
if [[ -x "${ROOT}/venv/bin/pip" ]]; then
  "${ROOT}/venv/bin/pip" install -q --disable-pip-version-check fastapi uvicorn plotly pandas >/dev/null || true
fi

echo "✅ WorldClass AutoScript Upgrade complete."
echo "Next:"
echo "  1) Restart Guardian:"
echo "     nohup bash ${ROOT}/neo_light_fix.sh >> ${LOGS}/guardian_stdout.log 2>&1 & disown; tail -f ${LOGS}/guardian_stdout.log"
echo "  2) Open the dashboard URL it prints (port auto-picked 8090–8099)."

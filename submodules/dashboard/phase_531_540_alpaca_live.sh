#!/usr/bin/env bash
# phase_531_540_alpaca_live.sh
set -e

echo "🔥 NeoLight :: Phase 531–540 (Alpaca Live Feed + Dashboard) starting..."

# 1) Folders
mkdir -p backend templates static ai/strategies tools runtime logs

# 2) Python env (optional but recommended)
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate || true
python -m pip install --upgrade pip

# 3) Deps
pip install fastapi uvicorn alpaca-trade-api pandas --quiet

# 4) Runtime files
cat > runtime/live_mode.json <<'JSONLIVE'
{"live": false}
JSONLIVE

# 5) BACKEND: FastAPI app
cat > backend/main.py <<'PYCODE'
import os, json, datetime, random
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Optional: Alpaca only used in LIVE mode
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")

app = FastAPI(title="AI Money Web :: NeoLight v3.4")
app.mount("/static", StaticFiles(directory="static"), name="static")

RUNTIME_LIVE = "runtime/live_mode.json"
SIGNALS_FILE = "runtime/signals.jsonl"

def get_live_flag() -> bool:
    try:
        with open(RUNTIME_LIVE, "r") as f:
            return bool(json.load(f).get("live", False))
    except Exception:
        return False

def ensure_files():
    os.makedirs("runtime", exist_ok=True)
    if not os.path.exists(RUNTIME_LIVE):
        with open(RUNTIME_LIVE, "w") as f:
            json.dump({"live": False}, f)
    if not os.path.exists(SIGNALS_FILE):
        open(SIGNALS_FILE, "a").close()
ensure_files()

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    with open("templates/dashboard.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/live-toggle")
def api_get_toggle():
    return {"live": get_live_flag()}

@app.post("/api/live-toggle")
def api_set_toggle(payload: dict):
    live = bool(payload.get("live", False))
    with open(RUNTIME_LIVE, "w") as f:
        json.dump({"live": live}, f)
    return {"status": "updated", "live": live}

@app.get("/api/strategy-log")
def api_strategy_log():
    if not os.path.exists(SIGNALS_FILE):
        return []
    entries = []
    with open(SIGNALS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return entries[-200:]  # last 200 for sanity

@app.get("/api/ohlc")
def api_ohlc(symbol: str = "AAPL", limit: int = 60):
    """
    Returns latest OHLC data.
    - LIVE mode: Alpaca paper bars (1m)
    - SIM mode: synthetic series
    """
    live = get_live_flag()
    if live:
        # Require keys for live mode
        if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
            return JSONResponse({"error": "Missing ALPACA_API_KEY/ALPACA_SECRET_KEY env vars."}, status_code=400)
        try:
            # Lazy import only when needed
            from alpaca_trade_api.rest import REST, TimeFrame
            api = REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url="https://paper-api.alpaca.markets")
            bars = api.get_bars(symbol, TimeFrame.Minute, limit=limit).df
            if bars is None or len(bars) == 0:
                return []
            bars = bars.reset_index()
            out = []
            for _, row in bars.iterrows():
                # Row keys: open high low close volume, timestamp index
                out.append({
                    "t": str(row["timestamp"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                })
            return out[-limit:]
        except Exception as e:
            return JSONResponse({"error": f"Alpaca error: {e}"}, status_code=500)

    # --- SIM MODE (fallback) ---
    series = []
    now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
    price = 150.0
    for i in range(limit):
        ts = now - datetime.timedelta(minutes=(limit - 1 - i))
        o = price + random.uniform(-0.8, 0.8)
        h = o + random.uniform(0.0, 1.2)
        l = o - random.uniform(0.0, 1.2)
        c = random.uniform(l, h)
        v = random.randint(1000, 9000)
        series.append({"t": ts.isoformat(), "open": round(o, 2), "high": round(h, 2),
                       "low": round(l, 2), "close": round(c, 2), "volume": v})
        price = c
    return series

@app.post("/api/quick-trade")
def api_quick_trade(order: dict):
    """
    Stub for a quick trade endpoint.
    Extend to place live/paper orders via Alpaca REST in future phases.
    """
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "type": "quick_trade",
        "payload": order,
        "note": "stubbed"
    }
    with open(SIGNALS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return {"status": "ok", "logged": entry}

# DEV: uvicorn entry
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
PYCODE

# 6) DASHBOARD HTML
cat > templates/dashboard.html <<'HTMLCODE'
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>NeoLight v3.4 :: Live Dashboard</title>
  <link rel="stylesheet" href="/static/style.css" />
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <h1>💡 AI Money Web :: NeoLight v3.4</h1>

  <div class="row">
    <label class="switch">
      <input type="checkbox" id="modeToggle" />
      <span class="slider round"></span>
    </label>
    <span id="modeStatus" class="badge">Loading...</span>
  </div>

  <h3>📈 AAPL — 1m OHLC (SIM/LIVE)</h3>
  <canvas id="chart" height="120"></canvas>

  <h3>🧠 Strategy Logs</h3>
  <pre id="logs">Loading...</pre>

  <script src="/static/dashboard.js"></script>
</body>
</html>
HTMLCODE

# 7) STYLE
cat > static/style.css <<'CSSCODE'
:root {
  --neon: #00ffff;
  --bg: #000;
  --panel: #0b0b0b;
  --ink: #e8ffff;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2rem;
  background: var(--bg); color: var(--ink);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
h1 { color: var(--neon); margin-top: 0; }
.row { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; }
.badge { color: var(--neon); }
pre#logs {
  background: var(--panel); padding: 1rem; border-radius: 10px;
  max-height: 300px; overflow: auto; white-space: pre-wrap;
  border: 1px solid #112;
}

/* Toggle switch */
.switch { position: relative; display: inline-block; width: 60px; height: 34px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
  background-color: #333; transition: .4s; }
.slider:before { position: absolute; content: ""; height: 26px; width: 26px;
  left: 4px; bottom: 4px; background-color: white; transition: .4s; }
input:checked + .slider { background-color: var(--neon); }
input:checked + .slider:before { transform: translateX(26px); }
.slider.round { border-radius: 34px; }
.slider.round:before { border-radius: 50%; }
CSSCODE

# 8) DASHBOARD JS
cat > static/dashboard.js <<'JSCODE'
let chart;

async function fetchToggle() {
  const r = await fetch('/api/live-toggle');
  return r.json();
}
async function setToggle(live) {
  await fetch('/api/live-toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ live })
  });
}

async function loadOHLC() {
  const r = await fetch('/api/ohlc?symbol=AAPL&limit=60');
  return r.json();
}
async function loadLogs() {
  const r = await fetch('/api/strategy-log');
  return r.json();
}

function renderChart(labels, closes) {
  const ctx = document.getElementById('chart').getContext('2d');
  if (chart) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = closes;
    chart.update();
    return;
  }
  chart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ label: 'Close', data: closes, borderColor: '#00ffff', tension: 0.3 }] },
    options: {
      plugins: { legend: { labels: { color: '#00ffff' } } },
      scales: {
        x: { ticks: { color: '#00ffff' } },
        y: { ticks: { color: '#00ffff' } }
      }
    }
  });
}

async function refreshChart() {
  try {
    const data = await loadOHLC();
    if (!Array.isArray(data)) return;
    const labels = data.map(d => (d.t || '').slice(11,16));
    const closes = data.map(d => d.close);
    renderChart(labels, closes);
  } catch (e) { /* silent */ }
}

async function refreshLogs() {
  try {
    const logs = await loadLogs();
    const pre = document.getElementById('logs');
    if (!logs || logs.length === 0) { pre.textContent = "No strategy logs yet."; return; }
    pre.textContent = logs.map(l => JSON.stringify(l)).join("\n");
  } catch (e) { /* silent */ }
}

async function main() {
  const toggle = document.getElementById('modeToggle');
  const status = document.getElementById('modeStatus');
  const mode = await fetchToggle();
  toggle.checked = !!mode.live;
  status.textContent = toggle.checked ? "LIVE Mode" : "SIM Mode";

  toggle.addEventListener('change', async () => {
    await setToggle(toggle.checked);
    status.textContent = toggle.checked ? "LIVE Mode" : "SIM Mode";
    refreshChart();
  });

  await refreshChart();
  await refreshLogs();
  setInterval(refreshChart, 5000);
  setInterval(refreshLogs, 7000);
}

document.addEventListener('DOMContentLoaded', main);
JSCODE

# 9) Friendly run tips
cat > RUN.txt <<'RUNTIPS'
Run server:
  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &

Open dashboard:
  http://localhost:8000/dashboard

Set Alpaca keys (LIVE mode):
  export ALPACA_API_KEY="YOUR_KEY"
  export ALPACA_SECRET_KEY="YOUR_SECRET"
Then flip the dashboard toggle to LIVE.

If you see "permission denied" when running a .sh:
  chmod +x ./phase_531_540_alpaca_live.sh
  # or for any script:
  chmod +x script.sh
RUNTIPS

echo "✅ Phase 531–540 complete!"
echo "----------------------------------------"
echo "To start:  nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &"
echo "Open:      http://localhost:8000/dashboard"
echo "LIVE mode: export ALPACA_API_KEY=... && export ALPACA_SECRET_KEY=... (then toggle LIVE)"


#!/bin/bash
# =============================================
# NeoLight v3.4 :: Phase 531–540 (Alpaca Integration)
# =============================================

echo "🔥 Launching AI Money Web :: NeoLight v3.4 Live Data Autopilot..."

# --- 1️⃣ Setup Folder Structure ---
mkdir -p backend templates static runtime tools ai/strategies
touch runtime/strategy_config.json runtime/signals.jsonl runtime/live_mode.json

# --- 2️⃣ Install Dependencies ---
pip install fastapi uvicorn requests alpaca-trade-api pandas yfinance --quiet

# --- 3️⃣ Create backend/main.py ---
cat > backend/main.py << 'EOF'
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json, os, datetime, requests, random
from alpaca_trade_api.rest import REST, TimeFrame

ALPACA_KEY = os.getenv("ALPACA_API_KEY", "demo-key")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY", "demo-secret")
ALPACA_BASE = "https://data.alpaca.markets/v2"

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/dashboard.html", "r") as f:
        return f.read()

@app.get("/api/live-toggle")
def get_toggle():
    if not os.path.exists("runtime/live_mode.json"):
        json.dump({"live": False}, open("runtime/live_mode.json", "w"))
    return json.load(open("runtime/live_mode.json"))

@app.post("/api/live-toggle")
def set_toggle(data: dict):
    json.dump(data, open("runtime/live_mode.json", "w"))
    return {"status": "updated", "mode": data}

@app.get("/api/ohlc")
def get_ohlc(symbol: str = "AAPL"):
    live_mode = json.load(open("runtime/live_mode.json"))["live"]
    if live_mode:
        try:
            api = REST(ALPACA_KEY, ALPACA_SECRET, base_url="https://paper-api.alpaca.markets")
            bars = api.get_bars(symbol, TimeFrame.Minute, limit=50).df
            bars = bars.reset_index()
            bars["t"] = bars["timestamp"].astype(str)
            return bars[["t","open","high","low","close","volume"]].tail(30).to_dict(orient="records")
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    else:
        # Simulated data if not live
        data = []
        now = datetime.datetime.utcnow()
        price = 150.0
        for i in range(30):
            o = price + random.uniform(-1, 1)
            h = o + random.uniform(0, 2)
            l = o - random.uniform(0, 2)
            c = random.uniform(l, h)
            data.append({"t": str(now - datetime.timedelta(minutes=i)), "open": o, "high": h, "low": l, "close": c, "volume": random.randint(1000, 10000)})
        return list(reversed(data))

@app.get("/api/strategy-log")
def strategy_log():
    if not os.path.exists("runtime/signals.jsonl"):
        return []
    with open("runtime/signals.jsonl", "r") as f:
        return [json.loads(line) for line in f]

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_view():
    with open("templates/dashboard.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
EOF

# --- 4️⃣ Create templates/dashboard.html ---
cat > templates/dashboard.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NeoLight v3.4 :: Live Data Dashboard</title>
    <link rel="stylesheet" href="/static/style.css">
    <style>
        body {
            font-family: monospace;
            background-color: black;
            color: #00ffff;
            padding: 2rem;
        }
        canvas {
            border: 1px solid #00ffff;
            width: 100%;
            height: 400px;
        }
        .switch {
            position: relative;
            display: inline-block;
            width: 60px;
            height: 34px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
            background-color: #444; transition: 0.4s;
        }
        .slider:before {
            position: absolute; content: ""; height: 26px; width: 26px; left: 4px; bottom: 4px;
            background-color: white; transition: 0.4s;
        }
        input:checked + .slider { background-color: #00ffff; }
        input:checked + .slider:before { transform: translateX(26px); }
        .slider.round { border-radius: 34px; }
        .slider.round:before { border-radius: 50%; }
    </style>
</head>
<body>
    <h1>💡 AI Money Web :: NeoLight v3.4</h1>
    <label class="switch">
        <input type="checkbox" id="modeToggle">
        <span class="slider round"></span>
    </label>
    <span id="modeStatus">Loading...</span>

    <h3>📈 Live Market Data (AAPL)</h3>
    <canvas id="chart"></canvas>

    <h3>🧠 Strategy Logs</h3>
    <pre id="logs">Loading...</pre>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="/static/dashboard.js"></script>
</body>
</html>
EOF

# --- 5️⃣ Create static/dashboard.js ---
cat > static/dashboard.js << 'EOF'
const ctx = document.getElementById('chart').getContext('2d');
let chart;

async function fetchData() {
    const res = await fetch('/api/ohlc');
    const data = await res.json();
    const labels = data.map(d => d.t.slice(11, 16));
    const prices = data.map(d => d.close);

    if (chart) {
        chart.data.labels = labels;
        chart.data.datasets[0].data = prices;
        chart.update();
    } else {
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'AAPL',
                    data: prices,
                    borderColor: '#00ffff',
                    tension: 0.3
                }]
            },
            options: {
                scales: {
                    x: { ticks: { color: '#00ffff' } },
                    y: { ticks: { color: '#00ffff' } }
                },
                plugins: { legend: { labels: { color: '#00ffff' } } }
            }
        });
    }
}

async function fetchLogs() {
    const res = await fetch('/api/strategy-log');
    const logs = await res.json();
    const pre = document.getElementById('logs');
    if (logs.length === 0) pre.textContent = "No signals yet.";
    else pre.textContent = logs.map(l => JSON.stringify(l)).join("\\n");
}

async function setupToggle() {
    const toggle = document.getElementById('modeToggle');
    const status = document.getElementById('modeStatus');
    const res = await fetch('/api/live-toggle');
    const mode = await res.json();
    toggle.checked = mode.live;
    status.textContent = mode.live ? "LIVE Mode" : "SIM Mode";

    toggle.addEventListener('change', async () => {
        await fetch('/api/live-toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ live: toggle.checked })
        });
        status.textContent = toggle.checked ? "LIVE Mode" : "SIM Mode";
    });
}

setInterval(fetchData, 5000);
setInterval(fetchLogs, 7000);
setupToggle();
fetchData();
fetchLogs();
EOF

# --- 6️⃣ Permissions & Startup ---
chmod +x backend/main.py
chmod +x phase_531_540_alpaca_integration.sh 2>/dev/null

echo "✅ NeoLight v3.4 Patch Complete!"
echo "-------------------------------------------"
echo "TO START FASTAPI:"
echo "nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &"
echo "Then visit 👉 http://localhost:8000/dashboard"
echo "-------------------------------------------"
echo "🧠 To toggle LIVE vs SIM, use the switch on dashboard!"
EOF


#!/bin/bash

# Filename: phase_511_530_live_data_patch.sh

echo "🔥 Starting AI Money Web :: NeoLight Phase 511–530 Patch..."

# === 1. PREP DIRS & FILES ===
mkdir -p backend runtime static templates ai/strategies logs

# === 2. BACKUP OLD FILES ===
cp backend/main.py backend/main_v3.2_backup.py 2>/dev/null
cp static/app.js static/app_v3.2_backup.js 2>/dev/null

# === 3. CREATE NEW BACKEND/main.py ===
cat > backend/main.py << 'EOF'
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import uvicorn
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

class StrategyCommand(BaseModel):
    command: str

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    with open("templates/index.html", "r") as f:
        return f.read()

@app.get("/api/live-toggle")
def get_toggle():
    with open("runtime/live_mode.json", "r") as f:
        return json.load(f)

@app.post("/api/live-toggle")
def toggle_mode(data: dict):
    with open("runtime/live_mode.json", "w") as f:
        json.dump(data, f)
    return {"status": "updated"}

@app.get("/api/strategy-log")
def get_strategy_log():
    if os.path.exists("runtime/signals.jsonl"):
        with open("runtime/signals.jsonl", "r") as f:
            return JSONResponse(content=[json.loads(line) for line in f])
    return []

@app.post("/api/quick-trade")
def quick_trade(data: dict):
    # Stub: Implement order logic or Alpaca integration here
    print(f"[ORDER] Quick trade triggered: {data}")
    return {"status": "ok", "data": data}

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
EOF

# === 4. CREATE NEW static/app.js ===
cat > static/app.js << 'EOF'
document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("modeToggle");
    const status = document.getElementById("modeStatus");

    fetch('/api/live-toggle')
        .then(res => res.json())
        .then(data => {
            toggle.checked = data.live;
            status.innerText = data.live ? "LIVE Mode" : "SIM Mode";
        });

    toggle.addEventListener("change", () => {
        fetch('/api/live-toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ live: toggle.checked })
        }).then(() => {
            status.innerText = toggle.checked ? "LIVE Mode" : "SIM Mode";
        });
    });
});
EOF

# === 5. CREATE NEW templates/index.html ===
cat > templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NeoLight v3.3 :: Live Mode</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="overlay neon-bg">
        <h1>💡 AI Money Web :: NeoLight v3.3</h1>
        <h2 id="modeStatus">Loading...</h2>
        <label class="switch">
            <input type="checkbox" id="modeToggle">
            <span class="slider round"></span>
        </label>
        <h3>Strategy Logs</h3>
        <pre id="logs"></pre>
    </div>
    <script src="/static/app.js"></script>
</body>
</html>
EOF

# === 6. INIT MODE + LOG FILES ===
echo '{"live": false}' > runtime/live_mode.json
touch runtime/signals.jsonl

# === 7. PERMISSIONS + RUN COMMANDS ===
chmod +x phase_511_530_live_data_patch.sh

echo "✅ Patch Complete!"
echo "🧠 To RUN your updated NeoLight v3.3 backend:"
echo "--------------------------------------------"
echo "nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &"
echo "--------------------------------------------"
echo "🌐 Then open your browser: http://localhost:8000"
echo "🔥 NeoLight v3.3 is live with:"
echo "  ➤ Toggle: SIM / LIVE"
echo "  ➤ Strategy Logs endpoint"
echo "  ➤ Autopilot-ready backend"
echo "  ➤ Neon dashboard patch"

# END OF SCRIPT


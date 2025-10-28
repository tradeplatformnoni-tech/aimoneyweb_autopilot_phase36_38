#!/bin/bash
echo "🚀 Starting Phase 221–240: Autopilot Strategy Dashboard Enhancer..."

# === [1] BACKUP main.py FIRST ===
BACKUP_FILE="backups/main.py.$(date +%Y%m%d_%H%M%S).bak"
mkdir -p backups
cp backend/main.py "$BACKUP_FILE"
echo "✅ Backup created -> $BACKUP_FILE"

# === [2] PATCH main.py with /dashboard route if not exists ===
if ! grep -q "/dashboard" backend/main.py; then
  echo "🧩 Patching main.py with /dashboard route..."
  cat >> backend/main.py <<EOF

from fastapi.responses import HTMLResponse
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    with open("static/dashboard.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)
EOF
else
  echo "⚠️ Route /dashboard already exists. Skipping patch."
fi

# === [3] Create static/dashboard.html if not exists ===
mkdir -p static
cat > static/dashboard.html <<EOF
<!DOCTYPE html>
<html>
<head>
  <title>AI Money Web Dashboard</title>
</head>
<body>
  <h1>📊 AI Strategy Autopilot</h1>
  <button onclick="startStrategy()">▶️ Start</button>
  <button onclick="stopStrategy()">⏹️ Stop</button>
  <button onclick="sendTest()">🧪 Send Test Order</button>
  <select id="strategySelector">
    <option value="momentum">Momentum</option>
    <option value="crossover">Crossover</option>
  </select>
  <script>
    function startStrategy() {
      fetch("/api/toggle_mode", { method: "POST" });
    }
    function stopStrategy() {
      fetch("/api/toggle_mode", { method: "POST" });
    }
    function sendTest() {
      fetch("/api/signal", { method: "POST", body: JSON.stringify({ test: true }) });
    }
    document.getElementById("strategySelector").addEventListener("change", function() {
      fetch("/api/strategy_config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy: this.value })
      });
    });
  </script>
</body>
</html>
EOF
echo "✅ dashboard.html created or updated."

# === [4] Restart supervisor-controlled backend ===
echo "🔁 Restarting backend using supervisor (if running)..."
pkill -f uvicorn || true
sleep 2
source venv/bin/activate && nohup uvicorn backend.main:app --reload > logs/backend.log 2>&1 &

# === [5] All done! ===
echo "🎯 Phase 221–240 complete. Visit http://localhost:8000/dashboard to test."
echo "📄 Logs: tail -f logs/backend.log logs/strategy.log"


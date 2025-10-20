#!/bin/bash

echo "🚀 Starting AI Money Web Unified Script..."

# Step 1: Start FastAPI Backend
echo "🔧 Starting FastAPI backend..."
uvicorn fastapi_app:app --reload &

# Step 2: Start Paper Trading Supervisor
echo "📈 Starting paper trading..."
make start-paper

# Step 3: Sync WebSockets (Fix Loading Issue)
echo "🔌 Rebinding WebSocket listeners..."
node tools/ws_reconnect_patch.js

# Step 4: Apply Dark Theme + Tailwind Pro Layout
echo "🎨 Applying Pro Dashboard Skin (Tailwind + Chart.js)..."
npm install tailwindcss chart.js
npx tailwindcss -i ./static/input.css -o ./static/output.css --watch &
cp tools/themes/pro_dashboard_skin.css static/style.css

# Step 5: Auto-heal (Syntax + Router Validator)
echo "🛡️ Running syntax healer + router validator..."
python3 tools/auto_heal.py

# Step 6: Activate AI Live Signal Stream
echo "🧠 Activating AI signal stream..."
python3 tools/ai_money_pipeline_phase16to18.py --live

# Step 7: Start DB Snapshot Sync
echo "🗄️ Starting Supabase snapshot + backup..."
python3 tools/db_snapshotter.py &

# Step 8: Run Validation Tests
echo "✅ Running validation test suite..."
pytest tests/test_integrations.py

echo "🎉 AI Money Web is LIVE! Visit http://127.0.0.1:8000/dashboard"

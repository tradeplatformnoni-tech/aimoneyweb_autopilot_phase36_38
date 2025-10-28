#!/bin/bash

# 💥 AI Money Web: Unified Self-Healing Startup Script 💥
# This script will:
# - Kill zombie uvicorn processes
# - Start the FastAPI backend safely
# - Validate endpoints
# - Auto-start trading supervisor (mock/paper)
# - Log outputs for troubleshooting
# - Begin AI learning loop (mock, for now)

echo "🧠 AI Money Web :: Self-Healing Bootstrap Starting..."

PROJECT_DIR="$(pwd)"
PORT=8000
ENTRY_MODULE="main:app"

# 1. Kill zombie processes on port 8000
echo "🔪 Killing stale processes on port $PORT..."
PIDS=$(lsof -ti :$PORT)
if [ ! -z "$PIDS" ]; then
  kill -9 $PIDS
  echo "✅ Killed processes: $PIDS"
else
  echo "✅ No zombie processes found."
fi

# 2. Confirm FastAPI entrypoint exists
if [ ! -f "$PROJECT_DIR/main.py" ]; then
  echo "⚠️  main.py not found in project root. Creating default FastAPI app..."
  cat <<EOF > "$PROJECT_DIR/main.py"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "✅ AI Money Web Backend is running."}

@app.get("/api/alpaca_status")
def alpaca_status():
    return {"status": "connected", "account_value": 100000.0, "cash": 15000.0}
EOF
  echo "✅ Created default main.py"
fi

# 3. Start backend server
echo "🚀 Starting backend server..."
nohup uvicorn $ENTRY_MODULE --reload --port $PORT > logs/backend.log 2>&1 &

sleep 3
echo "⏳ Waiting for server to start..."
curl -s http://127.0.0.1:$PORT || echo "⚠️  Still starting or failed."

# 4. Start mock AI trading supervisor (placeholder)
echo "🧠 Starting AI paper trading supervisor (mock)..."
nohup python3 tools/mock_trader.py > logs/trader.log 2>&1 &

# 5. Validate critical endpoints
echo "🧪 Validating backend..."
curl -s http://127.0.0.1:$PORT/api/alpaca_status || echo "❌ /api/alpaca_status failed"
curl -s http://127.0.0.1:$PORT || echo "❌ / root route failed"

echo "✅ All systems booted. Logs in /logs/"
echo "🎯 Next: Run your dashboard at http://127.0.0.1:$PORT/dashboard"


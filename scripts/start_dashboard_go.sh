#!/bin/bash
# World-Class Go Dashboard Startup Script
# Fast, reliable, production-ready

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
DASHBOARD_DIR="$ROOT/dashboard_go"
BINARY_NAME="dashboard_go"
PORT="${NEOLIGHT_DASHBOARD_PORT:-8100}"

mkdir -p "$LOG_DIR"

echo "🚀 Starting NeoLight Dashboard (Go) on port $PORT..."

# Check if Go is installed
if ! command -v go &> /dev/null; then
    echo "❌ Go is not installed. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install go
        else
            echo "❌ Please install Homebrew first: https://brew.sh"
            exit 1
        fi
    else
        echo "❌ Please install Go: https://go.dev/dl/"
        exit 1
    fi
fi

# Check if binary exists, if not build it
if [ ! -f "$DASHBOARD_DIR/$BINARY_NAME" ]; then
    echo "📦 Building Go dashboard binary..."
    cd "$DASHBOARD_DIR"
    go mod download
    go build -ldflags="-s -w" -o "$BINARY_NAME" main.go
    if [ ! -f "$BINARY_NAME" ]; then
        echo "❌ Build failed"
        exit 1
    fi
    echo "✅ Binary built successfully"
    cd "$ROOT"
fi

# Stop any existing dashboard instances
echo "🛑 Stopping existing dashboard instances..."
pkill -f "$BINARY_NAME" || pkill -f "uvicorn.*$PORT" || true
sleep 2

# Start Go dashboard
echo "🚀 Launching Go dashboard..."
cd "$DASHBOARD_DIR"
nohup ./$BINARY_NAME > "$LOG_DIR/dashboard_go.log" 2>&1 &
DASH_PID=$!
cd "$ROOT"

echo "⏳ Waiting for dashboard to start..."
sleep 3

# Health check with retries
MAX_RETRIES=20
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo "✅ Dashboard is running on port $PORT"
        echo "   PID: $DASH_PID"
        echo "   Health: http://localhost:$PORT/health"
        echo "   Metrics: http://localhost:$PORT/meta/metrics"
        echo "   Status: http://localhost:$PORT/status"
        exit 0
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 1
done

echo "⚠️  Dashboard may still be starting (checked $MAX_RETRIES times)"
echo "   Check logs: tail -f $LOG_DIR/dashboard_go.log"
echo "   PID: $DASH_PID"
exit 1


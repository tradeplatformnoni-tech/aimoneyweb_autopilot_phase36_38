#!/usr/bin/env bash
# World-class sports betting system launcher
set -euo pipefail

ROOT="${HOME}/neolight"
cd "$ROOT"

source venv/bin/activate
export PYTHONPATH="$ROOT"
export PYTHONUNBUFFERED=1

set -a
. ./.env
set +a

echo "🚀 NeoLight Sports System - Full Stack Startup"
echo "================================================"

# Refresh data
echo "📊 Refreshing NBA data..."
python scripts/ingest_nba_data.py --seasons 2025,2024,2023

echo "⚽ Refreshing Soccer data..."
python scripts/ingest_soccer_data.py --seasons 2025,2024,2023 --leagues EPL,LaLiga,SerieA --odds

# Run analytics
echo "🧠 Running sports analytics..."
python agents/sports_analytics_agent.py &
ANALYTICS_PID=$!

# Wait for predictions
sleep 10

# Run Einstein layer
echo "🔬 Running Einstein meta-layer..."
python agents/sports_einstein_layer.py

# Launch arbitrage scanner
echo "💰 Launching arbitrage scanner..."
nohup python agents/sports_arbitrage_scanner.py >> logs/arbitrage_scanner.log 2>&1 &

echo "✅ All systems operational!"
echo "📁 Check state/ for outputs:"
echo "   - sports_predictions_nba.json"
echo "   - sports_predictions_soccer.json"
echo "   - sports_einstein_queue.json"
echo "   - sports_arbitrage_opportunities.json"

#!/bin/bash
# Start SmartTrader with proper environment
set -e

cd "$(dirname "$0")/.."
source ~/.neolight_secrets
source venv/bin/activate

echo "🚀 Starting SmartTrader (Enhanced with 8 Strategies)"
echo ""

# Check dependencies
python3 -c "import yfinance" 2>/dev/null || {
    echo "⚠️  Installing yfinance..."
    pip install yfinance >/dev/null 2>&1
}

# Ensure logs directory
mkdir -p logs

# Start SmartTrader
exec python3 trader/smart_trader.py 2>&1 | tee logs/smart_trader_$(date +%Y%m%d).log


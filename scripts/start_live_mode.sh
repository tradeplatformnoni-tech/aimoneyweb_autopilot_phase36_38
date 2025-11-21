#!/bin/bash
# NeoLight Live Trading Mode Launcher
# Phase 2900-3100: Real Trading Execution
# =========================================
# Starts SmartTrader in LIVE_MODE with safety controls
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Colors
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }

# Check for Alpaca API keys
if [ -z "$ALPACA_API_KEY" ] || [ -z "$ALPACA_SECRET_KEY" ]; then
    red "❌ ALPACA_API_KEY and ALPACA_SECRET_KEY must be set!"
    red "   Export them or add to your .env file"
    exit 1
fi

# Check if LIVE_MODE is explicitly requested
if [ "$1" != "confirm" ]; then
    red "⚠️  WARNING: This will start LIVE TRADING with real money!"
    yellow "   Make sure you have:"
    yellow "   1. Tested in PAPER_MODE first"
    yellow "   2. Verified API keys are correct"
    yellow "   3. Set appropriate risk limits"
    yellow "   4. Reviewed circuit breaker settings"
    echo ""
    yellow "   To proceed, run: $0 confirm"
    exit 1
fi

green "🚀 Starting SmartTrader in LIVE_MODE..."

# Set trading mode
export TRADING_MODE="LIVE_MODE"
export NEOLIGHT_USE_ALPACA_QUOTES="true"

# Ensure state directories exist
mkdir -p "$ROOT_DIR/state"
mkdir -p "$ROOT_DIR/runtime"
mkdir -p "$ROOT_DIR/logs"

# Check Python
if ! command -v python3 &> /dev/null; then
    red "❌ python3 not found"
    exit 1
fi

# Run SmartTrader
green "📊 Launching SmartTrader with live execution..."
python3 "$ROOT_DIR/trader/smart_trader.py"


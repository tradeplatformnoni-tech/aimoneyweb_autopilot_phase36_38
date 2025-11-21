#!/bin/bash
# NeoLight Paper Trading Launcher - World-Class Enterprise Setup
# ==============================================================
# Safe, monitored paper trading with full Portfolio Core integration
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Colors
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
blue(){ printf "\033[0;34m%s\033[0m\n" "$*"; }

# Banner
echo ""
green "╔════════════════════════════════════════════════════════════╗"
green "║     🚀 NeoLight Paper Trading - Enterprise Launch         ║"
green "║     Portfolio Core Integration (Phases 2500-3500)         ║"
green "╚════════════════════════════════════════════════════════════╝"
echo ""

# Environment check
green "📋 Environment Check..."
echo "   Working Directory: $ROOT_DIR"
echo "   Python: $(python3 --version 2>/dev/null || echo 'Not found')"
echo "   Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Configuration
green "⚙️  Configuration Setup..."

# Portfolio optimization cycle (default: 100)
PORTFOLIO_OPT_CYCLE="${PORTFOLIO_OPT_CYCLE:-100}"
echo "   PORTFOLIO_OPT_CYCLE: $PORTFOLIO_OPT_CYCLE cycles"
export PORTFOLIO_OPT_CYCLE

# Risk assessment cycle (default: 200)
RISK_ASSESSMENT_CYCLE="${RISK_ASSESSMENT_CYCLE:-200}"
echo "   RISK_ASSESSMENT_CYCLE: $RISK_ASSESSMENT_CYCLE cycles"
export RISK_ASSESSMENT_CYCLE

# Trading mode (default: PAPER_TRADING_MODE)
TRADING_MODE="${TRADING_MODE:-PAPER_TRADING_MODE}"
echo "   TRADING_MODE: $TRADING_MODE"
export TRADING_MODE

# Stop loss distance (default: 2%)
STOP_LOSS_DISTANCE="${STOP_LOSS_DISTANCE:-0.02}"
echo "   STOP_LOSS_DISTANCE: $STOP_LOSS_DISTANCE (2%)"
export STOP_LOSS_DISTANCE

# Ensure directories exist
mkdir -p "$ROOT_DIR/state"
mkdir -p "$ROOT_DIR/runtime"
mkdir -p "$ROOT_DIR/logs"
green "   ✅ State directories ready"
echo ""

# Display configuration summary
blue "📊 Launch Configuration Summary"
echo "   ────────────────────────────────────────"
echo "   Mode: $TRADING_MODE"
echo "   Portfolio Rebalance: Every $PORTFOLIO_OPT_CYCLE cycles"
echo "   Risk Assessment: Every $RISK_ASSESSMENT_CYCLE cycles"
echo "   Stop Loss: 2%"
echo "   Logs: $ROOT_DIR/logs/smart_trader.log"
echo "   ────────────────────────────────────────"
echo ""

# Launch
green "🚀 Launching SmartTrader..."
echo ""

# Set PYTHONPATH
export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

# Launch SmartTrader
python3 "$ROOT_DIR/trader/smart_trader.py"

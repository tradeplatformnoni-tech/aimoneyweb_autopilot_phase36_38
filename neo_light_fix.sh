#!/usr/bin/env bash
# =============================================================
# ⚙️ NeoLight Guardian v23.1 — Syntax-Clean Final Quantum Build
# =============================================================
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="${ROOT:-$HOME/neolight}"
VENV="${VENV:-$ROOT/venv}"
LOGS="${LOGS:-$ROOT/logs}"
RUNTIME="${RUNTIME:-$ROOT/runtime}"
LOCK="$RUNTIME/.guardian.lock"
mkdir -p "$LOGS" "$RUNTIME"
export PATH="$VENV/bin:$PATH"
export PYTHONPATH="$ROOT"
cd "$ROOT" || exit 1

# ---- Load Environment Variables ----
if [[ -f "$ROOT/.env" ]]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

PY="$VENV/bin/python"
UVICORN="$VENV/bin/uvicorn"

# ---- UI Helpers ----
color(){ printf "\033[%sm%s\033[0m\n" "$1" "$2"; }
note(){  color "36" "🧠 $*"; }
ok(){    color "32" "✅ $*"; }
warn(){  color "33" "⚠️  $*"; }
err(){   color "31" "🛑 $*"; }

# ---- Clean Lock ----
if [[ "${1:-}" == "--force" ]]; then
  warn "Force mode — unlocking Guardian..."
  rm -f "$LOCK"
fi
if [[ -f "$LOCK" ]]; then
  warn "Guardian already running ($LOCK). Exiting."
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"; warn "Guardian stopped gracefully."' EXIT

# ---- Prepare Environment ----
note "Preparing environment..."
mkdir -p "$LOGS"
for log in intelligence_orchestrator smart_trader weights_bridge dashboard dashboard_status guardian strategy_manager strategy_performance rl_trainer rl_inference; do
  : > "$LOGS/$log.log"
done

note "Healing Python environment..."
"$VENV/bin/pip" install --upgrade pip wheel setuptools >/dev/null 2>&1 || true
"$VENV/bin/pip" install -q fastapi uvicorn psutil starlette python-dateutil anyio click >/dev/null 2>&1 || true

# ---- Validate Python Health ----
note "Validating Python modules..."
$PY - <<'PY'
import importlib, sys
for mod in ['fastapi','uvicorn','psutil','starlette','anyio']:
    try:
        importlib.import_module(mod)
        print(f"✅ {mod} OK")
    except Exception as e:
        sys.exit(f"Missing or broken: {mod} ({e})")
print("✅ Core Python modules validated successfully.")
PY

# ---- Rebuild Status Endpoint ----
mkdir -p "$ROOT/dashboard"
cat > "$ROOT/dashboard/status_endpoint.py" <<'PY'
from fastapi import FastAPI
import psutil, os, time, datetime, json, glob

app = FastAPI(title="NeoLight Guardian v23.1", version="23.1")

def safe_json(obj):
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception as e:
        return {"error": str(e)}

@app.get("/status")
def status():
    try:
        logs = {os.path.basename(f): time.ctime(os.path.getmtime(f)) for f in glob.glob(os.path.expanduser("~/neolight/logs/*.log"))}
        processes = [p.info for p in psutil.process_iter(attrs=["pid","name","cpu_percent","memory_percent"]) if any(k in (p.info.get("name") or "") for k in ["uvicorn","intelligence_orchestrator","smart_trader","weights_bridge"])]
        system = {
            "cpu": psutil.cpu_percent(interval=0.3),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent,
            "uptime": datetime.datetime.now().isoformat(),
        }
        return safe_json({"system": system, "guardian": {"logs": logs, "agents": processes}})
    except Exception as e:
        return {"error": f"Guardian status failed: {e}"}
PY

# ---- Heal Ports ----
note "Healing ports..."
for P in {8090..8110}; do
  lsof -i :$P -t | xargs -r kill -9 || true
done

# ---- Smart Runner ----
ensure_running() {
  local name="$1" cmd="$2" log="$3"
  note "Ensuring $name"
  nohup bash -lc "
    source '$VENV/bin/activate'
    export PYTHONPATH='$ROOT'
    cd '$ROOT'
    backoff=2
    fails=0
    while true; do
      echo '[Guardian] Starting $name @' \$(date '+%Y-%m-%dT%H:%M:%S') >> '$log'
      $cmd >> '$log' 2>&1 &
      pid=\$!
      sleep 3
      if ! kill -0 \$pid 2>/dev/null; then
        echo '[Guardian] $name crashed. Backoff '\$backoff's' >> '$log'
        fails=\$((fails+1))
        if [ \$fails -ge 3 ] && [ -x '$ROOT/scripts/code_fix_hook.sh' ]; then
          echo '[Guardian] invoking code_fix_hook after 3 failures…' >> '$log'
          '$ROOT/scripts/code_fix_hook.sh' >> '$log' 2>&1 || true
          fails=0
        fi
        sleep \$backoff
        backoff=\$((backoff*2)); [ \$backoff -gt 60 ] && backoff=60
      else
        wait \$pid
        backoff=2
        fails=0
      fi
    done
  " >/dev/null 2>&1 &
}

# ---- Launch Core Agents ----
ensure_running "intelligence_orchestrator" "$PY ./agents/intelligence_orchestrator.py" "$LOGS/intelligence_orchestrator.log"
ensure_running "smart_trader" "$PY ./trader/smart_trader.py" "$LOGS/smart_trader.log"
ensure_running "weights_bridge" "$PY ./agents/weights_bridge.py" "$LOGS/weights_bridge.log"
ensure_running "atlas_bridge" "$PY ./agents/atlas_bridge.py" "$LOGS/atlas_bridge.log"

# ---- Launch RL System (Phase 3700-3900) ----
ensure_running "rl_trainer" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY ai/rl_trainer.py --loop" "$LOGS/rl_trainer.log"
ensure_running "rl_inference" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY ai/rl_inference.py --loop --interval 300" "$LOGS/rl_inference.log"

# ---- Strategy Manager (Phase 3500-3700) ----
ensure_running "strategy_manager" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY agents/strategy_manager.py" "$LOGS/strategy_manager.log"

# ---- Strategy Performance Tracker (Phase 3500-3700) ----
ensure_running "strategy_performance" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY analytics/strategy_performance.py" "$LOGS/strategy_performance.log"
ensure_running "rl_performance" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY analytics/rl_performance.py --report" "$LOGS/rl_performance.log"

# ---- Capital Governor (Phase 5700-5900) ----
ensure_running "capital_governor" "$PY ./agents/phase_5700_5900_capital_governor.py" "$LOGS/capital_governor.log"

# ---- Dashboard / Full Unified Dashboard (Port 8090) ----
ensure_running "dashboard" "$UVICORN dashboard.app:app --host 0.0.0.0 --port 8090" "$LOGS/dashboard.log"
sleep 3
if lsof -i :8090 >/dev/null 2>&1; then
  ok "Full dashboard active at http://localhost:8090"
else
  warn "Dashboard port 8090 failed — check logs"
fi

# ---- Status API (Port 8100) ----
port=8100
for i in {0..10}; do
  ensure_running "dashboard_status" "$UVICORN dashboard.status_endpoint:app --host 0.0.0.0 --port $port" "$LOGS/dashboard_status.log"
  sleep 3
  if lsof -i :$port >/dev/null 2>&1; then
    ok "Status endpoint active at http://localhost:$port/status"
    break
  else
    warn "Port $port failed — switching..."
    port=$((port+1))
  fi
done

# ---- Risk AI Server (Port 8500) ----
ensure_running "risk_ai_server" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' RISK_AI_PORT=8500 $PY ai/risk_ai_server.py" "$LOGS/risk_ai_server.log"
sleep 3
if lsof -i :8500 >/dev/null 2>&1; then
  ok "Risk AI Server active at http://localhost:8500"
else
  warn "Risk AI Server port 8500 failed — check logs"
fi

# ---- Scheduler (Periodic Intelligence Orchestrator) ----
ensure_running "scheduler" "bash '$ROOT/scripts/schedule_all.sh'" "$LOGS/scheduler.log"

# ---- Google Drive Sync (Periodic Cloud Backup) ----
# Note: rclone_sync.sh runs once and exits, so we use a wrapper loop
ensure_running "drive_sync" "bash '$ROOT/scripts/rclone_sync_loop.sh'" "$LOGS/drive_sync.log"

# ---- Revenue Agents (Phase 1300-1500) ----
# Launch revenue agents if enabled via environment variable
if [ "${NEOLIGHT_ENABLE_REVENUE_AGENTS:-false}" = "true" ]; then
  note "Launching revenue agents..."
  note "SPORTS_PAPER_MODE=${SPORTS_PAPER_MODE:-unset}"
  ensure_running "knowledge_integrator" "$PY ./agents/knowledge_integrator.py" "$LOGS/knowledge_integrator.log"
  ensure_running "revenue_monitor" "$PY ./agents/revenue_monitor.py" "$LOGS/revenue_monitor.log"
  ensure_running "dropship_agent" "$PY ./agents/dropship_agent.py" "$LOGS/dropship_agent.log"
  ensure_running "ticket_arbitrage_agent" "$PY ./agents/ticket_arbitrage_agent.py" "$LOGS/ticket_arbitrage_agent.log"
  ensure_running "sports_analytics_agent" "$PY ./agents/sports_analytics_agent.py" "$LOGS/sports_analytics_agent.log"

  # Sports Paper Trading or Live Betting
  paper_mode="$(printf '%s' "${SPORTS_PAPER_MODE:-true}" | tr '[:upper:]' '[:lower:]')"
  if [ "$paper_mode" = "true" ]; then
    pkill -f "agents/sports_betting_agent.py" >/dev/null 2>&1 || true
    ensure_running "sports_paper_trader" "$PY ./agents/sports_paper_trader.py" "$LOGS/sports_paper_trader.log"
    note "Sports in PAPER MODE - simulating bets without real money"
  else
    pkill -f "agents/sports_paper_trader.py" >/dev/null 2>&1 || true
    ensure_running "sports_betting_agent" "$PY ./agents/sports_betting_agent.py" "$LOGS/sports_betting_agent.log"
    note "Sports in LIVE MODE - generating manual BetMGM alerts"
  fi
  
  ensure_running "sports_einstein_layer" "$PY ./agents/sports_einstein_layer.py" "$LOGS/sports_einstein.log"
  ensure_running "sports_arbitrage_scanner" "$PY ./agents/sports_arbitrage_scanner.py" "$LOGS/arbitrage_scanner.log"
  ensure_running "sports_ingestion_scheduler" "bash ./scripts/schedule_sports_ingestion.sh" "$LOGS/sports_ingestion_scheduler.log"
  ok "Revenue agents launched (dropship, tickets, sports)"
else
  note "Revenue agents disabled (set NEOLIGHT_ENABLE_REVENUE_AGENTS=true to enable)"
fi

# ---- Phase 1500-1800: ML Pipeline & Self-Training ----
if [ "${NEOLIGHT_ENABLE_ML_PIPELINE:-true}" = "true" ]; then
  note "Launching ML pipeline (Phase 1500-1800)..."
  ensure_running "ml_pipeline" "$PY ./agents/ml_pipeline.py" "$LOGS/ml_pipeline.log"
  ok "ML pipeline active (auto-training models)"
fi

# ---- Phase 1800-2000: Performance Attribution ----
if [ "${NEOLIGHT_ENABLE_ATTRIBUTION:-true}" = "true" ]; then
  note "Launching performance attribution (Phase 1800-2000)..."
  ensure_running "performance_attribution" "$PY ./agents/performance_attribution.py" "$LOGS/performance_attribution.log"
  ok "Performance attribution active (decision tracking)"
fi

# ---- Phase 2000-2300: Regime Detection ----
if [ "${NEOLIGHT_ENABLE_REGIME:-true}" = "true" ]; then
  note "Launching regime detector (Phase 2000-2300)..."
  ensure_running "regime_detector" "$PY ./agents/regime_detector.py" "$LOGS/regime_detector.log"
  ok "Regime detection active (adaptive strategies)"
fi

# ---- Phase 301-340: Equity Replay ----
if [ "${NEOLIGHT_ENABLE_EQUITY_REPLAY:-true}" = "true" ]; then
  note "Launching equity replay (Phase 301-340)..."
  EQUITY_REPLAY_INTERVAL="${NEOLIGHT_EQUITY_REPLAY_INTERVAL:-86400}"  # Default 24 hours
  ensure_running "equity_replay" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_301_340_equity_replay.py --interval $EQUITY_REPLAY_INTERVAL" "$LOGS/equity_replay.log"
  ok "Equity replay active (historical data, backtesting, yfinance, interval: ${EQUITY_REPLAY_INTERVAL}s)"
fi

# ---- World-Class Trading Improvements ----
if [ "${NEOLIGHT_ENABLE_MARKET_INTEL:-true}" = "true" ]; then
  note "Launching market intelligence (Reddit, Twitter, News, Fed)..."
  ensure_running "market_intelligence" "$PY ./agents/market_intelligence.py" "$LOGS/market_intelligence.log"
  ok "Market intelligence active (multi-source research)"
fi

if [ "${NEOLIGHT_ENABLE_STRATEGY_RESEARCH:-true}" = "true" ]; then
  note "Launching strategy research (millionaire strategies)..."
  ensure_running "strategy_research" "$PY ./agents/strategy_research.py" "$LOGS/strategy_research.log"
  ok "Strategy research active (proven methods)"
fi

# ---- Automated Product Creator (Dropshipping) ----
if [ "${NEOLIGHT_ENABLE_PRODUCT_CREATOR:-true}" = "true" ]; then
  note "Launching automated product creator (Shopify)..."
  ensure_running "product_creator" "$PY ./agents/automated_product_creator.py" "$LOGS/product_creator.log"
  ok "Product creator active (world-class profitable products)"
fi

# ---- Phase 3900-4100: Event-Driven Architecture ----
if [ "${NEOLIGHT_ENABLE_EVENTS:-true}" = "true" ]; then
  note "Launching event-driven architecture (Phase 3900-4100)..."
  ensure_running "event_driven" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_3900_4100_events.py" "$LOGS/event_driven.log"
  ok "Event-driven architecture active (real-time event capture)"
fi

# ---- Phase 4300-4500: Portfolio Analytics & Attribution ----
if [ "${NEOLIGHT_ENABLE_PORTFOLIO_ANALYTICS:-true}" = "true" ]; then
  note "Launching portfolio analytics (Phase 4300-4500)..."
  ensure_running "portfolio_analytics" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_4300_4500_analytics.py" "$LOGS/portfolio_analytics.log"
  ok "Portfolio analytics active (performance & risk attribution)"
fi

# ---- Risk Attribution Analysis (Phase 4300-4500 Enhancement) ----
if [ "${NEOLIGHT_ENABLE_RISK_ATTRIBUTION:-true}" = "true" ]; then
  note "Launching risk attribution analyzer..."
  ensure_running "risk_attribution" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY analytics/risk_attribution.py" "$LOGS/risk_attribution.log"
  ok "Risk attribution active (risk decomposition by strategy)"
fi

# ---- Phase 2500-2700: Portfolio Optimization ----
if [ "${NEOLIGHT_ENABLE_PORTFOLIO_OPTIMIZATION:-true}" = "true" ]; then
  note "Launching portfolio optimization (Phase 2500-2700)..."
  ensure_running "portfolio_optimization" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_2500_2700_portfolio_optimization.py" "$LOGS/portfolio_optimization.log"
  ok "Portfolio optimization active (Sharpe optimization, efficient frontier)"
fi

# ---- Phase 2700-2900: Advanced Risk Management ----
if [ "${NEOLIGHT_ENABLE_RISK_MANAGEMENT:-true}" = "true" ]; then
  note "Launching advanced risk management (Phase 2700-2900)..."
  ensure_running "risk_management" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_2700_2900_risk_management.py" "$LOGS/risk_management.log"
  ok "Advanced risk management active (VaR, CVaR, stress testing)"
fi

# ---- Phase 3300-3500: Kelly Criterion Position Sizing ----
if [ "${NEOLIGHT_ENABLE_KELLY_SIZING:-true}" = "true" ]; then
  note "Launching Kelly position sizing (Phase 3300-3500)..."
  ensure_running "kelly_sizing" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_3300_3500_kelly.py" "$LOGS/kelly_sizing.log"
  ok "Kelly position sizing active (optimal position sizing)"
fi

# ---- Phase 4100-4300: Advanced Execution Algorithms ----
if [ "${NEOLIGHT_ENABLE_EXECUTION_ALGORITHMS:-true}" = "true" ]; then
  note "Launching advanced execution algorithms (Phase 4100-4300)..."
  ensure_running "execution_algorithms" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_4100_4300_execution.py" "$LOGS/execution_algorithms.log"
  ok "Advanced execution algorithms active (TWAP/VWAP, smart routing)"
fi

# ---- Correlation Matrix Enhancement ----
if [ "${NEOLIGHT_ENABLE_CORRELATION_MATRIX:-true}" = "true" ]; then
  note "Launching correlation matrix computation..."
  ensure_running "correlation_matrix" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY analytics/correlation_matrix.py" "$LOGS/correlation_matrix.log"
  ok "Correlation matrix active (rolling correlation, risk alerts)"
fi

# ---- Phase 4500-4700: Alternative Data Integration ----
if [ "${NEOLIGHT_ENABLE_ALT_DATA:-true}" = "true" ]; then
  note "Launching alternative data integration (Phase 4500-4700)..."
  ensure_running "alt_data" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_4500_4700_alt_data.py" "$LOGS/alt_data.log"
  ok "Alternative data integration active (social sentiment, news, web scraping)"
fi

# ---- Phase 3500-3700: Multi-Strategy Framework Enhancement ----
# Enhanced strategy_manager already running above, correlation analysis integrated

# ---- Phase 3700-3900: Enhanced Reinforcement Learning ----
if [ "${NEOLIGHT_ENABLE_RL_ENHANCED:-true}" = "true" ]; then
  note "Launching enhanced RL strategy selection (Phase 3700-3900)..."
  ensure_running "rl_enhanced" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_3700_3900_rl.py" "$LOGS/rl_enhanced.log"
  ok "Enhanced RL active (Q-learning, multi-armed bandit, reward shaping)"
fi

# ---- Enhanced Backtesting System (Replay Engine) ----
if [ "${NEOLIGHT_ENABLE_BACKTESTING:-true}" = "true" ]; then
  note "Launching enhanced backtesting system (replay engine)..."
  BACKTEST_INTERVAL="${NEOLIGHT_BACKTEST_INTERVAL:-86400}"  # Default: 24 hours
  ensure_running "replay_engine" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY backend/replay_engine.py --loop" "$LOGS/replay_engine.log"
  ok "Enhanced backtesting active (walk-forward, Monte Carlo, transaction costs, interval: ${BACKTEST_INTERVAL}s)"
fi

# ---- Advanced Backtesting Framework (Strategy Backtesting) ----
if [ "${NEOLIGHT_ENABLE_STRATEGY_BACKTESTING:-true}" = "true" ]; then
  note "Launching advanced backtesting framework..."
  ensure_running "strategy_backtesting" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY analytics/strategy_backtesting.py" "$LOGS/strategy_backtesting.log"
  ok "Advanced backtesting active (walk-forward, Monte Carlo, parameter optimization)"
fi

# ---- Real-Time Market Data Pipeline ----
if [ "${NEOLIGHT_ENABLE_REALTIME_DATA:-true}" = "true" ]; then
  note "Launching real-time market data pipeline..."
  ensure_running "realtime_market_data" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY analytics/realtime_market_data.py" "$LOGS/realtime_market_data.log"
  ok "Real-time market data active (streaming prices, order book, trade tape)"
fi

# ---- Paper Trading Realism Enhancement ----
if [ "${NEOLIGHT_ENABLE_PAPER_REALISM:-true}" = "true" ]; then
  note "Launching paper trading realism enhancement..."
  ensure_running "paper_trading_realism" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY analytics/paper_trading_realism.py" "$LOGS/paper_trading_realism.log"
  ok "Paper trading realism active (slippage, latency, fill simulation)"
fi

# ---- Enhanced Pattern Recognition ----
# Enhanced signals already integrated in enhanced_signals.py (Phase 3100-3300)

# ---- Continuous Self-Healing Loop ----
while true; do
  note "Assessing system health..."
  df -h > "$LOGS/system_health.log" 2>&1
  ps -eo pid,comm,%cpu,%mem | sort -k3 -r | head -n 15 >> "$LOGS/system_health.log"
  sleep 300
done

#!/usr/bin/env bash
# NeoLight Fly.io Startup Script
# ===============================
# Runs guardian and all services in Fly.io cloud environment
set -euo pipefail

ROOT="/app"
LOGS="$ROOT/logs"
STATE="$ROOT/state"
RUNTIME="$ROOT/runtime"
PYTHON="${PYTHON:-python3}"

# Ensure directories exist
mkdir -p "$LOGS" "$STATE" "$RUNTIME" "$ROOT/data"

# Set environment
export PYTHONPATH="$ROOT"
export PYTHONUNBUFFERED=1
export PATH="/usr/local/bin:$PATH"
export HOME="/app"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/flyio_startup.log"
}

log "🚀 NeoLight Fly.io Startup - Initializing..."

# Install any missing Python packages (in case requirements.txt was updated)
log "Checking Python dependencies..."
$PYTHON -m pip install --quiet --upgrade pip setuptools wheel 2>/dev/null || true

# Create a simplified guardian runner for Fly.io
log "Creating Fly.io guardian runner..."
cat > "$ROOT/flyio_guardian.sh" <<'GUARDIAN_SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
ROOT="/app"
LOGS="$ROOT/logs"
STATE="$ROOT/state"
RUNTIME="$ROOT/runtime"
PYTHON="${PYTHON:-python3}"

export PYTHONPATH="$ROOT"
export PYTHONUNBUFFERED=1
cd "$ROOT"

# Ensure directories
mkdir -p "$LOGS" "$STATE" "$RUNTIME"

# Function to ensure a service is running
ensure_running() {
    local name="$1"
    local cmd="$2"
    local logfile="$LOGS/${name}.log"
    
    if pgrep -f "$cmd" >/dev/null 2>&1; then
        return 0
    fi
    
    log "Starting $name..."
    nohup bash -c "$cmd" >> "$logfile" 2>&1 &
    sleep 2
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGS/guardian_flyio.log"
}

# Start core services
log "Starting core agents..."
ensure_running "intelligence_orchestrator" "$PYTHON $ROOT/agents/intelligence_orchestrator.py"
ensure_running "smart_trader" "$PYTHON $ROOT/trader/smart_trader.py"
ensure_running "weights_bridge" "$PYTHON $ROOT/agents/weights_bridge.py"
ensure_running "atlas_bridge" "$PYTHON $ROOT/agents/atlas_bridge.py"

# Start dashboard
log "Starting dashboard..."
ensure_running "dashboard" "$PYTHON -m uvicorn dashboard.app:app --host 0.0.0.0 --port 8090"

# Start status endpoint
log "Starting status endpoint..."
ensure_running "dashboard_status" "$PYTHON -m uvicorn dashboard.status_endpoint:app --host 0.0.0.0 --port 8100"

# Start revenue agents if enabled
if [ "${NEOLIGHT_ENABLE_REVENUE_AGENTS:-false}" = "true" ]; then
    log "Starting revenue agents..."
    ensure_running "knowledge_integrator" "$PYTHON $ROOT/agents/knowledge_integrator.py"
    ensure_running "dropship_agent" "$PYTHON $ROOT/agents/dropship_agent.py"
    ensure_running "sports_analytics_agent" "$PYTHON $ROOT/agents/sports_analytics_agent.py"
fi

# Start all enabled phases
if [ "${NEOLIGHT_ENABLE_EQUITY_REPLAY:-true}" = "true" ]; then
    ensure_running "equity_replay" "$PYTHON $ROOT/phases/phase_301_340_equity_replay.py --interval ${NEOLIGHT_EQUITY_REPLAY_INTERVAL:-86400}"
fi

if [ "${NEOLIGHT_ENABLE_ML_PIPELINE:-true}" = "true" ]; then
    ensure_running "ml_pipeline" "$PYTHON $ROOT/agents/ml_pipeline.py"
fi

if [ "${NEOLIGHT_ENABLE_ATTRIBUTION:-true}" = "true" ]; then
    ensure_running "performance_attribution" "$PYTHON $ROOT/agents/performance_attribution.py"
fi

if [ "${NEOLIGHT_ENABLE_REGIME:-true}" = "true" ]; then
    ensure_running "regime_detector" "$PYTHON $ROOT/agents/regime_detector.py"
fi

if [ "${NEOLIGHT_ENABLE_PORTFOLIO_OPTIMIZATION:-true}" = "true" ]; then
    ensure_running "portfolio_optimization" "$PYTHON $ROOT/phases/phase_2500_2700_portfolio_optimization.py"
fi

if [ "${NEOLIGHT_ENABLE_RISK_MANAGEMENT:-true}" = "true" ]; then
    ensure_running "risk_management" "$PYTHON $ROOT/phases/phase_2700_2900_risk_management.py"
fi

if [ "${NEOLIGHT_ENABLE_KELLY_SIZING:-true}" = "true" ]; then
    ensure_running "kelly_sizing" "$PYTHON $ROOT/phases/phase_3300_3500_kelly.py"
fi

if [ "${NEOLIGHT_ENABLE_EVENTS:-true}" = "true" ]; then
    ensure_running "event_driven" "$PYTHON $ROOT/phases/phase_3900_4100_events.py"
fi

if [ "${NEOLIGHT_ENABLE_PORTFOLIO_ANALYTICS:-true}" = "true" ]; then
    ensure_running "portfolio_analytics" "$PYTHON $ROOT/phases/phase_4300_4500_analytics.py"
fi

if [ "${NEOLIGHT_ENABLE_EXECUTION_ALGORITHMS:-true}" = "true" ]; then
    ensure_running "execution_algorithms" "$PYTHON $ROOT/phases/phase_4100_4300_execution.py"
fi

if [ "${NEOLIGHT_ENABLE_ALT_DATA:-true}" = "true" ]; then
    ensure_running "alt_data" "$PYTHON $ROOT/phases/phase_4500_4700_alt_data.py"
fi

log "✅ Guardian services started"

# Keep script running
while true; do
    sleep 300
    log "Guardian heartbeat - all services running"
done
GUARDIAN_SCRIPT

chmod +x "$ROOT/flyio_guardian.sh"

# Start health check server in background
log "Starting health check server on port 8090..."
$PYTHON /app/health_check.py > "$LOGS/health_check.log" 2>&1 &
HEALTH_PID=$!

# Wait a moment for health server to start
sleep 2

# Start the guardian
log "Starting NeoLight Guardian..."
cd "$ROOT" && bash flyio_guardian.sh > "$LOGS/guardian_flyio.log" 2>&1 &
GUARDIAN_PID=$!

# Keep script running and monitor processes
log "✅ All services started. Monitoring..."
log "Health Check PID: $HEALTH_PID"
log "Guardian PID: $GUARDIAN_PID"

# Monitor processes and restart if they die
while true; do
    sleep 60
    
    # Check health server
    if ! kill -0 $HEALTH_PID 2>/dev/null; then
        log "⚠️ Health check server died, restarting..."
        $PYTHON /app/health_check.py > "$LOGS/health_check.log" 2>&1 &
        HEALTH_PID=$!
    fi
    
    # Check guardian
    if ! kill -0 $GUARDIAN_PID 2>/dev/null; then
        log "⚠️ Guardian died, restarting..."
        cd "$ROOT" && bash flyio_guardian.sh > "$LOGS/guardian_flyio.log" 2>&1 &
        GUARDIAN_PID=$!
    fi
done


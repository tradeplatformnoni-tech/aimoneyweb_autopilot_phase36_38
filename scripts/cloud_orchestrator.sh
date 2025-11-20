#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ Cloud Orchestrator - Proactive Failover System                    ║
# ║ Coordinates Render, Cloud Run, and monitoring                     ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
RUN_DIR="$ROOT/run"
LOG_FILE="$LOG_DIR/cloud_orchestrator.log"
PID_FILE="$RUN_DIR/cloud_orchestrator.pid"

mkdir -p "$LOG_DIR" "$RUN_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
ok() { log "${GREEN}✅ $*${NC}"; }
warn() { log "${YELLOW}⚠️  $*${NC}"; }
err() { log "${RED}❌ $*${NC}"; }
info() { log "${CYAN}🎯 $*${NC}"; }

# Check if already running
check_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            warn "Orchestrator already running (PID: $pid)"
            return 1
        else
            # Stale PID file
            rm -f "$PID_FILE"
        fi
    fi
    return 0
}

# Start orchestrator
start() {
    if ! check_running; then
        exit 1
    fi
    
    info "Starting Cloud Orchestrator..."
    
    # Start Render usage monitor
    info "Starting Render usage monitor..."
    nohup python3 "$ROOT/scripts/render_usage_monitor.py" >> "$LOG_DIR/render_monitor.log" 2>&1 &
    local monitor_pid=$!
    echo "$monitor_pid" > "$RUN_DIR/render_monitor.pid"
    ok "Render usage monitor started (PID: $monitor_pid)"
    
    # Start monthly reset handler (check every hour)
    info "Setting up monthly reset handler..."
    # This will be called via cron: 0 * * * * (every hour)
    
    # Save orchestrator PID
    echo $$ > "$PID_FILE"
    ok "Cloud Orchestrator started (PID: $$)"
    
    # Keep running
    info "Orchestrator running. Monitoring Render usage and managing failover..."
    info "Logs: $LOG_FILE"
    info "Status: $RUN_DIR/render_usage_status.json"
    
    # Wait for processes
    wait
}

# Stop orchestrator
stop() {
    info "Stopping Cloud Orchestrator..."
    
    # Stop Render monitor
    if [[ -f "$RUN_DIR/render_monitor.pid" ]]; then
        local monitor_pid=$(cat "$RUN_DIR/render_monitor.pid" 2>/dev/null || echo "")
        if [[ -n "$monitor_pid" ]] && kill -0 "$monitor_pid" 2>/dev/null; then
            kill "$monitor_pid" 2>/dev/null || true
            ok "Render usage monitor stopped"
        fi
        rm -f "$RUN_DIR/render_monitor.pid"
    fi
    
    # Remove PID file
    rm -f "$PID_FILE"
    ok "Cloud Orchestrator stopped"
}

# Status
status() {
    info "Cloud Orchestrator Status:"
    echo ""
    
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            ok "Orchestrator: Running (PID: $pid)"
        else
            warn "Orchestrator: Not running (stale PID file)"
        fi
    else
        warn "Orchestrator: Not running"
    fi
    
    if [[ -f "$RUN_DIR/render_monitor.pid" ]]; then
        local monitor_pid=$(cat "$RUN_DIR/render_monitor.pid" 2>/dev/null || echo "")
        if [[ -n "$monitor_pid" ]] && kill -0 "$monitor_pid" 2>/dev/null; then
            ok "Render Monitor: Running (PID: $monitor_pid)"
        else
            warn "Render Monitor: Not running"
        fi
    else
        warn "Render Monitor: Not running"
    fi
    
    echo ""
    info "Usage Status:"
    if [[ -f "$RUN_DIR/render_usage_status.json" ]] && command -v jq >/dev/null 2>&1; then
        jq . "$RUN_DIR/render_usage_status.json" 2>/dev/null || cat "$RUN_DIR/render_usage_status.json"
    elif [[ -f "$RUN_DIR/render_usage_status.json" ]]; then
        cat "$RUN_DIR/render_usage_status.json"
    else
        warn "No usage status file found"
    fi
    
    echo ""
    info "Failover Status:"
    if [[ -f "$RUN_DIR/failover_status.json" ]] && command -v jq >/dev/null 2>&1; then
        jq . "$RUN_DIR/failover_status.json" 2>/dev/null || cat "$RUN_DIR/failover_status.json"
    elif [[ -f "$RUN_DIR/failover_status.json" ]]; then
        cat "$RUN_DIR/failover_status.json"
    else
        warn "No failover status file found"
    fi
}

# Main
main() {
    case "${1:-start}" in
        "start")
            start
            ;;
        "stop")
            stop
            ;;
        "restart")
            stop
            sleep 2
            start
            ;;
        "status")
            status
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status}"
            exit 1
            ;;
    esac
}

main "$@"



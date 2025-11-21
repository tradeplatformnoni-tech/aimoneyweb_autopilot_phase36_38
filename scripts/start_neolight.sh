#!/bin/bash
# World-Class NeoLight Hybrid Stack Orchestration
# Starts Go Dashboard, Rust Risk Engine, and Python Agents in correct order

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting NeoLight Hybrid Stack${NC}"
echo ""

# Step 1: Go Dashboard
echo -e "${YELLOW}Step 1/6: Starting Go Dashboard...${NC}"
bash "$ROOT/scripts/start_dashboard_go.sh"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Go Dashboard running on :8100${NC}"
else
    echo -e "${RED}❌ Go Dashboard failed to start${NC}"
    exit 1
fi

sleep 3

# Step 2: Rust Risk Engine
echo ""
echo -e "${YELLOW}Step 2/6: Starting Rust Risk Engine...${NC}"
cd "$ROOT/risk_engine_rust"

# Build if needed
if [ ! -f "target/release/risk_engine_rust" ]; then
    echo "📦 Building Rust risk engine..."
    cargo build --release
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Rust build failed${NC}"
        exit 1
    fi
fi

# Check if already running
if pgrep -f "risk_engine_rust" > /dev/null; then
    echo "⚠️  Risk engine already running, stopping..."
    pkill -f "risk_engine_rust" || true
    sleep 2
fi

# Start risk engine
nohup ./target/release/risk_engine_rust > "$LOG_DIR/risk_engine.log" 2>&1 &
RISK_PID=$!
cd "$ROOT"

sleep 3

# Health check
if curl -s http://localhost:8300/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Rust Risk Engine running on :8300${NC}"
else
    echo -e "${YELLOW}⚠️  Risk engine starting (may need a moment)...${NC}"
    sleep 5
    if curl -s http://localhost:8300/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Rust Risk Engine running on :8300${NC}"
    else
        echo -e "${RED}❌ Risk engine failed to start${NC}"
        exit 1
    fi
fi

# Step 3: GPU Risk Engine
echo ""
echo -e "${YELLOW}Step 3/6: Starting GPU Risk Engine (Monte Carlo)...${NC}"
cd "$ROOT/risk_engine_rust_gpu"

if [ ! -f "target/release/risk_engine_rust_gpu" ]; then
    echo "📦 Building GPU risk engine..."
    cargo build --release
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ GPU risk engine build failed${NC}"
        exit 1
    fi
fi

if pgrep -f "risk_engine_rust_gpu" > /dev/null; then
    echo "⚠️  GPU risk engine already running, stopping..."
    pkill -f "risk_engine_rust_gpu" || true
    sleep 2
fi

nohup ./target/release/risk_engine_rust_gpu > "$LOG_DIR/risk_engine_gpu.log" 2>&1 &
cd "$ROOT"

sleep 3

if curl -s http://localhost:8301/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ GPU Risk Engine running on :8301${NC}"
else
    echo -e "${YELLOW}⚠️  GPU Risk Engine starting (may need a moment)...${NC}"
    sleep 5
    if curl -s http://localhost:8301/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ GPU Risk Engine running on :8301${NC}"
    else
        echo -e "${RED}❌ GPU Risk Engine failed to start${NC}"
        exit 1
    fi
fi

# Step 4: AI Risk Scoring Server
echo ""
echo -e "${YELLOW}Step 4/6: Starting AI Risk Scoring Server...${NC}"

if [ -d "$ROOT/venv" ]; then
    source "$ROOT/venv/bin/activate"
fi

pkill -f "risk_ai_server" || true
sleep 1
nohup python3 "$ROOT/ai/risk_ai_server.py" >> "$LOG_DIR/risk_ai_server.log" 2>&1 &
sleep 3

if curl -s http://localhost:8500/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ AI Risk Scoring Server running on :8500${NC}"
else
    echo -e "${YELLOW}⚠️  AI Risk Server starting (may need a moment)...${NC}"
    sleep 5
    if curl -s http://localhost:8500/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ AI Risk Scoring Server running on :8500${NC}"
    else
        echo -e "${YELLOW}⚠️  AI Risk Server may need dependencies (uvicorn, fastapi)${NC}"
    fi
fi

# Step 5: Python Agents
echo ""
echo -e "${YELLOW}Step 5/6: Starting Python Agents...${NC}"

# Check for venv
if [ -d "$ROOT/venv" ]; then
    source "$ROOT/venv/bin/activate"
else
    echo "⚠️  No venv found, using system Python"
fi

# Phase 5600
echo "   Starting Phase 5600 (Hive Telemetry)..."
pkill -f "phase_5600_hive_telemetry" || true
sleep 1
nohup python3 "$ROOT/agents/phase_5600_hive_telemetry.py" >> "$LOG_DIR/phase_5600.log" 2>&1 &
sleep 2

# Phase 5700-5900
echo "   Starting Capital Governor..."
pkill -f "phase_5700_5900_capital_governor" || true
sleep 1
nohup python3 "$ROOT/agents/phase_5700_5900_capital_governor.py" >> "$LOG_DIR/capital_governor.log" 2>&1 &
sleep 2

echo -e "${GREEN}✅ Python Agents started${NC}"

# Step 6: Validation
echo ""
echo -e "${YELLOW}Step 6/6: Validating system...${NC}"
sleep 5

VALIDATION_FAILED=0

# Check Go Dashboard
if curl -s http://localhost:8100/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Go Dashboard: OK${NC}"
else
    echo -e "${RED}❌ Go Dashboard: FAILED${NC}"
    VALIDATION_FAILED=1
fi

# Check Rust Risk Engine
if curl -s http://localhost:8300/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Rust Risk Engine: OK${NC}"
else
    echo -e "${RED}❌ Rust Risk Engine: FAILED${NC}"
    VALIDATION_FAILED=1
fi

# Check GPU Risk Engine
if curl -s http://localhost:8301/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ GPU Risk Engine: OK${NC}"
else
    echo -e "${RED}❌ GPU Risk Engine: FAILED${NC}"
    VALIDATION_FAILED=1
fi

# Check AI Risk Server
if curl -s http://localhost:8500/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ AI Risk Server: OK${NC}"
else
    echo -e "${YELLOW}⚠️  AI Risk Server: Not running (may need dependencies)${NC}"
fi

# Check Python Agents
if pgrep -f "phase_5600_hive_telemetry" > /dev/null; then
    echo -e "${GREEN}✅ Phase 5600: Running${NC}"
else
    echo -e "${RED}❌ Phase 5600: NOT RUNNING${NC}"
    VALIDATION_FAILED=1
fi

if pgrep -f "phase_5700_5900_capital_governor" > /dev/null; then
    echo -e "${GREEN}✅ Capital Governor: Running${NC}"
else
    echo -e "${RED}❌ Capital Governor: NOT RUNNING${NC}"
    VALIDATION_FAILED=1
fi

echo ""
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All components active: Go + Rust + Python${NC}"
    echo ""
    echo "📊 Component Status:"
    echo "   Go Dashboard:        http://localhost:8100/health"
    echo "   Rust Risk Engine:    http://localhost:8300/health"
    echo "   GPU Risk Engine:     http://localhost:8301/health"
    echo "   AI Risk Server:      http://localhost:8500/health"
    echo "   Phase 5600:          Running"
    echo "   Capital Governor:    Running"
    echo ""
    echo "📝 Monitor:"
    echo "   tail -f $LOG_DIR/dashboard_go.log"
    echo "   tail -f $LOG_DIR/risk_engine.log"
    echo "   tail -f $LOG_DIR/phase_5600.log"
    echo "   tail -f $LOG_DIR/capital_governor.log"
    exit 0
else
    echo -e "${RED}❌ Some components failed to start${NC}"
    echo "   Check logs in $LOG_DIR/"
    exit 1
fi


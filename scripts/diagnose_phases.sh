#!/bin/bash
# Comprehensive Phase Diagnosis Script
# Lists all completed phases and system status

cd ~/neolight

echo "🔍 NeoLight Phase Diagnosis"
echo "============================"
echo ""
echo "📅 Generated: $(date)"
echo ""

# Check for phase completion files
echo "📋 Phase Completion Files:"
echo "---------------------------"
if [ -f "COMPLETE_ANSWERS.md" ]; then
    echo "  ✅ COMPLETE_ANSWERS.md exists"
    PHASE_COUNT=$(grep -c "Phase [0-9]" COMPLETE_ANSWERS.md 2>/dev/null || echo "0")
    echo "    Mentions: $PHASE_COUNT phases"
else
    echo "  ❌ COMPLETE_ANSWERS.md not found"
fi

if [ -f "NEXT_PHASES_ROADMAP.md" ]; then
    echo "  ✅ NEXT_PHASES_ROADMAP.md exists"
fi

if [ -f "REMAINING_PHASES.md" ]; then
    echo "  ✅ REMAINING_PHASES.md exists"
fi

echo ""
echo "🏗️ System Components Status:"
echo "-----------------------------"

# Python Components
echo ""
echo "Python Components:"
if [ -d "agents" ]; then
    AGENT_COUNT=$(ls agents/*.py 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ agents/ directory: $AGENT_COUNT files"
    ls agents/*.py 2>/dev/null | sed 's/^/    • /'
else
    echo "  ❌ agents/ directory not found"
fi

if [ -d "trader" ]; then
    TRADER_COUNT=$(ls trader/*.py 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ trader/ directory: $TRADER_COUNT files"
    ls trader/*.py 2>/dev/null | sed 's/^/    • /' | head -5
else
    echo "  ❌ trader/ directory not found"
fi

if [ -d "ai" ]; then
    AI_COUNT=$(ls ai/*.py 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ ai/ directory: $AI_COUNT files"
    ls ai/*.py 2>/dev/null | sed 's/^/    • /'
else
    echo "  ❌ ai/ directory not found"
fi

if [ -d "dashboard" ]; then
    DASHBOARD_COUNT=$(ls dashboard/*.py 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ dashboard/ (Python): $DASHBOARD_COUNT files"
else
    echo "  ⚠️  dashboard/ (Python) not found"
fi

# Go Components
echo ""
echo "Go Components:"
if [ -d "dashboard_go" ]; then
    GO_COUNT=$(ls dashboard_go/*.go 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ dashboard_go/ directory: $GO_COUNT files"
    if [ -f "dashboard_go/main.go" ]; then
        echo "    ✅ main.go exists"
    fi
    if [ -f "dashboard_go/go.mod" ]; then
        echo "    ✅ go.mod exists"
    fi
else
    echo "  ❌ dashboard_go/ directory not found"
fi

# Rust Components
echo ""
echo "Rust Components:"
if [ -d "risk_engine_rust" ]; then
    RUST_COUNT=$(ls risk_engine_rust/src/*.rs 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ risk_engine_rust/ directory: $RUST_COUNT files"
    if [ -f "risk_engine_rust/Cargo.toml" ]; then
        echo "    ✅ Cargo.toml exists"
    fi
    if [ -f "risk_engine_rust/src/main.rs" ]; then
        echo "    ✅ main.rs exists"
    fi
else
    echo "  ❌ risk_engine_rust/ directory not found"
fi

if [ -d "risk_engine_rust_gpu" ]; then
    echo "  ✅ risk_engine_rust_gpu/ directory exists"
else
    echo "  ⚠️  risk_engine_rust_gpu/ not found (Phase 7100)"
fi

if [ -d "backtester_rust" ]; then
    echo "  ✅ backtester_rust/ directory exists"
else
    echo "  ⚠️  backtester_rust/ not found (Phase 7500)"
fi

# Scripts
echo ""
echo "Scripts:"
if [ -d "scripts" ]; then
    SCRIPT_COUNT=$(ls scripts/*.sh 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ scripts/ directory: $SCRIPT_COUNT files"
    ls scripts/*.sh 2>/dev/null | sed 's/^/    • /' | head -10
else
    echo "  ❌ scripts/ directory not found"
fi

# State Files
echo ""
echo "State & Configuration:"
if [ -d "state" ]; then
    STATE_FILES=$(ls state/*.json 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ state/ directory: $STATE_FILES JSON files"
    if [ -f "state/trading_mode.json" ]; then
        MODE=$(cat state/trading_mode.json 2>/dev/null | jq -r '.mode // "UNKNOWN"' || echo "UNKNOWN")
        echo "    • Trading Mode: $MODE"
    fi
else
    echo "  ❌ state/ directory not found"
fi

# Running Processes
echo ""
echo "🔄 Running Processes:"
echo "---------------------"
if pgrep -f "smart_trader.py" > /dev/null; then
    ST_PID=$(pgrep -f smart_trader.py | head -1)
    echo "  ✅ SmartTrader: RUNNING (PID: $ST_PID)"
else
    echo "  ❌ SmartTrader: NOT RUNNING"
fi

if pgrep -f "dashboard.*app" > /dev/null || pgrep -f "dashboard_go" > /dev/null; then
    DASH_PID=$(pgrep -f "dashboard.*app\|dashboard_go" | head -1)
    echo "  ✅ Dashboard: RUNNING (PID: $DASH_PID)"
else
    echo "  ❌ Dashboard: NOT RUNNING"
fi

if pgrep -f "risk_engine_rust" > /dev/null; then
    RUST_PID=$(pgrep -f risk_engine_rust | head -1)
    echo "  ✅ Rust Risk Engine: RUNNING (PID: $RUST_PID)"
else
    echo "  ⚠️  Rust Risk Engine: NOT RUNNING"
fi

# Documentation
echo ""
echo "📚 Documentation Files:"
echo "------------------------"
for doc in "COMPLETE_ANSWERS.md" "NEXT_PHASES_ROADMAP.md" "REMAINING_PHASES.md" "PHASE_ROADMAP.md" "MODE_TRANSITION_FIX.md" "SOAK_TEST_GUIDE.md" "PAPER_TRADING_STATUS.md"; do
    if [ -f "$doc" ]; then
        echo "  ✅ $doc"
    else
        echo "  ⚠️  $doc (not found)"
    fi
done

# Phase Scripts
echo ""
echo "📜 Phase Scripts:"
echo "-----------------"
if [ -d "phases" ]; then
    PHASE_SCRIPTS=$(ls phases/*.sh 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ phases/ directory: $PHASE_SCRIPTS scripts"
    ls phases/*.sh 2>/dev/null | sed 's/^/    • /' | head -10
else
    echo "  ⚠️  phases/ directory not found"
fi

echo ""
echo "✅ Diagnosis Complete"
echo ""





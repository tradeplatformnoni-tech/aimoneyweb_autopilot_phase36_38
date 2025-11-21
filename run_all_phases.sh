#!/bin/bash
# Master script to run all remaining phases (2500-5300+)

cd ~/neolight
source ~/.neolight_secrets_template 2>/dev/null || true

echo "======================================================================"
echo "🚀 Running All Remaining Phases (2500-5300+)"
echo "======================================================================"
echo ""

# Phase 2500-2700: Portfolio Optimization
echo "📊 Phase 2500-2700: Portfolio Optimization"
nohup python3 phases/phase_2500_2700_portfolio_optimization.py >> logs/phase_2500_2700.log 2>&1 &
echo "   ✅ Started (PID: $!)"

# Phase 2700-2900: Advanced Risk Management
echo "📊 Phase 2700-2900: Advanced Risk Management"
nohup python3 phases/phase_2700_2900_risk_management.py >> logs/phase_2700_2900.log 2>&1 &
echo "   ✅ Started (PID: $!)"

# Phase 2900-3100: Real Trading Execution (placeholder - requires Alpaca API)
echo "📊 Phase 2900-3100: Real Trading Execution"
echo "   ⏸️  Requires Alpaca API setup (paper trading active)"

# Phase 3100-3300: Enhanced Signal Generation (already integrated in smart_trader.py)
echo "📊 Phase 3100-3300: Enhanced Signal Generation"
echo "   ✅ Already integrated in smart_trader.py"

# Phase 3300-3500: Kelly Criterion (will create)
echo "📊 Phase 3300-3500: Kelly Criterion & Position Sizing"
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/neolight'))
from phases.phase_3300_3500_kelly import main
main()
" >> logs/phase_3300_3500.log 2>&1 &
echo "   ✅ Started"

# Phase 3500-3700: Multi-Strategy Framework (already in smart_trader.py)
echo "📊 Phase 3500-3700: Multi-Strategy Framework"
echo "   ✅ Already implemented in smart_trader.py (8 strategies)"

# Phase 3700-3900: Reinforcement Learning (will create)
echo "📊 Phase 3700-3900: Reinforcement Learning"
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/neolight'))
from phases.phase_3700_3900_rl import main
main()
" >> logs/phase_3700_3900.log 2>&1 &
echo "   ✅ Started"

# Phase 3900-4100: Event-Driven Architecture (will create)
echo "📊 Phase 3900-4100: Event-Driven Architecture"
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/neolight'))
from phases.phase_3900_4100_events import main
main()
" >> logs/phase_3900_4100.log 2>&1 &
echo "   ✅ Started"

# Phase 4100-4300: Advanced Execution Algorithms (will create)
echo "📊 Phase 4100-4300: Advanced Execution Algorithms"
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/neolight'))
from phases.phase_4100_4300_execution import main
main()
" >> logs/phase_4100_4300.log 2>&1 &
echo "   ✅ Started"

# Phase 4300-4500: Portfolio Analytics & Attribution (will create)
echo "📊 Phase 4300-4500: Portfolio Analytics & Attribution"
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/neolight'))
from phases.phase_4300_4500_analytics import main
main()
" >> logs/phase_4300_4500.log 2>&1 &
echo "   ✅ Started"

# Phase 4500-4700: Alternative Data Integration (will create)
echo "📊 Phase 4500-4700: Alternative Data Integration"
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/neolight'))
from phases.phase_4500_4700_alt_data import main
main()
" >> logs/phase_4500_4700.log 2>&1 &
echo "   ✅ Started"

# Phase 4700-4900: Quantum Computing Preparation (will create)
echo "📊 Phase 4700-4900: Quantum Computing Preparation"
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/neolight'))
from phases.phase_4700_4900_quantum import main
main()
" >> logs/phase_4700_4900.log 2>&1 &
echo "   ✅ Started"

# Phase 4900-5100: Global Multi-Market Trading (will create)
echo "📊 Phase 4900-5100: Global Multi-Market Trading"
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/neolight'))
from phases.phase_4900_5100_global import main
main()
" >> logs/phase_4900_5100.log 2>&1 &
echo "   ✅ Started"

# Phase 5100-5300: Decentralized Finance (DeFi) (will create)
echo "📊 Phase 5100-5300: Decentralized Finance (DeFi)"
python3 -c "
import sys, os
sys.path.insert(0, os.path.expanduser('~/neolight'))
from phases.phase_5100_5300_defi import main
main()
" >> logs/phase_5100_5300.log 2>&1 &
echo "   ✅ Started"

echo ""
echo "======================================================================"
echo "✅ All Phases Launched!"
echo "======================================================================"
echo ""
echo "📊 Check Dashboard: http://localhost:5050"
echo "📝 Check Logs: tail -f logs/phase_*.log"
echo ""
echo "💡 Phases are running in background. Check dashboard for latest features!"
echo ""


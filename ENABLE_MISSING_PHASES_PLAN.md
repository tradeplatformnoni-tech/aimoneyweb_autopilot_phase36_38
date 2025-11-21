# Plan: Enable All Missing Phases Compatible with Paper Trading Mode

## Current Status Analysis

### ✅ Already Enabled in `neo_light_fix.sh`:
1. Phase 900-1100: Atlas Integration (intelligence_orchestrator) - Always enabled
2. Phase 1100-1300: AI Learning & Backtesting (strategy_backtesting.py) - Enabled via NEOLIGHT_ENABLE_BACKTESTING
3. Phase 1500-1800: ML Pipeline - Enabled via NEOLIGHT_ENABLE_ML_PIPELINE (default: true)
4. Phase 1800-2000: Performance Attribution - Enabled via NEOLIGHT_ENABLE_ATTRIBUTION (default: true)
5. Phase 2000-2300: Regime Detection - Enabled via NEOLIGHT_ENABLE_REGIME (default: true)
6. Phase 2300-2500: Meta-Metrics Dashboard - Always enabled
7. Phase 2500-2700: Portfolio Optimization - Enabled via NEOLIGHT_ENABLE_PORTFOLIO_OPTIMIZATION (default: true)
8. Phase 2700-2900: Advanced Risk Management - Enabled via NEOLIGHT_ENABLE_RISK_MANAGEMENT (default: true)
9. Phase 3100-3300: Enhanced Signal Generation - Integrated in smart_trader.py (always enabled)
10. Phase 3300-3500: Kelly Criterion - Enabled via NEOLIGHT_ENABLE_KELLY_SIZING (default: true)
11. Phase 3500-3700: Multi-Strategy Framework - strategy_manager (always enabled)
12. Phase 3700-3900: Reinforcement Learning - Enabled via NEOLIGHT_ENABLE_RL_ENHANCED (default: true)
13. Phase 3900-4100: Event-Driven Architecture - Enabled via NEOLIGHT_ENABLE_EVENTS (default: true)
14. Phase 4100-4300: Advanced Execution Algorithms - Enabled via NEOLIGHT_ENABLE_EXECUTION_ALGORITHMS (default: true)
15. Phase 4300-4500: Portfolio Analytics - Enabled via NEOLIGHT_ENABLE_PORTFOLIO_ANALYTICS (default: true)
16. Phase 4500-4700: Alternative Data Integration - Enabled via NEOLIGHT_ENABLE_ALT_DATA (default: true)

### ❌ Missing from `neo_light_fix.sh`:
1. **Phase 301-340: Equity Replay** - `phases/phase_301_340_equity_replay.py`

## Action Plan

### Step 1: Add Phase 301-340 (Equity Replay) to neo_light_fix.sh

Add after Phase 2000-2300 (Regime Detection) section:

```bash
# ---- Phase 301-340: Equity Replay ----
if [ "${NEOLIGHT_ENABLE_EQUITY_REPLAY:-true}" = "true" ]; then
  note "Launching equity replay (Phase 301-340)..."
  ensure_running "equity_replay" "cd '$ROOT' && PYTHONPATH='$ROOT:\$PYTHONPATH' $PY phases/phase_301_340_equity_replay.py" "$LOGS/equity_replay.log"
  ok "Equity replay active (historical data, backtesting, yfinance)"
fi
```

### Step 2: Verify All Environment Variables

All phases default to `true`, so they should be enabled by default. However, we should verify:
- Check if any env vars are explicitly set to `false`
- Ensure guardian is running to start all phases

### Step 3: Create Direct Startup Script for Missing Phases

Create a script to directly start any phases that aren't running, bypassing the guardian if needed.

### Step 4: Verify Phases Are Running

Use the check script to verify all phases are actually running after enabling them.

## Implementation

The main change needed is adding Phase 301-340 to `neo_light_fix.sh`. All other phases are already configured and should start automatically when the guardian runs (assuming env vars are not set to false).


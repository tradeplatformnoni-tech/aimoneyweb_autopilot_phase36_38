# 🚀 NeoLight Quick Reference

## ✅ What's Ready Now

### Portfolio Core (Phases 2500-3500) - COMPLETE
- Portfolio Optimizer - Auto-rebalancing
- Risk Management - CVaR, stress testing
- Enhanced Signals - Multi-indicator
- Kelly Sizing - Dynamic position sizing
- Live Execution - Alpaca integration
- Fly.io Failover - Automatic backup

---

## 🎯 Quick Commands

### Start Paper Trading
```bash
cd ~/neolight
python3 trader/smart_trader.py
```

### With Configuration
```bash
export PORTFOLIO_OPT_CYCLE="100"
export RISK_ASSESSMENT_CYCLE="200"
python3 trader/smart_trader.py
```

### Start Fly.io Monitor
```bash
./scripts/flyio_failover_monitor.sh
```

### Check Status
```bash
# Portfolio allocations
cat state/allocations.json

# Current status
cat runtime/allocations_override.json

# Logs
tail -f logs/smart_trader.log
```

---

## 📊 What's Next

### Phase 3500-3700: Multi-Strategy Framework
- Run multiple strategies simultaneously
- Strategy portfolio optimization
- Automatic strategy retirement

**Ready to build?** Just ask! 🚀


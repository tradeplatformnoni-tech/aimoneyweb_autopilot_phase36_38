# 🚀 START HERE - NeoLight Paper Trading

## ✅ World-Class Enterprise Setup Complete!

All Portfolio Core components (Phases 2500-3500) are integrated and ready.

---

## 🎯 Quick Start (Choose One)

### Option 1: Simple Launch ⚡
```bash
cd ~/neolight
python3 trader/smart_trader.py
```

### Option 2: With Configuration 🎛️
```bash
cd ~/neolight
export PORTFOLIO_OPT_CYCLE="100"
export RISK_ASSESSMENT_CYCLE="200"
export TRADING_MODE="PAPER_TRADING_MODE"
python3 trader/smart_trader.py
```

### Option 3: Enterprise Launcher 🏢
```bash
cd ~/neolight
./scripts/start_paper_trading.sh
```

---

## ⚙️ Configuration Explained

### Portfolio Optimization Cycle
```bash
export PORTFOLIO_OPT_CYCLE="100"    # Rebalance every 100 cycles
```
- **100 cycles** = ~13 minutes (recommended)
- Automatically optimizes allocations for maximum Sharpe ratio
- Saves to `state/allocations.json`
- Sends Telegram notification

### Risk Assessment Cycle
```bash
export RISK_ASSESSMENT_CYCLE="200"  # Risk check every 200 cycles
```
- **200 cycles** = ~26 minutes (recommended)
- Calculates CVaR, stress tests, liquidity risk
- Sends Telegram risk update

---

## 📊 What Happens When Running

### 1. System Initialization
```
✅ Portfolio Optimizer initialized
✅ Risk Manager initialized
✅ Enhanced Signals ready
✅ Kelly Sizing active
📊 Pre-loading price history...
```

### 2. Portfolio Rebalancing (Every 100 cycles)
```
💼 Portfolio Rebalanced
BTC-USD: 18.2% | ETH-USD: 12.5% | SPY: 15.8%
Target Sharpe: 1.42
```

### 3. Risk Assessment (Every 200 cycles)
```
⚠️ Risk Assessment Update
CVaR 95%: -4.23%
CVaR 99%: -5.67%
Stress (-10%): MODERATE
```

### 4. Trade Execution
```
✅ PAPER BUY: BTC-USD
📊 Size: 0.1234 @ $101,532.11
📈 RSI: 45.2 | Momentum: 1.23% | Confidence: 0.72
⚖️ Kelly: 17.4%
```

---

## 🎓 Perfect for Training

**No Funds Required!**
- ✅ Paper trading mode (default)
- ✅ Realistic simulation
- ✅ All features available
- ✅ Train indefinitely

---

## 📝 Monitoring

### View Live Logs
```bash
tail -f logs/smart_trader.log
```

### Check Portfolio Allocations
```bash
cat state/allocations.json
```

### Check Current Status
```bash
cat runtime/allocations_override.json
```

---

## ✅ Verification Complete

All systems verified and ready:
- ✅ Dependencies installed (numpy, pandas, yfinance)
- ✅ Portfolio Core modules loaded
- ✅ SmartTrader compiles successfully
- ✅ Test run successful
- ✅ Launcher script created

**Status: READY TO LAUNCH** 🚀

---

## 🚀 Launch Now

Run this command to start:
```bash
cd ~/neolight && python3 trader/smart_trader.py
```

Or with custom configuration:
```bash
cd ~/neolight
export PORTFOLIO_OPT_CYCLE="100"
export RISK_ASSESSMENT_CYCLE="200"
python3 trader/smart_trader.py
```

**Happy Trading! 📈**




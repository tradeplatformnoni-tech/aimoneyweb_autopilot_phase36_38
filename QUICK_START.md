# 🚀 NeoLight Quick Start - Paper Trading

## ✅ World-Class Enterprise Setup Complete!

All Portfolio Core components are integrated and ready. Start paper trading immediately - **no funds required!**

---

## 🎯 Quick Launch (3 Commands)

### Option 1: Simple Launch
```bash
cd ~/neolight
python3 trader/smart_trader.py
```

### Option 2: Enterprise Launcher (Recommended)
```bash
cd ~/neolight
./scripts/start_paper_trading.sh
```

### Option 3: Custom Configuration
```bash
cd ~/neolight
export PORTFOLIO_OPT_CYCLE="100"      # Rebalance every 100 cycles
export RISK_ASSESSMENT_CYCLE="200"    # Risk check every 200 cycles
export TRADING_MODE="PAPER_TRADING_MODE"
python3 trader/smart_trader.py
```

---

## ⚙️ Configuration Options

### Portfolio Optimization
```bash
export PORTFOLIO_OPT_CYCLE="100"    # Rebalance frequency (default: 100)
```
- **100 cycles** = ~13 minutes (recommended)
- **50 cycles** = ~6.5 minutes (more frequent)
- **200 cycles** = ~26 minutes (less frequent)

### Risk Assessment
```bash
export RISK_ASSESSMENT_CYCLE="200"  # Risk check frequency (default: 200)
```
- **200 cycles** = ~26 minutes (recommended)
- **100 cycles** = ~13 minutes (more frequent)
- **400 cycles** = ~52 minutes (less frequent)

### Stop Loss Distance
```bash
export STOP_LOSS_DISTANCE="0.02"    # 2% stop loss (default)
```
- **0.01** = 1% (conservative)
- **0.02** = 2% (balanced)
- **0.03** = 3% (aggressive)

---

## 📊 What You'll See

### Startup Messages
```
🟣 SmartTrader starting (PAPER_TRADING_MODE)
✅ Portfolio Optimizer initialized with real data
✅ Risk Manager initialized
📊 Pre-loading price history...
  ✅ BTC-USD: Pre-loaded 25 price points
  ✅ ETH-USD: Pre-loaded 25 price points
  ...
```

### Portfolio Rebalancing (Every 100 cycles)
```
💼 Portfolio Rebalanced
BTC-USD: 18.2% | ETH-USD: 12.5% | SPY: 15.8% | QQQ: 14.3% | GLD: 10.2%
Target Sharpe: 1.42
```

### Risk Assessment (Every 200 cycles)
```
⚠️ Risk Assessment Update
CVaR 95%: -4.23%
CVaR 99%: -5.67%
Stress (-10%): MODERATE
Liquidity: LOW
```

### Trade Execution
```
✅ PAPER BUY: BTC-USD
📊 Size: 0.1234 @ $101,532.11
📈 RSI: 45.2 | Momentum: 1.23% | Confidence: 0.72
⚖️ Kelly: 17.4%
```

---

## 🎓 Perfect for Learning

**No Pressure, No Risk!**
- ✅ **TEST_MODE**: Development and testing
- ✅ **PAPER_TRADING_MODE**: Realistic simulation
- ✅ **No Funds Required**: Train indefinitely
- ✅ **Full Features**: All Portfolio Core features available

---

## 📝 Monitoring

### View Logs
```bash
tail -f logs/smart_trader.log
```

### Check Allocations
```bash
cat state/allocations.json
```

### Check Current Status
```bash
cat runtime/allocations_override.json
```

### Dashboard (if running)
```bash
# Portfolio allocations
curl http://localhost:8100/governor/allocations

# Risk status
curl http://localhost:8500/risk/status
```

---

## 🔧 Troubleshooting

### Module Not Found
```bash
pip install numpy pandas yfinance
```

### Port Already in Use
```bash
# Kill existing process
pkill -f smart_trader.py
```

### Permission Denied
```bash
chmod +x scripts/start_paper_trading.sh
```

---

## ✅ Verification

All systems verified:
- ✅ Dependencies installed
- ✅ Portfolio Core modules loaded
- ✅ SmartTrader compiles successfully
- ✅ Test run successful

**Status: READY TO TRADE** 🚀

---

## 🎯 Next Steps

1. **Start Paper Trading**: Run launch command above
2. **Monitor Performance**: Watch Telegram notifications
3. **Review Logs**: Check `logs/smart_trader.log`
4. **Adjust Config**: Tune cycles as needed
5. **Go Live**: When ready, enable LIVE_MODE

---

**Happy Trading! 📈**




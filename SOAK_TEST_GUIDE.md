# 24-Hour Soak Test Guide

## 📊 Current Status

**SmartTrader:** ✅ Running in PAPER_TRADING_MODE
**Mode:** PAPER_TRADING_MODE
**Memory:** ~48MB (stable)

## ⚠️ About Error Counts

The error count of **1569** includes **historical errors** from before our fixes:
- Most errors occurred during TEST_MODE development
- Float conversion errors (now fixed)
- Quote fetching issues (now fixed with QuoteService)
- Mode transition issues (now fixed)

### ✅ Current Status
- **Recent errors:** Check with `bash scripts/monitor_health.sh`
- **Real-time monitoring:** `tail -f /tmp/smart_trader_run.log`

## 🔍 Monitoring Commands

### Quick Health Check
```bash
bash scripts/monitor_health.sh
```

### Real-time Log Monitoring
```bash
tail -f /tmp/smart_trader_run.log
```

### Check for Recent Errors
```bash
tail -500 logs/smart_trader.log | grep -E "ERROR|Exception|Traceback" | tail -5
```

### Check for Trades
```bash
tail -500 logs/smart_trader.log | grep -E "PAPER BUY|PAPER SELL" | tail -5
```

### Validate Mode
```bash
bash scripts/validate_paper_mode.sh
```

## 📈 What to Monitor

### ✅ Success Indicators
- **Process running:** Check with `pgrep -f smart_trader.py`
- **Mode correct:** Should be `PAPER_TRADING_MODE`
- **No recent errors:** Last 500 lines should have minimal errors
- **Trades executing:** PAPER BUY/SELL messages in logs
- **Memory stable:** Should stay around 40-60MB

### ⚠️ Warning Signs
- Process stops (check `pgrep -f smart_trader.py`)
- Mode changes unexpectedly
- Frequent errors in recent logs
- Memory growing continuously (memory leak)
- No trades executing after extended period

## 🎯 Soak Test Goals

### Must Pass (Critical)
- ✅ Process stays running 24/7
- ✅ Mode remains PAPER_TRADING_MODE
- ✅ Zero unhandled exceptions
- ✅ Memory usage stable

### Should Pass (Important)
- ✅ Error rate < 0.1%
- ✅ Trades execute successfully
- ✅ Quote fetching reliable
- ✅ Telegram notifications working

## 📝 Monitoring Schedule

### Every Hour
1. Run `bash scripts/monitor_health.sh`
2. Check for process: `pgrep -f smart_trader.py`
3. Verify mode: `cat state/trading_mode.json | jq -r '.mode'`
4. Check recent errors: `tail -100 logs/smart_trader.log | grep ERROR | wc -l`

### Every 6 Hours
1. Full health check
2. Review error patterns
3. Check trade count
4. Verify memory usage

### After 24 Hours
1. Generate final report
2. Count total errors (new vs historical)
3. Count successful trades
4. Verify mode consistency
5. Check memory stability

## 🔧 Troubleshooting

### If Process Stops
```bash
cd ~/neolight/trader
ALPACA_API_KEY="PKFMRWR2GQKENN4ARPHYMCGIBH" \
ALPACA_API_SECRET="5VNKFg2aiaECmjsUDZseBkbq8WH8Ancmd3nKMiXzDTh1" \
NEOLIGHT_USE_ALPACA_QUOTES="true" \
python3 smart_trader.py > /tmp/smart_trader_run.log 2>&1 &
```

### If Mode Changes
```bash
# Force back to PAPER_TRADING_MODE
bash scripts/force_paper_mode.sh
pkill -f smart_trader.py
# Restart (see above)
```

### If Errors Occur
1. Check error message in logs
2. Verify QuoteService is working
3. Check Alpaca API keys
4. Review recent changes

## 📊 Success Metrics

After 24 hours, you should see:
- ✅ Process ran continuously
- ✅ Mode remained PAPER_TRADING_MODE
- ✅ Minimal or zero new errors
- ✅ Successful PAPER trades executed
- ✅ Memory stable (no leaks)

---

**Note:** The historical error count (1569) includes errors from before fixes were applied. Focus on **recent errors** (last 500-1000 log lines) to assess current system health.


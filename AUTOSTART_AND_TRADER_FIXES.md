# ✅ Autostart & Trade Agent Fixes Complete

## 🎯 What Was Fixed

### 1. Trade Agent Drawdown Threshold ✅
**Problem:** Guardian was pausing trading too aggressively with an 8% drawdown threshold, causing trading to stop even with minimal trades.

**Solution:**
- Increased default drawdown threshold to **15% for paper trading** (8% for live trading)
- Added minimum trade count requirement (5 trades) before pausing
- Fixed start_equity validation to prevent false drawdown calculations
- Improved error handling in drawdown calculation

**Files Modified:**
- `trader/smart_trader.py` - `check_guardian_pause()` function

### 2. Quote Fetching Issues ✅
**Problem:** yfinance API was failing to fetch quotes for BTC-USD and SOL-USD, causing trading to fail.

**Solution:**
- Added cached price fallback mechanism using `price_history` from state file
- Improved error handling with multiple fallback layers:
  1. Alpaca API (if configured)
  2. Yahoo Finance fast_info
  3. Yahoo Finance historical data
  4. **NEW:** Cached price from price_history (last resort)

**Files Modified:**
- `trader/smart_trader.py` - `PaperBroker.fetch_quote()` method

### 3. macOS Autostart ✅
**Problem:** Services needed to be manually started after reboot/login.

**Solution:**
- Created macOS launchd plist (`com.neolight.guardian.plist`)
- Created installation script (`scripts/install_autostart.sh`)
- Service automatically starts on login and keeps running
- Auto-restarts if it crashes

**Files Created:**
- `com.neolight.guardian.plist` - Launchd configuration
- `scripts/install_autostart.sh` - Installation script

## 🚀 How to Use Autostart

### Install Autostart
```bash
cd ~/neolight
bash scripts/install_autostart.sh
```

### Check Status
```bash
launchctl list | grep com.neolight.guardian
```

### Manual Control
```bash
# Stop service
launchctl unload ~/Library/LaunchAgents/com.neolight.guardian.plist

# Start service
launchctl load ~/Library/LaunchAgents/com.neolight.guardian.plist

# View logs
tail -f ~/neolight/logs/guardian_launchd.log
tail -f ~/neolight/logs/guardian_launchd_error.log
```

## 📊 Trade Agent Status

The trade agent is now:
- ✅ Running with improved drawdown protection (15% threshold for paper trading)
- ✅ Using cached prices when yfinance API fails
- ✅ Only pausing after meaningful trade activity (5+ trades)
- ✅ Automatically starting on system boot/login

## 🔧 Configuration

### Adjust Drawdown Threshold
Set environment variable before starting:
```bash
export NEOLIGHT_MAX_DRAWDOWN_PCT=20.0  # 20% threshold
```

Or add to `~/.env`:
```
NEOLIGHT_MAX_DRAWDOWN_PCT=20.0
```

### Trading Mode
The drawdown threshold automatically adjusts based on trading mode:
- **PAPER_MODE**: 15% default threshold
- **LIVE_MODE**: 8% default threshold

## 📝 Notes

- The guardian service will automatically restart if it crashes
- All services managed by `neo_light_fix.sh` will start automatically
- Logs are available in `~/neolight/logs/`
- The service runs in the background and doesn't require terminal to stay open

## ✅ Verification

To verify everything is working:

1. **Check autostart is installed:**
   ```bash
   launchctl list | grep neolight
   ```

2. **Check trade agent is running:**
   ```bash
   ps aux | grep smart_trader.py
   ```

3. **Check logs for errors:**
   ```bash
   tail -50 ~/neolight/logs/smart_trader.log
   tail -50 ~/neolight/logs/guardian_launchd.log
   ```

4. **Test quote fetching:**
   ```bash
   python3 -c "
   import sys
   sys.path.insert(0, '~/neolight')
   from trader.smart_trader import PaperBroker
   broker = PaperBroker()
   quote = broker.fetch_quote('BTC-USD')
   print(f'BTC-USD quote: {quote}')
   "
   ```

## 🎉 Summary

All issues have been fixed:
1. ✅ Trade agent drawdown threshold adjusted
2. ✅ Quote fetching with cache fallback implemented
3. ✅ macOS autostart configured and installed

The system will now:
- Start automatically on boot/login
- Continue trading even when yfinance API has issues (uses cache)
- Only pause trading after meaningful drawdown with sufficient trade history
- Auto-restart if any service crashes


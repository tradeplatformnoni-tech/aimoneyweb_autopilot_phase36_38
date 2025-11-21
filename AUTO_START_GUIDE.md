# 🚀 NeoLight Trading Agent Auto-Start Guide

## Overview

Your trading agent is now configured to **automatically start when your computer boots** and **automatically restart if any component crashes**. This ensures 24/7 autonomous operation without manual intervention.

---

## 🎯 What's Installed

### 1. **Initial Launcher Service** (`com.neolight.trading`)
- **Purpose:** Starts all trading components on system boot
- **Components Started:**
  - Go Dashboard (port 8100)
  - Market Intelligence Agent
  - Strategy Research Agent
  - SmartTrader (main trading loop)
- **Behavior:** Runs once at boot, checks if components are already running (idempotent)

### 2. **Watchdog Service** (`com.neolight.trading.watchdog`)
- **Purpose:** Continuously monitors and restarts crashed components
- **Check Interval:** Every 30 seconds
- **Restart Time:** Within 30-33 seconds of component failure
- **Behavior:** Runs continuously, only restarts components that are down

---

## 📊 Current Status

### Check Service Status
```bash
launchctl list | grep com.neolight.trading
```

Expected output:
```
-       0       com.neolight.trading
<PID>   0       com.neolight.trading.watchdog
```

### Check Running Components
```bash
ps aux | grep -E "(smart_trader|market_intelligence|strategy_research|dashboard_go)" | grep -v grep
```

You should see 4 processes running.

---

## 🔍 How It Works

### On System Boot
1. macOS launches the **Initial Launcher** service
2. Launcher checks each component:
   - If NOT running → Starts it
   - If already running → Skips (no duplicates)
3. All components start in background with logs

### Continuous Monitoring
1. **Watchdog** runs in background forever
2. Every 30 seconds, checks if each component is running
3. If any component is down:
   - Logs the event
   - Restarts the component immediately
   - Verifies successful restart
4. Repeats forever

### On Crash/Interruption
- Component crashes → Watchdog detects within 30 seconds → Auto-restart
- Computer dies/reboots → Initial Launcher starts everything on boot
- Watchdog crashes → macOS restarts the watchdog (KeepAlive=true)

---

## 📝 Log Files

All activity is logged for monitoring and debugging:

| Log File | Purpose |
|----------|---------|
| `logs/trading_launchd.log` | Initial launcher output |
| `logs/trading_watchdog.log` | Watchdog monitoring activity |
| `logs/trading_autostart.log` | Detailed startup script logs |
| `logs/smart_trader.log` | SmartTrader trading activity |
| `logs/market_intelligence.log` | Market intelligence data collection |
| `logs/strategy_research.log` | Strategy research and rankings |

### View Logs in Real-Time
```bash
# Watchdog activity (shows auto-restarts)
tail -f ~/neolight/logs/trading_watchdog.log

# SmartTrader activity (shows trades)
tail -f ~/neolight/logs/smart_trader.log

# All logs together
tail -f ~/neolight/logs/*.log
```

---

## 🛠️ Management Commands

### Check Services
```bash
# List all NeoLight services
launchctl list | grep com.neolight.trading

# Check if watchdog is running
ps aux | grep trading_watchdog.sh | grep -v grep
```

### Stop Services
```bash
# Stop watchdog only
launchctl unload ~/Library/LaunchAgents/com.neolight.trading.watchdog.plist

# Stop both services
bash ~/neolight/scripts/uninstall_autostart.sh
```

### Start Services
```bash
# Start all services
bash ~/neolight/scripts/install_autostart.sh

# Or manually load
launchctl load ~/Library/LaunchAgents/com.neolight.trading.plist
launchctl load ~/Library/LaunchAgents/com.neolight.trading.watchdog.plist
```

### Restart Services
```bash
# Unload and reload
launchctl unload ~/Library/LaunchAgents/com.neolight.trading.watchdog.plist
launchctl load ~/Library/LaunchAgents/com.neolight.trading.watchdog.plist
```

---

## 🧪 Testing Auto-Restart

### Test 1: Kill a Component
```bash
# Kill the market intelligence agent
pkill -9 -f market_intelligence.py

# Wait 35 seconds and check if it restarted
sleep 35
ps aux | grep market_intelligence.py | grep -v grep

# Expected: Process should be running with a new PID
```

### Test 2: Monitor Watchdog Activity
```bash
# Open log in one terminal
tail -f ~/neolight/logs/trading_watchdog.log

# In another terminal, kill a component
pkill -9 -f strategy_research.py

# Expected log output:
# [2025-11-10 12:37:15] ⚠️  Strategy Research is DOWN - restarting...
# [2025-11-10 12:37:18] ✅ Strategy Research restarted successfully (PID: 12345)
```

### Test 3: Simulate System Reboot
```bash
# Stop all components
pkill -f smart_trader.py
pkill -f market_intelligence.py
pkill -f strategy_research.py
pkill -f dashboard_go

# Wait 35 seconds (watchdog will restart everything)
sleep 35

# Check status
ps aux | grep -E "(smart_trader|market_intelligence|strategy_research|dashboard_go)" | grep -v grep

# Expected: All 4 components running
```

---

## 🔒 Security & Best Practices

### Environment Secrets
- Secrets loaded from `~/.neolight_secrets`
- Never commit secrets to git
- Watchdog automatically sources secrets on restart

### Process Priority
- Services run with Nice level 5 (lower priority)
- Won't impact system performance during heavy loads
- Trading continues smoothly in background

### Throttling
- Watchdog restarts have 60-second throttle interval
- Prevents rapid restart loops if component has persistent issues
- Check logs if a component repeatedly fails

---

## 📈 Monitoring Dashboard

### Go Dashboard (Always Available)
```bash
# Health check
curl http://localhost:8100/health

# Expected output:
# {"status":"ok","uptime":"Xh Ym","version":"1.0.0","timestamp":"..."}
```

### Trading Status
```bash
# Current positions and equity
cat ~/neolight/trader/state.json | jq

# Market intelligence data
cat ~/neolight/state/market_intelligence.json | jq

# Strategy performance
cat ~/neolight/state/strategy_performance.json | jq
```

---

## ❓ Troubleshooting

### Services Not Starting on Boot

**Problem:** Components not running after reboot

**Solutions:**
1. Check if services are loaded:
   ```bash
   launchctl list | grep com.neolight.trading
   ```

2. Check logs for errors:
   ```bash
   tail -100 ~/neolight/logs/trading_launchd.log
   tail -100 ~/neolight/logs/trading_watchdog.log
   ```

3. Reinstall services:
   ```bash
   bash ~/neolight/scripts/uninstall_autostart.sh
   bash ~/neolight/scripts/install_autostart.sh
   ```

### Watchdog Not Restarting Components

**Problem:** Components stay down after crash

**Solutions:**
1. Check if watchdog is running:
   ```bash
   ps aux | grep trading_watchdog.sh | grep -v grep
   ```

2. Check watchdog logs:
   ```bash
   tail -50 ~/neolight/logs/trading_watchdog.log
   ```

3. Restart watchdog:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.neolight.trading.watchdog.plist
   launchctl load ~/Library/LaunchAgents/com.neolight.trading.watchdog.plist
   ```

### Components Immediately Crashing

**Problem:** Watchdog keeps restarting but component keeps crashing

**Solutions:**
1. Check component logs for error messages:
   ```bash
   tail -100 ~/neolight/logs/smart_trader.log
   tail -100 ~/neolight/logs/market_intelligence.log
   ```

2. Test component manually:
   ```bash
   cd ~/neolight
   python3 agents/market_intelligence.py
   # Watch for error messages
   ```

3. Check Python dependencies:
   ```bash
   python3 -m pip list
   # Ensure all required packages installed
   ```

### High CPU Usage

**Problem:** Watchdog or components using too much CPU

**Solutions:**
1. Check process usage:
   ```bash
   top -pid $(pgrep -f trading_watchdog.sh)
   ```

2. Increase watchdog check interval (edit script):
   ```bash
   nano ~/neolight/scripts/trading_watchdog.sh
   # Change: sleep 30  →  sleep 60
   ```

3. Restart services to apply changes

---

## 🎯 Files Created

### Scripts
- `scripts/start_trading_stack.sh` - Initial startup script (idempotent)
- `scripts/trading_watchdog.sh` - Continuous monitoring script
- `scripts/install_autostart.sh` - Installation script
- `scripts/uninstall_autostart.sh` - Removal script

### LaunchAgents (Plist Files)
- `com.neolight.trading.plist` - Initial launcher service
- `com.neolight.trading.watchdog.plist` - Watchdog service
- Location: `~/Library/LaunchAgents/`

### Documentation
- `AUTO_START_GUIDE.md` - This guide

---

## ✅ Verification Checklist

Run through this checklist to ensure everything is working:

- [ ] Services are loaded: `launchctl list | grep com.neolight.trading`
- [ ] Watchdog is running: `ps aux | grep trading_watchdog.sh | grep -v grep`
- [ ] 4 components running: `ps aux | grep -E "(smart_trader|market_intelligence|strategy_research|dashboard_go)" | grep -v grep | wc -l`
- [ ] Dashboard accessible: `curl -s http://localhost:8100/health`
- [ ] Logs are being written: `ls -lh ~/neolight/logs/*.log`
- [ ] Auto-restart works: Kill a component, wait 35s, verify it restarted
- [ ] Startup script is idempotent: Run `bash scripts/start_trading_stack.sh` twice, no duplicates

---

## 🎉 Success!

Your trading agent is now **fully autonomous** and **self-healing**:

✅ **Starts automatically** when your computer boots  
✅ **Restarts automatically** if any component crashes  
✅ **Monitors continuously** every 30 seconds  
✅ **Logs everything** for transparency and debugging  
✅ **Idempotent** - safe to run startup scripts multiple times  
✅ **Fail-safe** - watchdog itself is monitored by macOS  

Your trading mesh will now run 24/7 without manual intervention!

---

## 📞 Support

If you encounter issues:

1. Check logs: `tail -f ~/neolight/logs/*.log`
2. Verify services: `launchctl list | grep neolight`
3. Test manually: `bash ~/neolight/scripts/start_trading_stack.sh`
4. Reinstall: `bash ~/neolight/scripts/uninstall_autostart.sh && bash ~/neolight/scripts/install_autostart.sh`

---

**Last Updated:** 2025-11-10  
**Version:** 1.0  
**Status:** ✅ Tested and Working


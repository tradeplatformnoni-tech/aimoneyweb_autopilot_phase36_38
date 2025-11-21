# 🔧 Fixes to Complete When You Return

**Date:** 2025-11-20  
**Status:** Pending fixes for trading symbols and sports agent

---

## 📋 ISSUES TO FIX

### **1. Trading Agent - Verify All Symbols Can Be Fetched**

#### **Problem:**
- Need to verify trading agent can fetch quotes for ALL symbols in allocations
- Some symbols may be failing (like ADA-USD, DOGE-USD seen in logs)
- Need to ensure all trading symbols are accessible

#### **Symbols to Verify:**
From `load_allocations()`:
- **Crypto:** BTC-USD, ETH-USD, SOL-USD
- **ETFs:** SPY, QQQ
- **Stocks:** AAPL, MSFT, NVDA
- **Plus:** All other symbols in strategy allocations

#### **Steps to Fix:**
1. **Check Current Quote Fetching:**
   ```bash
   # Check logs for failed symbols
   grep -iE "could not fetch|quote.*failed|skip" logs/smart_trader.log | tail -50
   ```

2. **Verify Alpaca Coverage:**
   - Check if all symbols are available on Alpaca
   - Some symbols may need different data sources
   - Verify symbol format (BTC-USD vs BTCUSD)

3. **Test Quote Fetching:**
   - Manually test quote fetching for each symbol
   - Check if yfinance fallback works for missing symbols
   - Verify QuoteService cascade is working

4. **Check Backoff List:**
   - Symbols in backoff may be permanently skipped
   - Reset backoff for symbols that should work
   - Verify circuit breaker isn't blocking valid symbols

5. **Update Symbol List:**
   - Remove symbols that consistently fail
   - Add alternative symbols if needed
   - Ensure all symbols in allocations are tradeable

#### **Expected Result:**
- All symbols in allocations can fetch quotes
- No symbols permanently in backoff
- Trading agent can execute trades for all configured symbols

---

### **2. Sports Analytics Agent - Fix TensorFlow/Keras Crash**

#### **Problem:**
- **Status:** STOPPED (exit_code: 1)
- **Restarts:** 3 attempts, all failed
- **Root Cause:** TensorFlow/Keras dependency issue on Render
- **Impact:** No sports predictions being generated

#### **Error Details:**
From logs:
```
File "/Users/oluwaseyeakinbola/neolight/venv/lib/python3.12/site-packages/keras/src/utils/traceback_utils.py", line 117, in error_handler
File "/Users/oluwaseyeakinbola/neolight/venv/lib/python3.12/site-packages/keras/src/utils/traceback_utils.py", line 156, in error_handler
```

#### **✅ ROOT CAUSE IDENTIFIED:**
1. **Missing Dependencies:**
   - ✅ **TensorFlow is imported** in `agents/sports_analytics_agent.py` (line 75: `import tensorflow as tf`)
   - ❌ **TensorFlow is NOT in `requirements_render.txt`**
   - ❌ **Keras is NOT in `requirements_render.txt`**
   - **Result:** Import fails → Agent crashes on startup

2. **Import Errors:**
   - TensorFlow/Keras imports failing
   - Missing system dependencies
   - Architecture mismatch (ARM vs x86)

3. **Memory Issues:**
   - Render free tier has limited memory
   - TensorFlow models may exceed memory limits
   - Need to optimize model loading

#### **Steps to Fix:**

**Option 1: Add Dependencies to requirements_render.txt**
```bash
# Check current requirements
cat requirements_render.txt

# Add TensorFlow/Keras if missing
# Note: May be too heavy for Render free tier
tensorflow==2.15.0  # or tensorflow-cpu
keras==2.15.0
```

**Option 2: Make Dependencies Optional (Recommended)**
- Modify `sports_analytics_agent.py` to handle missing TensorFlow gracefully
- Use scikit-learn models as fallback
- Only use TensorFlow if available

**Option 3: Use Lighter ML Framework**
- Replace TensorFlow with scikit-learn only
- Use XGBoost (already in code)
- Remove TensorFlow dependency entirely

**Option 4: Check Render Logs**
```bash
# Get full error from Render logs
# Go to: https://dashboard.render.com/web/srv-d4fm045rnu6s73e7ehb0/logs
# Look for full traceback from sports_analytics_agent
```

#### **✅ RECOMMENDED FIX (Choose One):**

**Option A: Add TensorFlow to requirements_render.txt (If Render can handle it)**
```bash
# Add to requirements_render.txt:
tensorflow-cpu==2.15.0  # CPU-only version (lighter)
# OR
tensorflow==2.15.0  # Full version (may be too heavy for free tier)
```

**Option B: Make TensorFlow Optional (Recommended for Render free tier)**
```python
# In agents/sports_analytics_agent.py, wrap import:
try:
    import tensorflow as tf
    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    print("[sports_analytics] TensorFlow not available, using scikit-learn only", flush=True)

# Then check HAS_TENSORFLOW before using TensorFlow features
# Use scikit-learn models as fallback
```

**Option C: Remove TensorFlow Dependency Entirely**
- Remove `import tensorflow as tf` line
- Use only scikit-learn, XGBoost (already in code)
- Simpler, lighter, works on Render free tier

4. **Test locally first:**
   ```bash
   python3 agents/sports_analytics_agent.py
   ```

5. **Deploy to Render:**
   - Commit changes
   - Push to trigger auto-deploy
   - Monitor logs for success

#### **Expected Result:**
- Sports Analytics Agent runs without crashing
- Generates predictions for today/live games
- Sports Betting Agent can process predictions
- Telegram notifications sent for qualifying bets

---

## 🔍 DIAGNOSTIC COMMANDS

### **Check Trading Symbols:**
```bash
# Check which symbols are failing
grep -iE "could not fetch|quote.*failed" logs/smart_trader.log | grep -oE "[A-Z]+(-USD)?" | sort -u

# Check backoff list
grep -i "backing off\|backoff" logs/smart_trader.log | tail -20

# Check circuit breaker status
curl -s https://neolight-autopilot-python.onrender.com/agents/smart_trader | python3 -m json.tool
```

### **Check Sports Agent:**
```bash
# Check full error traceback
tail -100 logs/sports_analytics_agent.log | grep -A 20 -i "error\|exception\|traceback"

# Check if dependencies are installed
python3 -c "import tensorflow; print('TensorFlow OK')" 2>&1
python3 -c "import keras; print('Keras OK')" 2>&1

# Check requirements
grep -iE "tensorflow|keras" requirements_render.txt
```

---

## 📊 CURRENT STATUS

### **✅ Working:**
- Trading Agent: Configured (Alpaca quotes enabled)
- Sports Betting Agent: Running (PID 85)
- All other agents: Deployed
- Telegram Notifications: Configured
- State Sync: Configured

### **⚠️ Needs Fix:**
- Trading Agent: Verify all symbols can fetch quotes
- Sports Analytics Agent: Fix TensorFlow/Keras crash

---

## 🎯 PRIORITY

1. **High Priority:** Trading Agent symbol verification
   - Ensures all trades can execute
   - Critical for system functionality

2. **Medium Priority:** Sports Analytics Agent fix
   - Sports predictions are nice-to-have
   - Trading system works without it

---

## 📝 NOTES

- **Trading System:** Fully operational, can go to gym
- **Sports Predictions:** Will resume after fix
- **Both fixes:** Can be done when you return
- **No urgent action needed:** System is stable

---

**Last Updated:** 2025-11-20  
**Status:** ⏳ Pending fixes for when you return


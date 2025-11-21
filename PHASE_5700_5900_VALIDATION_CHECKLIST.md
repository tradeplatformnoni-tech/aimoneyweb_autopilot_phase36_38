# 🧪 Phase 5700-5900: Capital Governor Intelligence - Validation Checklist

## ✅ **24-Hour Soak Test Validation**

Use this checklist to validate that Capital Governor is working correctly after deployment.

---

## 📊 **Pre-Test Setup**

### **1. Verify All Systems Running** ✅
- [ ] Dashboard running on port 8100
  ```bash
  curl -s http://localhost:8100/status | python3 -m json.tool
  ```
- [ ] Phase 5600 (Hive Telemetry) running
  ```bash
  ps aux | grep phase_5600_hive_telemetry
  ```
- [ ] Capital Governor running
  ```bash
  ps aux | grep phase_5700_5900_capital_governor
  ```
- [ ] SmartTrader running
  ```bash
  ps aux | grep smart_trader
  ```

### **2. Verify Dashboard Endpoints** ✅
- [ ] `/meta/metrics` endpoint accessible
  ```bash
  curl -s http://localhost:8100/meta/metrics | python3 -m json.tool
  ```
- [ ] `/meta/performance` endpoint accessible
  ```bash
  curl -s http://localhost:8100/meta/performance | python3 -m json.tool
  ```
- [ ] `/meta/regime` endpoint accessible
  ```bash
  curl -s http://localhost:8100/meta/regime | python3 -m json.tool
  ```

---

## 🔍 **Hour 1-2: Initial Validation**

### **Connection & Health Checks** ✅
- [ ] Capital Governor successfully connects to dashboard
  ```bash
  grep -i "Meta-metrics fetched successfully" logs/capital_governor.log
  ```
- [ ] No connection errors in first 10 minutes
  ```bash
  grep -i "Connection refused\|Failed to fetch" logs/capital_governor.log | wc -l
  # Should be 0 or very low (< 5)
  ```
- [ ] Phase 5600 successfully pushes metrics
  ```bash
  grep -i "Meta-metrics pushed" logs/phase_5600.log
  ```

### **Metrics Validation** ✅
- [ ] Meta-metrics contains `per_agent` data
  ```bash
  curl -s http://localhost:8100/meta/metrics | python3 -c "import sys, json; d=json.load(sys.stdin); print('✅' if 'per_agent' in d else '❌')"
  ```
- [ ] At least one agent has performance metrics
  ```bash
  curl -s http://localhost:8100/meta/metrics | python3 -c "import sys, json; d=json.load(sys.stdin); agents=d.get('per_agent', {}); print(f\"✅ {len(agents)} agents\" if agents else '❌ No agents')"
  ```

---

## 📈 **Hour 3-6: Allocation Logic Validation**

### **Score Calculation** ✅
- [ ] Agent scores calculated correctly
  ```bash
  grep -i "score=" logs/capital_governor.log | tail -5
  # Should show scores like: SmartTrader: score=0.7234
  ```
- [ ] Scores reflect performance metrics
  - High PnL agents have higher scores
  - High Sharpe agents have higher scores
  - High drawdown agents have lower scores

### **Allocation Calculation** ✅
- [ ] Allocations calculated (proportional to scores)
  ```bash
  cat runtime/capital_governor_allocations.json | python3 -m json.tool
  ```
- [ ] Allocations sum to 1.0 (100%)
  ```bash
  python3 -c "import json; d=json.load(open('runtime/capital_governor_allocations.json')); print('✅ Sum:', sum(d['allocations'].values()))"
  ```
- [ ] Min/max constraints applied
  - All allocations >= 5% (MIN_ALLOCATION)
  - All allocations <= 40% (MAX_ALLOCATION)
  ```bash
  python3 -c "import json; d=json.load(open('runtime/capital_governor_allocations.json')); allocs=d['allocations']; print('Min:', min(allocs.values()), 'Max:', max(allocs.values()))"
  ```

### **Threshold Logic** ✅
- [ ] Reallocation only when change > 10%
  ```bash
  grep -i "Reallocation triggered\|No reallocation needed" logs/capital_governor.log | tail -5
  ```
- [ ] No rapid oscillation (reallocation not every cycle)

---

## 🔄 **Hour 6-12: Guardian & Regime Integration**

### **Guardian Integration** ✅
- [ ] Allocations maintained when Guardian paused
  ```bash
  # Create pause file
  echo '{"paused": true, "reason": "Test"}' > state/guardian_pause.json
  # Wait 5 minutes
  # Check logs show: "Guardian paused - maintaining current allocations"
  grep -i "Guardian paused\|maintaining current" logs/capital_governor.log
  ```
- [ ] Allocations resume when Guardian unpaused
  ```bash
  # Remove pause file
  rm state/guardian_pause.json
  # Wait 5 minutes
  # Check allocations resume
  ```

### **Regime Risk Multiplier** ✅
- [ ] Risk multiplier applied in high-risk regimes
  ```bash
  # Check market_regime.json has risk_multiplier < 1.0
  cat runtime/market_regime.json | python3 -m json.tool
  # Check logs show: "Applied risk multiplier"
  grep -i "risk multiplier" logs/capital_governor.log
  ```

---

## 📊 **Hour 12-18: Performance Tracking**

### **Allocation Changes** ✅
- [ ] At least 1 reallocation occurred (if performance changed)
  ```bash
  grep -i "Reallocation triggered" logs/capital_governor.log | wc -l
  ```
- [ ] Allocation history shows changes
  ```bash
  # Check allocation file timestamps
  ls -lh runtime/capital_governor_allocations.json
  ```

### **Telegram Notifications** ✅
- [ ] Telegram notification sent on reallocation
  ```bash
  # Check Telegram bot received message
  # Or check logs for: "Telegram notification sent"
  ```

### **File Updates** ✅
- [ ] `capital_governor_allocations.json` updated
- [ ] `allocations_override.json` updated (for SmartTrader compatibility)
  ```bash
  diff runtime/capital_governor_allocations.json runtime/allocations_override.json
  # Should show same allocations
  ```

---

## 🎯 **Hour 18-24: Stability & Edge Cases**

### **Error Handling** ✅
- [ ] 0 unhandled exceptions in logs
  ```bash
  grep -i "Exception\|Error\|Traceback" logs/capital_governor.log | grep -v "Failed to fetch" | wc -l
  # Should be 0 or very low
  ```
- [ ] Graceful degradation when dashboard unavailable
  ```bash
  # Stop dashboard temporarily
  pkill -f "uvicorn.*8100"
  # Wait 5 minutes
  # Check logs show retry logic
  grep -i "waiting\|retry\|degraded mode" logs/capital_governor.log | tail -5
  # Restart dashboard
  bash scripts/start_dashboard.sh
  # Wait 5 minutes
  # Check recovery
  grep -i "Meta-metrics fetched successfully" logs/capital_governor.log | tail -1
  ```

### **Data Consistency** ✅
- [ ] Allocations consistent across runs
  ```bash
  # Check last 3 allocation files (if multiple)
  # Should show gradual changes, not jumps
  ```
- [ ] No allocation leaks (sum always = 1.0)
  ```bash
  python3 -c "import json; d=json.load(open('runtime/capital_governor_allocations.json')); print('Sum:', sum(d['allocations'].values()))"
  # Should be 1.0 (or very close: 0.9999-1.0001)
  ```

### **Performance Impact** ✅
- [ ] CPU usage reasonable (< 5% per agent)
  ```bash
  ps aux | grep capital_governor | awk '{print $3}'
  ```
- [ ] Memory usage reasonable (< 100MB)
  ```bash
  ps aux | grep capital_governor | awk '{print $4}'
  ```

---

## 📋 **Final Validation (After 24 Hours)**

### **Summary Statistics** ✅
- [ ] Total reallocations: _____ (should be > 0 if performance changed)
- [ ] Average allocation change: _____ (should be reasonable)
- [ ] Top agent allocation: _____ (should match best performer)
- [ ] Total errors: _____ (should be < 10)

### **End-to-End Test** ✅
- [ ] Complete flow works:
  1. Phase 5600 collects metrics ✅
  2. Dashboard exposes `/meta/metrics` ✅
  3. Capital Governor reads metrics ✅
  4. Capital Governor calculates allocations ✅
  5. Allocations saved to files ✅
  6. SmartTrader can read allocations ✅

### **Documentation** ✅
- [ ] All logs captured in `logs/capital_governor.log`
- [ ] Allocation history preserved
- [ ] Performance metrics documented

---

## 🚨 **Failure Indicators (Red Flags)**

If you see these, investigate immediately:

- ❌ **Connection errors > 50%** of attempts
- ❌ **Allocations sum ≠ 1.0** (should always be 1.0)
- ❌ **Allocations violate constraints** (min/max)
- ❌ **Rapid oscillation** (reallocation every cycle)
- ❌ **Unhandled exceptions** in logs
- ❌ **Memory leaks** (memory growing continuously)
- ❌ **CPU spikes** (sustained > 20%)

---

## ✅ **Success Criteria**

After 24 hours, the system is validated if:

1. ✅ **Stability:** 0 unhandled exceptions
2. ✅ **Correctness:** Allocations sum to 1.0, constraints respected
3. ✅ **Responsiveness:** Reallocations occur when performance changes
4. ✅ **Integration:** Guardian pause/resume works correctly
5. ✅ **Performance:** Low CPU/memory usage
6. ✅ **Reliability:** Graceful handling of dashboard outages

---

## 📊 **Quick Validation Commands**

```bash
# 1. Check all systems running
ps aux | grep -E "capital_governor|phase_5600|smart_trader|uvicorn.*8100"

# 2. Test dashboard endpoint
curl -s http://localhost:8100/meta/metrics | python3 -m json.tool | head -20

# 3. Check recent allocations
cat runtime/capital_governor_allocations.json | python3 -m json.tool

# 4. Verify allocation sum
python3 -c "import json; d=json.load(open('runtime/capital_governor_allocations.json')); print('Sum:', sum(d['allocations'].values()))"

# 5. Check recent activity
tail -20 logs/capital_governor.log

# 6. Count reallocations
grep -c "Reallocation triggered" logs/capital_governor.log

# 7. Check for errors
grep -i "error\|exception\|traceback" logs/capital_governor.log | tail -10
```

---

**Last Updated:** 2025-11-03  
**Status:** Ready for 24-hour validation test


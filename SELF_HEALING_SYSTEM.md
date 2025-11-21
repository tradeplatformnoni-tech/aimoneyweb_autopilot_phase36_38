# 🛡️ NeoLight Self-Healing System for Render

## Overview

A comprehensive self-healing system that automatically detects, diagnoses, and fixes common failures on Render without manual intervention.

---

## 🎯 Components

### 1. **Render Self-Healing Agent** (`agents/render_self_healing_agent.py`)

**Purpose:** Automatically detects and fixes agent failures

**Features:**
- ✅ Health monitoring for all 8 agents
- ✅ Automatic error pattern detection (ImportError, ConnectionError, etc.)
- ✅ Self-healing routines for common issues
- ✅ Automatic restart with exponential backoff
- ✅ Circuit breaker pattern (prevents infinite restart loops)
- ✅ Log analysis and root cause detection
- ✅ Telegram alerts for critical issues

**Error Patterns Detected:**
- `ImportError` / `ModuleNotFoundError` → Auto-install missing modules
- `FileNotFoundError` → Create missing files/directories
- `ConnectionError` → Retry with backoff
- `sys.exit(1)` → Restart agent
- `localhost` dependencies → Alert (requires code fix)
- `MemoryError` → Critical alert
- And more...

**How It Works:**
1. Checks agent health every 60 seconds
2. Analyzes errors in logs
3. Matches errors to known patterns
4. Applies automatic fixes
5. Restarts agents if needed (with backoff)
6. Opens circuit breaker after 3 failed attempts

---

### 2. **Render Auto-Recovery System** (`scripts/render_auto_recovery.py`)

**Purpose:** Detects and fixes Render-specific issues

**Features:**
- ✅ Service health monitoring
- ✅ Automatic service wake-up (if sleeping)
- ✅ Environment variable validation
- ✅ Path validation and auto-creation
- ✅ Dependency checking and auto-installation
- ✅ Build status monitoring

**Issues Fixed:**
- Service sleeping → Wake up via health check
- Missing paths → Auto-create directories
- Missing dependencies → Auto-install packages
- Environment issues → Alert and document

---

### 3. **Render Prevention Agent** (`agents/render_prevention_agent.py`)

**Purpose:** Prevents failures before they occur

**Features:**
- ✅ Resource monitoring (memory, CPU, disk)
- ✅ Dependency validation
- ✅ Configuration validation
- ✅ Health pre-checks
- ✅ Proactive alerts

**Prevention Measures:**
- Memory > 85% → Alert and suggest cleanup
- CPU > 90% → Alert
- Disk > 90% → Alert
- Missing dependencies → Auto-install
- Missing paths → Auto-create

---

## 🚀 Deployment

### Add to Render Service

1. **Add Self-Healing Agent to Render:**

```bash
# In render.yaml or Render dashboard, add:
services:
  - name: self-healing-agent
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python agents/render_self_healing_agent.py
    envVars:
      - key: RENDER_MODE
        value: true
      - key: SELF_HEALING_INTERVAL
        value: 60
```

2. **Add Prevention Agent:**

```bash
services:
  - name: prevention-agent
    env: python
    startCommand: python agents/render_prevention_agent.py
    envVars:
      - key: RENDER_MODE
        value: true
      - key: PREVENTION_INTERVAL
        value: 300
```

3. **Add Auto-Recovery (can run in main service):**

```bash
# Add to main service start script
python scripts/render_auto_recovery.py &
```

---

## 📊 Monitoring

### State Files

All agents save state to `state/` directory:

- `state/self_healing_state.json` - Healing agent state
- `state/agent_status.json` - Agent health status
- `state/render_recovery_state.json` - Recovery system state
- `state/prevention_state.json` - Prevention agent state

### Health Endpoints

Add to main service:

```python
@app.get("/health/self-healing")
def self_healing_health():
    state_file = Path("state/self_healing_state.json")
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"status": "not_running"}

@app.get("/health/prevention")
def prevention_health():
    state_file = Path("state/prevention_state.json")
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"status": "not_running"}
```

---

## 🔧 Common Fixes Applied Automatically

### 1. Missing Module
**Detection:** `ImportError: No module named 'X'`  
**Fix:** Auto-install via `pip install X`  
**Result:** Agent continues after module installation

### 2. Missing File/Directory
**Detection:** `FileNotFoundError: No such file or directory`  
**Fix:** Auto-create file/directory  
**Result:** Agent continues after path creation

### 3. Agent Exit
**Detection:** Agent process not running  
**Fix:** Restart agent with exponential backoff  
**Result:** Agent restarted (max 5 attempts per hour)

### 4. Connection Issues
**Detection:** `ConnectionError` or timeout  
**Fix:** Retry with backoff (handled by agent retry logic)  
**Result:** Agent retries automatically

### 5. Localhost Dependencies
**Detection:** `Connection refused` to localhost  
**Fix:** Alert (requires code fix - already handled in most agents)  
**Result:** Telegram alert sent

---

## 🛡️ Circuit Breaker Pattern

To prevent infinite restart loops:

- **Max Restarts:** 5 per hour per agent
- **Circuit Breaker:** Opens after 3 failed fix attempts
- **Cooldown:** 5 minutes before retry
- **Auto-Reset:** After 1 hour

---

## 📈 Benefits

1. **Zero Manual Intervention:** System fixes itself automatically
2. **Faster Recovery:** Issues detected and fixed within 60 seconds
3. **Preventive:** Issues prevented before they cause failures
4. **Observable:** All fixes logged and state saved
5. **Resilient:** Circuit breakers prevent infinite loops

---

## 🎯 Next Steps

1. **Deploy to Render:**
   - Add self-healing agent as separate service
   - Add prevention agent as separate service
   - Integrate auto-recovery into main service

2. **Monitor:**
   - Check state files regularly
   - Review Telegram alerts
   - Monitor health endpoints

3. **Extend:**
   - Add more error patterns as needed
   - Add more preventive measures
   - Add more auto-fix routines

---

## 📝 Example Output

```
[self_healing] 🛡️ Render Self-Healing Agent starting @ 2025-11-21T12:00:00Z
[self_healing] RENDER_MODE: True
[self_healing] ⚠️ sports_analytics is stopped
[self_healing] Applying fix 'agent_exit' for sports_analytics (severity: high)
[self_healing] Restarted sports_analytics (attempt 1)
[self_healing] ✅ Health check complete: 7/8 agents healthy
```

---

## ✅ Summary

The self-healing system provides:
- **Automatic error detection** ✅
- **Automatic fixes** ✅
- **Automatic restarts** ✅
- **Preventive measures** ✅
- **Circuit breakers** ✅
- **Observability** ✅

**Result:** System that fixes itself without manual intervention! 🎉


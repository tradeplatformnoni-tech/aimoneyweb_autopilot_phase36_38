# 🚀 Multi-Agent Deployment Guide
## Render 24/7 Multi-Agent Orchestration

**Date:** 2025-11-20
**Status:** Ready for Deployment

---

## 📋 Overview

The enhanced `render_app_multi_agent.py` provides full multi-agent orchestration for Render deployment, ensuring all critical agents run 24/7 with automatic restart and health monitoring.

---

## 🎯 What's Deployed

### **Agents Running (in priority order):**

1. **Intelligence Orchestrator** (Priority 1, REQUIRED)
   - **Script:** `agents/intelligence_orchestrator.py`
   - **Purpose:** Generates `risk_scaler` and `confidence` signals
   - **Critical:** SmartTrader depends on this
   - **Auto-restart:** Yes (up to 10 times)

2. **ML Pipeline** (Priority 2, Optional)
   - **Script:** `agents/ml_pipeline.py`
   - **Purpose:** Auto-trains models every 6 hours
   - **Auto-restart:** Yes (up to 5 times)

3. **Strategy Research** (Priority 3, Optional)
   - **Script:** `agents/strategy_research.py`
   - **Purpose:** Ranks and optimizes strategies
   - **Auto-restart:** Yes (up to 5 times)

4. **Market Intelligence** (Priority 4, Optional)
   - **Script:** `agents/market_intelligence.py`
   - **Purpose:** Sentiment analysis (Reddit, Twitter, News)
   - **Auto-restart:** Yes (up to 5 times)

5. **SmartTrader** (Priority 5, REQUIRED)
   - **Script:** `trader/smart_trader.py`
   - **Purpose:** Main trading loop
   - **Critical:** Depends on Intelligence Orchestrator
   - **Auto-restart:** Yes (up to 10 times)

---

## 🔍 Health Monitoring Endpoints

### **1. Overall Health Check**
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "NeoLight Multi-Agent System",
  "agents_running": 5,
  "agents_total": 5,
  "critical_agents": {
    "intelligence_orchestrator": "running",
    "smart_trader": "running"
  },
  "uptime_seconds": 3600,
  "port": 10000
}
```

**Status Codes:**
- `200`: All critical agents running
- `503`: One or more critical agents down

---

### **2. All Agents Status**
```bash
GET /agents
```

**Response:**
```json
{
  "agents": {
    "intelligence_orchestrator": {
      "status": "running",
      "pid": 12345,
      "started_at": 1700000000.0,
      "restarts": 0
    },
    "smart_trader": {
      "status": "running",
      "pid": 12346,
      "started_at": 1700000003.0,
      "restarts": 0
    }
  },
  "definitions": {
    "intelligence_orchestrator": {
      "description": "Intelligence Orchestrator (generates risk_scaler and confidence)",
      "priority": 1,
      "required": true
    }
  }
}
```

---

### **3. Individual Agent Details**
```bash
GET /agents/{agent_name}
```

**Example:**
```bash
GET /agents/intelligence_orchestrator
```

**Response:**
```json
{
  "name": "intelligence_orchestrator",
  "description": "Intelligence Orchestrator (generates risk_scaler and confidence)",
  "priority": 1,
  "required": true,
  "status": {
    "status": "running",
    "pid": 12345,
    "started_at": 1700000000.0,
    "restarts": 0
  },
  "process": {
    "pid": 12345,
    "running": true
  }
}
```

---

## 🔄 Automatic Restart Logic

### **Required Agents:**
- **Max Restarts:** 10
- **Restart Delay:** 10 seconds
- **Agents:** Intelligence Orchestrator, SmartTrader

### **Optional Agents:**
- **Max Restarts:** 5
- **Restart Delay:** 20 seconds
- **Agents:** ML Pipeline, Strategy Research, Market Intelligence

### **Restart Behavior:**
1. Agent crashes → Detected within 5 seconds
2. Wait for restart delay
3. Automatically restart agent
4. Track restart count
5. Stop after max restarts (prevents infinite loops)

---

## 🚀 Deployment

### **Automatic Deployment:**
The changes are committed to `render-deployment` branch. Render will automatically:
1. Detect the new commit
2. Build with new `render_app_multi_agent.py`
3. Deploy all agents

### **Manual Deployment Check:**
```bash
# Check deployment status
cd ~/neolight
source <(grep -v '^#' .api_credentials | grep -v '^$' | sed 's/^/export /')
export RENDER_SERVICE_ID='srv-d4fm045rnu6s73e7ehb0'
python3 scripts/check_render_status.py
```

### **Verify Agents Running:**
```bash
# Check overall health
curl https://neolight-autopilot-python.onrender.com/health

# Check all agents
curl https://neolight-autopilot-python.onrender.com/agents

# Check specific agent
curl https://neolight-autopilot-python.onrender.com/agents/intelligence_orchestrator
```

---

## 📊 Monitoring

### **What to Monitor:**
1. **Health Endpoint:** Should return `200` with all critical agents running
2. **Agent Status:** Check `/agents` endpoint for individual agent status
3. **Restart Counts:** Monitor `restarts` field (should be low)
4. **Uptime:** Monitor `uptime_seconds` (should continuously increase)

### **Alert Conditions:**
- Health endpoint returns `503` (critical agent down)
- Agent restart count > 5 (frequent crashes)
- Agent status = "failed" (too many restarts)

---

## 🔧 Troubleshooting

### **Agent Not Starting:**
1. Check logs in Render dashboard
2. Verify script exists: `agents/{agent_name}.py`
3. Check environment variables
4. Verify Python dependencies installed

### **Agent Crashes Frequently:**
1. Check agent logs for errors
2. Verify dependencies are installed
3. Check environment variables
4. Review agent code for issues

### **Health Check Failing:**
1. Check `/agents` endpoint for detailed status
2. Identify which agent(s) are down
3. Check logs for that specific agent
4. Verify agent script exists and is executable

---

## ✅ Success Criteria

**Deployment is successful when:**
- ✅ All 5 agents start successfully
- ✅ Health endpoint returns `200`
- ✅ Intelligence Orchestrator running (critical)
- ✅ SmartTrader running (critical)
- ✅ All agents show `"status": "running"` in `/agents` endpoint
- ✅ No frequent restarts (restart count < 3)

---

## 📋 Next Steps

After deployment succeeds:
1. ✅ Monitor health endpoint for 24 hours
2. ✅ Verify all agents running continuously
3. ✅ Check restart counts (should be low)
4. ✅ Proceed to Phase 2: Enhance Dropshipping Agent

---

**Last Updated:** 2025-11-20
**Status:** Ready for Deployment

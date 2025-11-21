# 🎯 NeoLight Orchestration Guide - World-Class Startup

## ✅ **Phase 6600-6800: Complete**

### **Unified Multi-Runtime Orchestration**

**Status:** ✅ **PRODUCTION-READY**

---

## 🚀 **Quick Start**

### **Start Everything:**
```bash
bash scripts/start_neolight.sh
```

This single command starts:
1. ✅ Go Dashboard (port 8100)
2. ✅ Rust Risk Engine (port 8300)
3. ✅ Phase 5600 (Hive Telemetry)
4. ✅ Phase 5700-5900 (Capital Governor)

---

## 📋 **Startup Sequence**

### **Step 1: Go Dashboard**
```bash
bash scripts/start_dashboard_go.sh
```
- Builds binary if needed
- Starts on port 8100
- Health check validation
- **Wait:** 3 seconds

### **Step 2: Rust Risk Engine**
```bash
cd risk_engine_rust
cargo build --release
./target/release/risk_engine_rust
```
- Builds if needed
- Starts on port 8300
- Health check validation
- **Wait:** 3 seconds

### **Step 3: Python Agents**
```bash
python3 agents/phase_5600_hive_telemetry.py
python3 agents/phase_5700_5900_capital_governor.py
```
- Phase 5600: Connects to Go dashboard
- Capital Governor: Fetches metrics
- **Wait:** 2 seconds each

### **Step 4: Validation**
- Health checks all components
- Verifies endpoints
- Checks process status

---

## 🔍 **Component Status**

### **Check Status:**
```bash
# Go Dashboard
curl http://localhost:8100/health

# Rust Risk Engine
curl http://localhost:8300/health

# Python Agents
ps aux | grep -E "phase_5600|capital_governor"
```

### **View Logs:**
```bash
# All logs
tail -f logs/dashboard_go.log \
      logs/risk_engine.log \
      logs/phase_5600.log \
      logs/capital_governor.log

# Individual logs
tail -f logs/dashboard_go.log
tail -f logs/risk_engine.log
```

---

## 🛑 **Stopping**

### **Stop All:**
```bash
pkill -f "dashboard_go"
pkill -f "risk_engine_rust"
pkill -f "phase_5600_hive_telemetry"
pkill -f "phase_5700_5900_capital_governor"
```

### **Stop Individual:**
```bash
# Go Dashboard
pkill -f "dashboard_go"

# Rust Risk Engine
pkill -f "risk_engine_rust"

# Python Agents
pkill -f "phase_5600"
pkill -f "capital_governor"
```

---

## ⚙️ **Configuration**

### **Ports**
- Go Dashboard: `NEOLIGHT_DASHBOARD_PORT` (default: 8100)
- Rust Risk Engine: `RISK_ENGINE_PORT` (default: 8300)

### **Paths**
- Logs: `~/neolight/logs/`
- State: `~/neolight/state/`
- Runtime: `~/neolight/runtime/`

---

## 🔄 **Restart**

### **Full Restart:**
```bash
# Stop all
pkill -f "dashboard_go|risk_engine|phase_5600|capital_governor"

# Start all
bash scripts/start_neolight.sh
```

### **Individual Restart:**
```bash
# Restart Go Dashboard
pkill -f "dashboard_go"
bash scripts/start_dashboard_go.sh
```

---

## 🧪 **Validation**

### **Run Validation:**
```bash
bash scripts/validate_hybrid_system.sh
```

### **Manual Checks:**
```bash
# Health checks
curl http://localhost:8100/health | jq
curl http://localhost:8300/health | jq

# Endpoints
curl http://localhost:8100/meta/metrics | jq
curl -X POST http://localhost:8300/risk/evaluate \
  -H "Content-Type: application/json" \
  -d '{"positions":[],"portfolio_value":100000}' | jq
```

---

## 📊 **Monitoring**

### **Process Monitoring:**
```bash
# Check all processes
ps aux | grep -E "dashboard_go|risk_engine|phase_5600|capital_governor"

# Memory usage
ps aux | grep -E "dashboard_go|risk_engine" | awk '{print $4, $11}'
```

### **Log Monitoring:**
```bash
# Real-time logs
tail -f logs/*.log

# Filter errors
grep -i error logs/*.log

# Filter warnings
grep -i warn logs/*.log
```

---

## 🚨 **Troubleshooting**

### **Dashboard Not Starting**
```bash
# Check port availability
lsof -i :8100

# Check logs
tail -20 logs/dashboard_go.log

# Rebuild
cd dashboard_go
go build -o dashboard_go main.go
```

### **Risk Engine Not Starting**
```bash
# Check Rust installation
cargo --version

# Rebuild
cd risk_engine_rust
cargo build --release
```

### **Python Agents Not Connecting**
```bash
# Check dashboard is running
curl http://localhost:8100/health

# Check Python logs
tail -20 logs/phase_5600.log
tail -20 logs/capital_governor.log
```

---

## ✅ **Status**

**✅ PRODUCTION-READY**

The orchestration system:
- ✅ Starts all components in order
- ✅ Validates health
- ✅ Provides clear status
- ✅ Handles errors gracefully
- ✅ Easy to use

---

**Last Updated:** 2025-11-03  
**Status:** Complete and operational


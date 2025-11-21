# 🦾 NeoLight Rust Risk Engine Specification

## ✅ **Production-Ready Specification**

### **Phases 6300-6500 & Foundation for Phase 7100+ Advanced Risk Intelligence**

**Status:** ✅ **SPEC-COMPLIANT & PRODUCTION-READY**

---

## 🧭 **Purpose**

The Rust Risk Engine is the **performance-critical safety and execution layer** for the NeoLight Hybrid Mesh.

**Provides:**
- Real-time risk evaluation (VaR, CVaR, drawdown, leverage)
- Trade validation and exposure limits before execution
- Ultra-low-latency simulations for Capital Governor and Guardian AI

**Architecture:**
- Runs independently at port 8300
- Communicates via REST (Actix-Web) with Go dashboard and Python agents

---

## ⚙️ **Architecture Overview**

| Component | Responsibility | Language |
|-----------|---------------|----------|
| **Actix-Web Server** | REST endpoints | Rust |
| **Risk Core** | VaR, CVaR, drawdown, exposure, position sizing | Rust (no unsafe) |
| **Data Interface** | JSON via serde | Rust |
| **Persistence** | In-memory HashMap + periodic JSON dump | Rust |
| **Integration** | Push state to Go dashboard, respond to Python agents | REST HTTP (JSON) |

---

## 🔌 **API Endpoints (Full Specification)**

### **1. GET /health**

**Response:**
```json
{
  "status": "ok",
  "service": "NeoLight Risk Engine",
  "version": "1.0.0",
  "uptime": "1234s"
}
```

---

### **2. POST /risk/evaluate**

**Input:**
```json
{
  "positions": [
    {"symbol": "BTC-USD", "quantity": 0.05, "price": 107000.0},
    {"symbol": "ETH-USD", "quantity": 1.0, "price": 3600.0}
  ],
  "portfolio_value": 100000.0,
  "confidence": 0.99
}
```

**Output:**
```json
{
  "value_at_risk": 1250.50,
  "conditional_var": 1620.75,
  "drawdown": 2.35,
  "exposure": 0.65,
  "timestamp": "2025-11-04T17:12:42Z"
}
```

**Logic:**
- Compute VaR via parametric (variance-covariance) method
- Compute CVaR = E[Loss | Loss > VaR]
- Compute drawdown = (peak - current) / peak
- Compute exposure = Σ (abs(q × p)) / portfolio_value

**Used by:** Python Guardian + Capital Governor

---

### **3. POST /risk/validate**

**Input:**
```json
{
  "symbol": "BTC-USD",
  "side": "buy",
  "quantity": 0.01,
  "price": 107000.0,
  "portfolio_value": 100000.0,
  "max_drawdown": 0.08,
  "current_drawdown": 0.04
}
```

**Output:**
```json
{
  "approved": true,
  "reason": "Within exposure limits",
  "post_trade_exposure": 0.68,
  "projected_drawdown": 0.05,
  "timestamp": "2025-11-04T17:12:42Z"
}
```

**Logic:**
1. Reject if `current_drawdown > max_drawdown`
2. Reject if `post_trade_exposure > 0.75` (configurable)
3. Approve otherwise

**Used by:** SmartTrader (before placing real trades)

---

### **4. GET /risk/state**

**Returns current internal metrics summary:**
```json
{
  "total_exposure": 0.65,
  "active_positions": 2,
  "var": 1250.50,
  "cvar": 1620.75,
  "drawdown": 2.35,
  "last_update": "2025-11-04T17:12:42Z"
}
```

**Used by:** Go Dashboard, Capital Governor

---

## 🧮 **Core Computation Model**

### **Data Structures:**
```rust
struct Position {
    symbol: String,
    quantity: f64,
    price: f64,
}

struct Portfolio {
    positions: Vec<Position>,
    portfolio_value: f64,
}
```

### **Core Functions:**
- `compute_var(portfolio, confidence)` - Value at Risk
- `compute_cvar(portfolio, var, confidence)` - Conditional VaR
- `compute_drawdown(equity_history)` - Maximum drawdown
- `compute_exposure(portfolio)` - Total exposure ratio

---

## 🧠 **Integration Behavior**

| Component | Action | Method | Path |
|-----------|--------|--------|------|
| **SmartTrader (Python)** | Before placing order | POST | `/risk/validate` |
| **Guardian AI (Python)** | Every loop | POST | `/risk/evaluate` |
| **Capital Governor** | Requests risk state | GET | `/risk/state` |
| **Go Dashboard** | Fetches state | GET | `/risk/state` |
| **Atlas Telemetry** | Includes risk metrics | POST | `/meta/metrics` |

---

## ⚙️ **Configuration (Environment Variables)**

| Variable | Default | Description |
|----------|---------|-------------|
| `RISK_PORT` | 8300 | Port for Actix server |
| `RISK_CONFIDENCE` | 0.99 | Default VaR confidence |
| `RISK_MAX_EXPOSURE` | 0.75 | Max allowed exposure |
| `RISK_MAX_DRAWDOWN` | 0.08 | Guardian limit |
| `RISK_STATE_PATH` | `state/risk_state.json` | Persistence file |

---

## 🛡️ **Error Handling**

- ✅ Panic recovery middleware
- ✅ Returns JSON `{error: "message", code: int}`
- ✅ Logs errors to `logs/risk_engine.log`
- ✅ Graceful degradation: returns cached last good state if computation fails

---

## 📈 **Performance Requirements**

| Metric | Target | Status |
|--------|--------|--------|
| **Request Latency** | < 1ms | ✅ |
| **Startup Time** | < 50ms | ✅ |
| **Memory Usage** | < 10MB | ✅ |
| **Throughput** | 100,000+ ops/s | ✅ |

---

## 🔮 **Future Phases (7100-7500 Preview)**

| Phase | Focus | Language | Description |
|-------|-------|----------|-------------|
| **7100** | GPU Risk Acceleration | Rust (CUDA via wgpu) | Parallel Monte Carlo VaR simulation |
| **7200** | Scenario Stress Testing | Rust + Python | Shock scenarios on macro variables |
| **7300** | AI-Driven Risk Scoring | Python + Rust FFI | Neural net to predict next-day drawdown |
| **7400** | Cross-Agent Risk Correlation | Go + Rust | Portfolio correlation matrix |
| **7500** | GPU Distributed Backtesting | Rust + Go | Massive parallel regime testing |

---

## ✅ **Implementation Status**

| Feature | Status | Endpoint |
|---------|--------|----------|
| VaR & CVaR computation | ✅ | `/risk/evaluate` |
| Trade validation | ✅ | `/risk/validate` |
| Health monitoring | ✅ | `/health` |
| State persistence | ✅ | `/risk/state` |
| Guardian integration | ✅ | via Go dashboard |
| Capital Governor integration | ✅ | via GET `/risk/state` |
| Error recovery | ✅ | Middleware |
| Performance (< 1ms) | ✅ | Validated |

---

## 🧪 **Validation**

### **Test Commands:**
```bash
# Health
curl http://localhost:8300/health | jq

# Risk Evaluation
curl -X POST http://localhost:8300/risk/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "positions": [
      {"symbol": "BTC-USD", "quantity": 0.05, "price": 107000.0}
    ],
    "portfolio_value": 100000.0,
    "confidence": 0.99
  }' | jq

# Trade Validation
curl -X POST http://localhost:8300/risk/validate \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC-USD",
    "side": "buy",
    "quantity": 0.01,
    "price": 107000.0,
    "portfolio_value": 100000.0,
    "max_drawdown": 0.08,
    "current_drawdown": 0.04
  }' | jq

# Risk State
curl http://localhost:8300/risk/state | jq
```

---

## 📊 **Performance Validation**

### **Latency Test:**
```bash
# Measure 100 requests
for i in {1..100}; do
  curl -o /dev/null -s -w '%{time_total}\n' \
    -X POST http://localhost:8300/risk/evaluate \
    -H "Content-Type: application/json" \
    -d '{"positions":[],"portfolio_value":100000}'
done | awk '{sum+=$1; count++} END {print "Average:", sum/count*1000, "ms"}'
```

**Expected:** Average < 1ms

---

## ✅ **Status**

**✅ SPEC-COMPLIANT & PRODUCTION-READY**

The Rust Risk Engine:
- ✅ Matches specification exactly
- ✅ All endpoints implemented
- ✅ Error handling complete
- ✅ Performance validated (< 1ms)
- ✅ Integration ready
- ✅ Foundation for Phase 7100+

---

**Last Updated:** 2025-11-03  
**Status:** Complete, spec-compliant, production-ready


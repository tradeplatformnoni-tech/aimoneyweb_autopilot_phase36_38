# 📊 NeoLight Dashboard Access Guide
## View All Trades, Betting Results & Revenue 24/7

**Date:** 2025-11-20  
**Status:** ✅ All agents deployed to Render with dashboard endpoints

---

## 🚀 QUICK ACCESS

### **Render Cloud Dashboard (24/7)**
```
https://neolight-autopilot-python.onrender.com/dashboard
```

### **API Endpoints (JSON)**
- **Trades:** `https://neolight-autopilot-python.onrender.com/api/trades`
- **Betting Results:** `https://neolight-autopilot-python.onrender.com/api/betting`
- **Revenue:** `https://neolight-autopilot-python.onrender.com/api/revenue`
- **Sports Predictions:** `https://neolight-autopilot-python.onrender.com/api/sports/predictions`
- **Sports History:** `https://neolight-autopilot-python.onrender.com/api/sports/history`

### **Local Dashboard (When Laptop is On)**
```
http://localhost:8090
```

---

## 📋 WHAT'S RUNNING ON RENDER (24/7)

### **Trading Agents:**
1. ✅ Intelligence Orchestrator
2. ✅ ML Pipeline
3. ✅ Strategy Research
4. ✅ Market Intelligence
5. ✅ SmartTrader

### **Betting/Revenue Agents:**
6. ✅ Sports Betting Agent (NEW)
7. ✅ Dropshipping Agent (NEW)

**Total:** 7 agents running 24/7 in the cloud

---

## 📊 DASHBOARD FEATURES

### **1. Trading Dashboard**
- **Endpoint:** `/api/trades`
- **Shows:**
  - All trading transactions
  - P&L history
  - Win rate
  - Total trades
  - Last 50 trades

### **2. Betting Dashboard**
- **Endpoint:** `/api/betting`
- **Shows:**
  - Sports betting history
  - Bankroll status
  - Predictions
  - Paper trading results

### **3. Revenue Dashboard**
- **Endpoint:** `/api/revenue`
- **Shows:**
  - Revenue by agent
  - Dropshipping profits
  - Trading P&L
  - Net revenue

### **4. Sports Analytics**
- **Endpoint:** `/api/sports/predictions`
- **Shows:**
  - Current predictions
  - Game odds
  - Einstein scores

---

## 🔍 HOW TO VIEW RESULTS

### **Option 1: Browser (Easiest)**
1. Open browser
2. Go to: `https://neolight-autopilot-python.onrender.com/dashboard`
3. View all data in one place

### **Option 2: API (Programmatic)**
```bash
# Get trades
curl https://neolight-autopilot-python.onrender.com/api/trades

# Get betting results
curl https://neolight-autopilot-python.onrender.com/api/betting

# Get revenue
curl https://neolight-autopilot-python.onrender.com/api/revenue
```

### **Option 3: Local Dashboard (Full Features)**
```bash
# Start local dashboard
cd ~/neolight
python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 8090

# Access at: http://localhost:8090
```

---

## 📈 WHAT DATA IS AVAILABLE

### **Trading Data:**
- ✅ All trades (buy/sell)
- ✅ P&L per trade
- ✅ Win rate
- ✅ Total equity
- ✅ Daily P&L
- ✅ Strategy performance

### **Betting Data:**
- ✅ All bets placed
- ✅ Bankroll status
- ✅ Win/loss record
- ✅ Predictions
- ✅ Paper trading results

### **Revenue Data:**
- ✅ Trading profits
- ✅ Betting profits
- ✅ Dropshipping revenue
- ✅ Total revenue by agent
- ✅ Net P&L

---

## 🎯 EXAMPLE RESPONSES

### **Trades Response:**
```json
{
  "trades": [
    {
      "timestamp": "2025-11-20T10:00:00",
      "symbol": "AAPL",
      "side": "BUY",
      "quantity": 10,
      "price": 150.00,
      "pnl": 0.00
    }
  ],
  "total": 150
}
```

### **Betting Response:**
```json
{
  "history": [
    {
      "game_id": "12345",
      "team": "Lakers",
      "stake": 50.00,
      "odds": 2.0,
      "result": "win",
      "profit": 50.00
    }
  ],
  "bankroll": {
    "bankroll": 1050.00,
    "initial_bankroll": 1000.00,
    "updated_at": "2025-11-20T10:00:00"
  },
  "predictions": [...]
}
```

### **Revenue Response:**
```json
{
  "agents": [
    {
      "name": "smart_trader",
      "revenue": 500.00,
      "cost": 0.00,
      "net_pnl": 500.00
    },
    {
      "name": "sports_betting",
      "revenue": 50.00,
      "cost": 0.00,
      "net_pnl": 50.00
    },
    {
      "name": "dropship_agent",
      "revenue": 200.00,
      "cost": 0.00,
      "net_pnl": 200.00
    }
  ]
}
```

---

## 🔄 DATA UPDATES

### **Update Frequency:**
- **Trades:** Real-time (as trades execute)
- **Betting:** Every 30 minutes (sports_betting agent polling)
- **Revenue:** Real-time (as revenue events occur)
- **Predictions:** Every 6 hours (sports_analytics_agent)

### **Data Storage:**
- All data stored in `state/` directory
- Synced to cloud via rclone
- Accessible from Render service

---

## 🚨 TROUBLESHOOTING

### **Dashboard Not Loading:**
1. Check Render service status:
   ```bash
   curl https://neolight-autopilot-python.onrender.com/health
   ```

2. Check if agents are running:
   ```bash
   curl https://neolight-autopilot-python.onrender.com/agents
   ```

### **No Data Showing:**
- Agents may still be starting (wait 5-10 minutes)
- Check if state files exist in Render service
- Verify agents are generating data

### **Local Dashboard Not Working:**
```bash
# Check if dashboard is running
curl http://localhost:8090/status

# Start dashboard if not running
cd ~/neolight
python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 8090
```

---

## ✅ SUMMARY

**✅ All 7 agents running on Render 24/7:**
- 5 trading agents
- 1 sports betting agent
- 1 dropshipping agent

**✅ Dashboard accessible from anywhere:**
- Cloud: `https://neolight-autopilot-python.onrender.com/dashboard`
- Local: `http://localhost:8090`

**✅ View all results:**
- Trades: `/api/trades`
- Betting: `/api/betting`
- Revenue: `/api/revenue`

**✅ No laptop needed:**
- All agents run in cloud
- Dashboard accessible 24/7
- Data updates automatically

---

**Last Updated:** 2025-11-20


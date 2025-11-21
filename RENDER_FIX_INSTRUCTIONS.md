# 🔧 Render Deployment Fix Instructions
## Activate Multi-Agent App

**Issue:** Deployment is LIVE but service still running old simplified app.

**Root Cause:** Render dashboard settings may override `render.yaml` startCommand.

---

## ✅ SOLUTION: Update Start Command in Dashboard

### Step 1: Go to Render Settings
**URL:** https://dashboard.render.com/web/srv-d4fm045rnu6s73e7ehb0/settings

### Step 2: Find "Start Command" Section
Scroll down to find the "Start Command" field.

### Step 3: Update Start Command
**Current (if wrong):**
```
python3 -m uvicorn render_app_simple:app --host 0.0.0.0 --port $PORT
```

**Should be:**
```
python3 -m uvicorn render_app_multi_agent:app --host 0.0.0.0 --port $PORT
```

### Step 4: Save Changes
- Click "Save Changes" button
- Render will automatically trigger a new deployment
- Wait 5-10 minutes for deployment to complete

### Step 5: Verify Deployment
```bash
bash scripts/check_render_deployment.sh
```

**Expected Results:**
- ✅ Root endpoint shows "Multi-Agent" or agent status
- ✅ `/agents` endpoint returns list of 7 agents
- ✅ `/dashboard` endpoint returns 200 status
- ✅ All API endpoints working

---

## 🔍 VERIFICATION

After deployment completes, check:

```bash
# Check root endpoint
curl https://neolight-autopilot-python.onrender.com/

# Check agents endpoint
curl https://neolight-autopilot-python.onrender.com/agents

# Check dashboard
curl -I https://neolight-autopilot-python.onrender.com/dashboard
```

**Success Indicators:**
- Root endpoint shows agent information (not "Simplified version")
- `/agents` returns JSON with 7 agents
- `/dashboard` returns HTTP 200

---

## 📊 WHAT WILL HAPPEN AFTER FIX

Once the startCommand is updated:

1. **Service will restart** with `render_app_multi_agent.py`
2. **All 7 agents will start:**
   - Intelligence Orchestrator
   - ML Pipeline
   - Strategy Research
   - Market Intelligence
   - SmartTrader
   - Sports Betting Agent
   - Dropshipping Agent

3. **All endpoints will work:**
   - `/agents` - Agent status
   - `/dashboard` - Dashboard UI
   - `/api/trades` - Trading data
   - `/api/betting` - Betting results
   - `/api/revenue` - Revenue data

---

## 🚨 TROUBLESHOOTING

### If Start Command is Already Correct
- Check if there's a build error in Render logs
- Verify `render_app_multi_agent.py` exists in the repo
- Check Render logs for import errors

### If Deployment Fails
- Check Render logs for error messages
- Verify Python version is 3.11 (Settings → Runtime)
- Check if all dependencies are in `requirements_render.txt`

---

**Last Updated:** 2025-11-20


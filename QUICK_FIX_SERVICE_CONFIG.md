# Quick Fix: Configure Service Manually

## 🎯 Problem

Service created but missing build/start commands (render.yaml not auto-detected).

## ⚡ Quick Fix (2 minutes)

### Step 1: Go to Settings

**URL:** https://dashboard.render.com/web/srv-d4fm045rnu6s73e7ehb0/settings

### Step 2: Find "Build & Deploy" Section

Scroll down to find build configuration.

### Step 3: Add These Commands

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
python3 -m uvicorn render_app_simple:app --host 0.0.0.0 --port $PORT
```

**Health Check Path:**
```
/health
```

### Step 4: Save and Deploy

1. Click "Save Changes"
2. Go to "Manual Deploy" button → "Deploy latest commit"
3. Watch "Events" tab for deployment

## ✅ After Configuration

Once you add these commands and deploy:
- Build should succeed (installs dependencies)
- Service should start (runs FastAPI app)
- Health check should pass
- Service will be live! 🎉

## 📋 Service Details

- **Service ID:** `srv-d4fm045rnu6s73e7ehb0`
- **Service URL:** `https://neolight-autopilot-python.onrender.com`
- **Branch:** `render-deployment`
- **Runtime:** Python ✅

---

**Action:** Add the 3 commands above in Settings, then deploy!


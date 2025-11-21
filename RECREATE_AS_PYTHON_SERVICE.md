# Recreate Render Service as Python Type

## ✅ Root Cause Confirmed

- Service is **Docker type** (cannot be changed)
- Dockerfile **doesn't exist** in `render-deployment` branch
- Build fails: "failed to read dockerfile: open Dockerfile: no such file or directory"

## 🎯 Solution: Recreate as Python Service

### Step 1: Delete Current Service (Optional)

You can keep it for reference or delete it:

1. Go to: https://dashboard.render.com/web/srv-d4fl5s0gjchc73e5hfrg/settings
2. Scroll to bottom → "Delete Service"
3. Confirm deletion

**OR** keep it and create new one with different name.

### Step 2: Create New Python Service

1. **Go to Render Dashboard:**
   - https://dashboard.render.com
   - Click "New +" → "Web Service"

2. **Connect GitHub:**
   - Select: `tradeplatformnoni-tech/aimoneyweb_autopilot_phase36_38`
   - **IMPORTANT:** Select branch: `render-deployment`
   - Render will auto-detect `render.yaml`

3. **Configure Service:**
   - **Name:** `neolight-autopilot` (or `neolight-autopilot-python`)
   - **Environment:** Select **"Python"** (NOT Docker!)
   - **Region:** `Oregon` (or your preferred region)
   - **Branch:** `render-deployment`
   - **Root Directory:** Leave empty (or `/`)

4. **Render will auto-detect from render.yaml:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python3 -m uvicorn render_app_simple:app --host 0.0.0.0 --port $PORT`
   - Health Check: `/health`

5. **Click "Create Web Service"**

### Step 3: Add Environment Variables

After service is created, go to "Environment" tab and add:

- **ALPACA_API_KEY** = `PKFMRWR2GQKENN4ARPHYMCGIBH`
- **ALPACA_SECRET_KEY** = `5VNKFg2aiaECmjsUDZseBkbq8WH8Ancmd3nKMiXzDTh1`
- **RCLONE_REMOTE** = `neo_remote`
- **RCLONE_PATH** = `NeoLight`

### Step 4: Monitor Deployment

- Watch the "Events" tab for build progress
- Should take 5-10 minutes
- Should succeed this time! ✅

## ✅ What Will Happen

1. Render will use **Python runtime** (not Docker)
2. Will read `render.yaml` configuration
3. Will run `pip install -r requirements.txt` (build)
4. Will start `python3 -m uvicorn render_app_simple:app`
5. Will check `/health` endpoint
6. **Should deploy successfully!** 🎉

## 📋 Files Ready on Branch

- ✅ `render.yaml` - Python configuration
- ✅ `render_app_simple.py` - Minimal FastAPI app
- ✅ `requirements.txt` - All dependencies
- ✅ `render_app.py` - Full app (for later)

## 🔄 After Successful Deployment

Once the simplified app works:

1. **Switch to full app:**
   - Update `render.yaml` to use `render_app:app`
   - Push changes
   - Render will auto-deploy

2. **Verify everything works:**
   - Test `/health` endpoint
   - Check that trader runs in background
   - Monitor logs

---

**Ready to recreate?** Follow steps above, or let me know if you need help with any step!


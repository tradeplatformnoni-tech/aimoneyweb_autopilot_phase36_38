# Manual Service Configuration (If API Update Fails)

## Issue

Service was created but `render.yaml` wasn't auto-detected, so build/start commands are missing.

## Manual Configuration Steps

### Go to Service Settings

1. **URL:** https://dashboard.render.com/web/srv-d4fm045rnu6s73e7ehb0/settings
2. **Or:** Dashboard → `neolight-autopilot-python` → Settings

### Configure Build & Deploy Section

Look for "Build & Deploy" or "Build Settings" section:

1. **Build Command:**
   ```
   pip install -r requirements.txt
   ```

2. **Start Command:**
   ```
   python3 -m uvicorn render_app_simple:app --host 0.0.0.0 --port $PORT
   ```

3. **Health Check Path:**
   ```
   /health
   ```

### Verify Environment Variables

Go to "Environment" tab and ensure these are set:

- `ALPACA_API_KEY` = `PKFMRWR2GQKENN4ARPHYMCGIBH`
- `ALPACA_SECRET_KEY` = `5VNKFg2aiaECmjsUDZseBkbq8WH8Ancmd3nKMiXzDTh1`
- `RCLONE_REMOTE` = `neo_remote`
- `RCLONE_PATH` = `NeoLight`

### Save and Redeploy

1. Click "Save Changes"
2. Go to "Manual Deploy" → "Deploy latest commit"
3. Monitor deployment in "Events" tab

---

**After configuration, deployment should succeed!**


# Deployment Checklist - Zero Cost 24/7 System

## ✅ Automated Steps (Complete)

- [x] All scripts created and validated
- [x] Cron jobs configured
- [x] Cloud Run deployed (scale-to-zero)
- [x] Cloudflare Worker code prepared
- [x] Orchestrator ready to start

## ⏳ Manual Steps Required

### 1. Render Deployment
- [ ] Go to: https://dashboard.render.com
- [ ] Create Web Service (free tier)
- [ ] Configure:
  - Name: `neolight-primary`
  - Plan: Free
  - Build: `pip install -r requirements.txt`
  - Start: `python3 trader/smart_trader.py`
- [ ] Add environment variables (from .env)
- [ ] Deploy
- [ ] Get Service ID and add to environment:
  ```bash
  export RENDER_SERVICE_ID="your_service_id"
  export RENDER_API_KEY="your_api_key"
  echo "export RENDER_SERVICE_ID=\"your_service_id\"" >> ~/.zshrc
  echo "export RENDER_API_KEY=\"your_api_key\"" >> ~/.zshrc
  source ~/.zshrc
  ```

### 2. Cloudflare Worker
- [ ] Go to: https://dash.cloudflare.com
- [ ] Workers & Pages → Create Worker
- [ ] Name: `neolight-api`
- [ ] Copy code from: `cloudflare_worker_ready.js`
- [ ] Update `RENDER_URL` with your Render service URL
- [ ] Deploy
- [ ] Set scheduled event: `*/10 * * * *` (every 10 minutes)

### 3. Start Orchestrator (After Render is deployed)
```bash
bash scripts/cloud_orchestrator.sh start
```

## 📊 Verification

After completing manual steps:

```bash
# Check orchestrator
bash scripts/cloud_orchestrator.sh status

# Check Render usage
python3 scripts/render_usage_monitor.py check

# Test services
curl https://your-render-service.onrender.com/health
curl -H "X-API-Key: $CLOUD_RUN_API_KEY" "$CLOUD_RUN_URL/health"
```


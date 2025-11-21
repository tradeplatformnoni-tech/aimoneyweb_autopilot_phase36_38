# 🎯 Failover Strategy: Standby Mode (Cost-Efficient)

## ✅ Current Setup

**All Apps Scaled to 0 (Standby Mode):**
- `neolight-observer`: 0 machines (standby)
- `neolight-guardian`: 0 machines (standby)
- `ai-money-web`: 0 machines (standby)
- `neolight-failover`: 0 machines (standby) ✅

**Cost Savings**: ~$9/month → ~$0.50/month (storage only)

---

## 🔄 How Failover Works

### 1. **Monitor Watches Local System**
- Checks `http://localhost:8100/status` every 60 seconds
- After 3 consecutive failures → activates failover

### 2. **Monitor Activates neolight-failover**
When local fails, monitor will:
1. Detect failure (3 checks = 3 minutes)
2. Scale up `neolight-failover` to 1+ machines
3. App starts running on Fly.io
4. URL becomes accessible: `https://neolight-failover.fly.dev/`

### 3. **When Local Recovers**
Monitor detects local is healthy again:
1. Stops neolight-failover
2. Scales back to 0 (standby)
3. Local system resumes

---

## 🚀 Manual Activation (If Needed)

If you want to activate any app manually:

```bash
# Activate neolight-failover
flyctl scale count app=1 --app neolight-failover --yes

# Activate observer
flyctl scale count app=1 --app neolight-observer --yes

# Activate guardian
flyctl scale count app=1 --app neolight-guardian --yes

# Activate ai-money-web
flyctl scale count app=1 --app ai-money-web --yes
```

To scale back down:
```bash
flyctl scale count app=0 --app <app-name> --yes
```

---

## 💡 Benefits

1. **Cost Efficient**: ~$0.50/month in standby vs ~$9/month running
2. **Automatic**: Monitor handles activation/deactivation
3. **Reliable**: All apps ready as backup
4. **Flexible**: Can manually activate any app if needed

---

## 📊 Cost Breakdown

**Standby Mode (Current):**
- Storage: ~$0.50/month per app
- Running: $0/month
- **Total: ~$2/month** (4 apps × $0.50)

**Active Mode (When Failover):**
- neolight-failover: ~$1.50/month (1 machine)
- **Total during failover: ~$1.50/month**

**Savings**: ~$7/month when not in failover mode! 🎉

---

## 🔍 Monitor Logs

Check monitor status:
```bash
tail -f logs/flyio_failover_*.log
```

Monitor will:
- ✅ Check local health every 60s
- ✅ Activate failover after 3 failures
- ✅ Deactivate when local recovers
- ✅ Send Telegram alerts

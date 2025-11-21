# ✅ Summary: Cost Reduction & URL Fix

## 💰 Cost Reduction Analysis

**Current Running Machines (Costing Money):**
- `neolight-observer`: 1 machine (256MB) → ~$1.50/month
- `neolight-guardian`: 1 machine (256MB) → ~$1.50/month
- `ai-money-web`: 2 machines (1024MB each) → ~$6/month ⚠️ **MAIN COST**
- `neolight-failover`: 0 machines (standby) ✅ **Correct!**

**Total Current Cost**: ~$9/month (matches your $7.73 invoice)

---

## 🎯 Recommended Actions

### Quick Wins (Save ~$3/month):
```bash
# Scale down observer (monitoring - can run locally)
flyctl scale count app=0 --app neolight-observer --yes

# Scale down guardian (can run locally)
flyctl scale count app=0 --app neolight-guardian --yes
```

### Big Savings (Save ~$6/month):
```bash
# Scale down ai-money-web to 0 (if not actively using)
flyctl scale count app=0 --app ai-money-web --yes

# OR reduce to 1 machine (save ~$3/month)
flyctl scale count app=1 --app ai-money-web --yes
```

### Maximum Savings:
Scale all apps to 0 except failover (which is already at 0):
- **Potential savings**: ~$9/month (down to ~$0.50/month for storage)

---

## 🔧 URL Fix

**Issue**: `https://neolight-failover.fly.dev/` doesn't work
**Reason**: App is scaled to 0 (standby mode) - **This is correct!**

**Fixed**:
- ✅ Updated Dockerfile health endpoint to listen on `0.0.0.0:8080`
- ✅ Health endpoint responds to both `/health` and `/`
- ✅ URL will work when monitor scales up (during failover)

**To test URL now** (temporary):
```bash
flyctl scale count app=1 --app neolight-failover --yes
curl https://neolight-failover.fly.dev/health
flyctl scale count app=0 --app neolight-failover --yes
```

---

## 🚀 Ready to Execute?

I've created `REDUCE_COSTS.sh` script that will:
1. Ask which apps to scale down
2. Execute the scaling commands
3. Show estimated savings

**Run it with:**
```bash
bash REDUCE_COSTS.sh
```

**Or scale manually:**
```bash
# Scale down observer
flyctl scale count app=0 --app neolight-observer --yes

# Scale down guardian
flyctl scale count app=0 --app neolight-guardian --yes

# Scale down ai-money-web (choose one)
flyctl scale count app=0 --app ai-money-web --yes  # Complete shutdown
# OR
flyctl scale count app=1 --app ai-money-web --yes  # Keep 1 machine
```

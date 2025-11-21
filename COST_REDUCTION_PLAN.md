# 💰 Fly.io Cost Reduction Plan

## Current Running Machines (Costing Money)

1. **neolight-observer**: 1 machine (256MB) - ~$1.50/month
2. **neolight-guardian**: 1 machine (256MB) - ~$1.50/month  
3. **ai-money-web**: 2 machines (1024MB each) - ~$6/month ⚠️ **MAIN COST**
4. **neolight-failover**: 0 machines (standby) ✅

**Total estimated cost**: ~$9/month (matches your $7.73 invoice)

---

## 🎯 Recommended Actions

### Option 1: Scale Down Non-Critical Apps (Recommended)
Scale these to 0 if not actively needed:
- `neolight-observer` - monitoring (can run locally)
- `neolight-guardian` - guardian (can run locally)

This saves ~$3/month.

### Option 2: Reduce ai-money-web Machines
`ai-money-web` has 2 machines. If it's not critical:
- Scale to 1 machine (saves ~$3/month)
- Or scale to 0 if not needed (saves ~$6/month)

### Option 3: Suspend All Except Failover
If you're using local system primarily:
- Keep only `neolight-failover` in standby (0 machines)
- Suspend all others

**Potential savings**: ~$9/month (down to ~$0.50/month for storage)

---

## 📊 What Each App Does

- **neolight-observer**: Monitoring/observability
- **neolight-guardian**: Guardian agent (auto-healing)
- **ai-money-web**: Web interface/dashboard
- **neolight-failover**: Failover backup (standby, only activates when local fails)

---

## 🚀 Quick Commands

```bash
# Scale down observer (if not needed)
flyctl scale count app=0 --app neolight-observer --yes

# Scale down guardian (if not needed)  
flyctl scale count app=0 --app neolight-guardian --yes

# Reduce ai-money-web to 1 machine
flyctl scale count app=1 --app ai-money-web --yes

# Or suspend completely (if not needed)
flyctl apps suspend ai-money-web --yes
```

---

## ⚠️ Important Notes

- **neolight-failover** should stay scaled to 0 (standby mode) - this is correct!
- Apps can be reactivated anytime with `flyctl apps resume <app>`
- Scaling to 0 = no cost (just storage ~$0.50/month)
- Started machines = cost (based on size and runtime)

# 🚀 Manual Failover Guide

## Quick Commands

### Activate All Apps (When Local Fails)
```bash
bash MANUAL_FAILOVER.sh
```

This will:
- Activate all 7 apps on Fly.io
- Scale each to 1 machine
- Show status and URLs

### Deactivate All Apps (When Local Recovers)
```bash
bash MANUAL_DEACTIVATE.sh
```

This will:
- Deactivate all 7 apps
- Scale all to 0 (standby mode)
- Save costs

---

## Apps Included

1. **neolight-failover** - Main trading system
2. **neolight-observer** - Monitoring
3. **neolight-guardian** - Auto-healing
4. **ai-money-web** - Dashboard
5. **neolight-atlas** - Atlas intelligence
6. **neolight-trade** - Trading execution
7. **neolight-risk** - Risk management

---

## Quick Status Check

```bash
bash QUICK_STATUS.sh
```

Shows:
- Monitor status
- Latest logs
- Fly.io app status
- Local and internet connectivity

---

## Manual Commands (One-Liners)

**Activate all:**
```bash
for app in neolight-failover neolight-observer neolight-guardian ai-money-web neolight-atlas neolight-trade neolight-risk; do flyctl scale count app=1 --app "$app" --yes; done
```

**Deactivate all:**
```bash
for app in neolight-failover neolight-observer neolight-guardian ai-money-web neolight-atlas neolight-trade neolight-risk; do flyctl scale count app=0 --app "$app" --yes; done
```

**Check status:**
```bash
for app in neolight-failover neolight-observer neolight-guardian ai-money-web neolight-atlas neolight-trade neolight-risk; do echo "$app:"; flyctl machines list --app "$app" | grep -c "started" || echo "0"; done
```

---

## Cost

- **Standby (0 machines)**: ~$2/month (storage)
- **Active (7 apps × 1 machine)**: ~$10.50/month
- **Only pay when active!**

---

## When to Use

**Activate when:**
- Local system is down
- Internet is down on local machine
- Need to continue trading on Fly.io

**Deactivate when:**
- Local system is back up
- Want to save costs
- Switching back to local

---

**Simple and reliable!** 🎯

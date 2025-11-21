# 🚀 Fly.io Failover System - Enterprise Setup

## 🎯 Overview

Fly.io serves as a **failover system** that activates **only when local is down**, following the same pattern as Google Drive sync (rclone/neo_remote).

**Key Principle:** Local is primary, Fly.io is backup (same as Google Drive)

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Local System   │  ← Primary (always preferred)
│  (Mac/Server)   │
└────────┬────────┘
         │
         │ Health Check
         │ (every 60s)
         │
         ▼
    [Healthy?]
         │
    ┌────┴────┐
    │         │
  YES        NO (3 failures)
    │         │
    │         ▼
    │    ┌─────────────────┐
    │    │  Sync State to   │
    │    │  Google Drive    │
    │    └────────┬─────────┘
    │             │
    │             ▼
    │    ┌─────────────────┐
    │    │ Activate Fly.io  │
    │    │ (Scale to 1)     │
    │    └─────────────────┘
    │
    ▼
[Continue Local]
```

---

## 📋 Setup Instructions

### 1. Install Fly.io CLI
```bash
curl -L https://fly.io/install.sh | sh
export PATH="$HOME/.fly/bin:$PATH"
```

### 2. Authenticate
```bash
flyctl auth login
```

### 3. Deploy (Standby Mode)
```bash
cd ~/neolight
./scripts/flyio_deploy.sh
```

This deploys the app but keeps it **scaled to 0** (standby).

### 4. Configure Environment Variables
```bash
export FLY_API_TOKEN="your_fly_api_token"
export FLY_APP="neolight-failover"
export FLY_HEALTH_URL="https://neolight-failover.fly.dev/health"
export LOCAL_HEALTH_URL="http://localhost:8100/status"
```

### 5. Start Failover Monitor
```bash
./scripts/flyio_failover_monitor.sh
```

---

## 🔧 Configuration

### Environment Variables (Same Pattern as Google Drive)

```bash
# Fly.io Configuration
export FLY_APP="neolight-failover"
export FLY_API_TOKEN="your_token"
export FLY_HEALTH_URL="https://neolight-failover.fly.dev/health"

# Local Health Check
export LOCAL_HEALTH_URL="http://localhost:8100/status"

# Monitoring
export CHECK_INTERVAL="60"        # Check every 60 seconds
export FAILURE_THRESHOLD="3"      # 3 failures = failover

# Google Drive Sync (existing)
export RCLONE_REMOTE="neo_remote"
export RCLONE_PATH="NeoLight"

# Telegram (optional)
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

---

## 📊 How It Works

### Normal Operation (Local Healthy)
1. Monitor checks local health every 60s
2. Local system is healthy → Fly.io stays scaled to 0
3. State syncs to Google Drive (existing pattern)
4. No Fly.io costs incurred

### Failover Scenario (Local Down)
1. Monitor detects 3 consecutive failures
2. Syncs state to Google Drive (same as rclone)
3. Activates Fly.io (scales to 1)
4. Fly.io pulls state from Google Drive
5. Trading continues on Fly.io
6. Telegram notification sent

### Recovery (Local Recovers)
1. Monitor detects local is healthy
2. Deactivates Fly.io (scales to 0)
3. Local system resumes
4. Telegram notification sent

---

## 🔍 Monitoring

### Check Status
```bash
# Local status
cat run/flyio_failover.status

# Fly.io status
flyctl status --app neolight-failover

# View logs
tail -f logs/flyio_failover_*.log
```

### Manual Control
```bash
# Force activate Fly.io (for testing)
flyctl apps scale count app=1 --app neolight-failover

# Force deactivate
flyctl apps scale count app=0 --app neolight-failover
```

---

## 💰 Cost Optimization

**Smart Scaling:**
- Fly.io scales to **0** when local is healthy (no cost)
- Only scales to **1** when local fails (minimal cost)
- Auto-stops after 1 hour of inactivity (configurable)

**Estimated Cost:**
- Standby: **$0** (scaled to 0)
- Active: **~$0.0000019/second** (~$0.16/day if running 24/7)
- Only pays when local is down

---

## ✅ Benefits

1. **Zero Cost When Healthy** - Fly.io stays at 0 machines
2. **Automatic Failover** - No manual intervention needed
3. **State Synchronization** - Uses existing Google Drive pattern
4. **Same Format** - Follows rclone/neo_remote structure
5. **Enterprise-Grade** - Monitoring, logging, notifications

---

## 🎯 Comparison with Google Drive

| Feature | Google Drive | Fly.io |
|---------|--------------|--------|
| **Purpose** | Backup/Sync | Failover |
| **Pattern** | rclone sync | Auto-scale |
| **Activation** | Manual/Periodic | Automatic (on local failure) |
| **Cost** | Free (storage) | Pay per use (only when active) |
| **State Sync** | ✅ Yes | ✅ Yes (via Google Drive) |

---

## 🚀 Quick Start

```bash
# 1. Deploy (one-time)
./scripts/flyio_deploy.sh

# 2. Start monitor (runs continuously)
./scripts/flyio_failover_monitor.sh

# 3. Monitor status
tail -f logs/flyio_failover_*.log
```

---

**Status: Enterprise-Ready Failover System** ✅



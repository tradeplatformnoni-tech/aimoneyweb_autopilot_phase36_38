# 🚀 Fly.io Failover - Quick Start

## ✅ Yes, Fly.io is Better for Failover!

**Why Fly.io over Google Cloud for failover:**
- ✅ **Zero cost when standby** (scales to 0)
- ✅ **Automatic failover** (no manual intervention)
- ✅ **Same format** as Google Drive sync
- ✅ **Only activates when local is down** (perfect!)

---

## 🎯 Setup (3 Steps)

### 1. Install Fly.io CLI
```bash
curl -L https://fly.io/install.sh | sh
export PATH="$HOME/.fly/bin:$PATH"
flyctl auth login
```

### 2. Deploy (Standby Mode)
```bash
cd ~/neolight
./scripts/flyio_deploy.sh
```
**Result:** App deployed but scaled to **0** (no cost)

### 3. Start Monitor
```bash
./scripts/flyio_failover_monitor.sh
```
**Result:** Monitors local health, activates Fly.io only when local fails

---

## 📊 How It Works

```
Local System (Healthy) → Fly.io stays at 0 machines ($0 cost)
Local System (Down)    → Fly.io scales to 1 machine (trading continues)
Local System (Recover) → Fly.io scales back to 0 (no cost)
```

---

## 🔧 Configuration

Same pattern as Google Drive:
```bash
export FLY_API_TOKEN="your_token"
export FLY_APP="neolight-failover"
export RCLONE_REMOTE="neo_remote"  # Same as Google Drive
export RCLONE_PATH="NeoLight"      # Same as Google Drive
```

---

## 💰 Cost

- **Standby**: $0 (scaled to 0)
- **Active**: ~$0.16/day (only when local is down)
- **Total**: Only pay when you need it!

---

## ✅ Status

All files created:
- ✅ `fly.toml` - Fly.io configuration
- ✅ `Dockerfile` - Container image
- ✅ `scripts/flyio_deploy.sh` - Deployment script
- ✅ `scripts/flyio_failover_monitor.sh` - Monitor script
- ✅ `FLYIO_FAILOVER_SETUP.md` - Full documentation

**Ready to deploy!** 🚀



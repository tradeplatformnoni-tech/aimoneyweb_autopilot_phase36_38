# 🚀 Deploy Commands - Run These in Your Terminal

## Option 1: Local Build (Recommended - Faster)

Run this command in your terminal:

```bash
cd ~/neolight
flyctl deploy --app neolight-cloud --config fly.toml --local-only
```

This builds the Docker image locally and then deploys it.

---

## Option 2: Wait and Retry Remote Build

Sometimes the remote builder needs a moment. Wait 30 seconds, then try:

```bash
cd ~/neolight
flyctl deploy --app neolight-cloud --config fly.toml
```

---

## Option 3: Build Docker Image First, Then Deploy

If the above don't work:

```bash
cd ~/neolight

# Build Docker image locally
docker build -t neolight-cloud:latest -f Dockerfile .

# Deploy with the built image
flyctl deploy --app neolight-cloud --config fly.toml --image neolight-cloud:latest
```

---

## After Successful Deployment

### 1. Set Secrets

```bash
# From .env file (if you have one)
flyctl secrets import --app neolight-cloud < .env

# Or use interactive script
bash scripts/flyio_set_secrets.sh
```

### 2. Check Status

```bash
flyctl status --app neolight-cloud
```

### 3. View Logs

```bash
flyctl logs --app neolight-cloud --follow
```

### 4. Sync State

```bash
bash scripts/flyio_sync_state.sh to
```

---

## Quick Fix for Remote Builder Error

The error you're seeing is because the remote builder isn't available. **Use Option 1 (local build)** - it's actually faster and more reliable!

**Just run:**
```bash
flyctl deploy --app neolight-cloud --config fly.toml --local-only
```

This will build locally and deploy. It should work!



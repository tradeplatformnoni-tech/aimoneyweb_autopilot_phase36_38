# 🎯 Original Plan Reminder - Free Tier Strategy

## ✅ Original Plan: Scale-to-Zero (Failover Mode)

**Goal:** Stay within Google Cloud free tier  
**Strategy:** Cloud Run scales to ZERO when idle, only activates on failover

---

## 📊 Google Cloud Run Free Tier Limits

**Free Tier Includes:**
- ✅ 2 million requests per month
- ✅ 360,000 GB-seconds of memory
- ✅ 180,000 vCPU-seconds
- ✅ **BUT:** Only if `min-instances=0` (scale to zero)

**If `min-instances=1` (always-on):**
- ❌ You pay for the always-on instance
- ❌ Cost: ~$7-10/month
- ❌ NOT free tier

---

## 🎯 Original Failover Strategy

### How It Should Work:

1. **Normal Operation (Local System Running):**
   - Cloud Run: `min-instances=0` (scaled to zero)
   - Cost: **$0/month** ✅
   - Local system handles everything

2. **Failover (Local System Fails):**
   - Monitor detects failure
   - Cloud Run scales up automatically
   - Cost: Only during failover (minimal)
   - Local recovers → Cloud Run scales back to zero

3. **Result:**
   - ✅ Stays within free tier (most of the time)
   - ✅ Only costs when actually needed
   - ✅ Automatic failover

---

## ❌ Current Problem

**Current Configuration:**
- `--min-instances=1` ❌ **WRONG!**
- This means: Always on = ~$7-10/month
- This is NOT free tier!

**Should Be:**
- `--min-instances=0` ✅ **CORRECT!**
- This means: Scale to zero = $0/month (free tier)
- Only scales up when needed

---

## ✅ Fix Required

**Change in `cloud-run/cloudbuild.yaml`:**
```yaml
# WRONG (current):
- '--min-instances=1'

# CORRECT (should be):
- '--min-instances=0'
```

**This will:**
- ✅ Scale to zero when idle (free tier)
- ✅ Only scale up on failover
- ✅ Stay within free tier limits
- ✅ Cost: $0/month (when idle)

---

## 🔄 How Failover Works with Scale-to-Zero

1. **Local system running:**
   - Cloud Run: Scaled to 0 (free)
   - Monitor: Watching local system

2. **Local system fails:**
   - Monitor detects failure (3 checks = 3 minutes)
   - Cloud Run scales up automatically
   - Service becomes available
   - Cost: Only during failover

3. **Local system recovers:**
   - Monitor detects recovery
   - Cloud Run scales back to 0
   - Cost: Back to $0

**Cold Start Time:** 10-30 seconds (acceptable for failover)

---

## 💰 Cost Comparison

### Current (Wrong - Always On):
- `min-instances=1` = ~$7-10/month ❌

### Correct (Free Tier):
- `min-instances=0` = $0/month (when idle) ✅
- Only costs during actual failover
- Stays within free tier limits

---

## 🚀 Next Steps

1. **Fix cloudbuild.yaml** - Change `min-instances=1` to `min-instances=0`
2. **Redeploy** - Update the service
3. **Verify** - Service scales to zero when idle
4. **Test failover** - Ensure it scales up when needed

---

**🎯 This is the original plan - scale-to-zero to stay within free tier!**




# 💾 NeoLight Disk Space Optimization Guide
## Free Up Laptop Space While Keeping System Operational

**Date:** 2025-11-20  
**Current Usage:** 5.1GB total

---

## 📊 CURRENT DISK USAGE BREAKDOWN

### **Total: 5.1GB**
- **logs/**: 1.1GB (22% - largest)
- **state/**: 28MB (0.5%)
- **runtime/**: 812KB (0.02%)
- **Code & Dependencies**: ~3.9GB (78%)

---

## ✅ WHAT'S RUNNING ON RENDER (24/7)

### **Currently Deployed:**
1. ✅ **Intelligence Orchestrator** - Running
2. ✅ **ML Pipeline** - Running
3. ✅ **Strategy Research** - Running
4. ✅ **Market Intelligence** - Running
5. ✅ **SmartTrader** - Running

### **NOT on Render (but available):**
- ⚠️ **Sports Betting Agent** - Exists but NOT deployed to Render
- ⚠️ **Dropshipping Agent** - Exists but NOT deployed to Render
- ⚠️ **Other Revenue Agents** - Not deployed

**Note:** Render deployment is independent of local files. Code must remain local for development, but agents run in the cloud.

---

## 💡 KEY INSIGHT: Render Doesn't Free Up Local Space

### **What Render Does:**
- ✅ Runs agents 24/7 in the cloud
- ✅ Processes run on Render's servers
- ✅ No local CPU/memory usage for deployed agents

### **What Render Doesn't Do:**
- ❌ Doesn't remove local code (you need it for development)
- ❌ Doesn't sync logs/state automatically
- ❌ Doesn't free up disk space

**Bottom Line:** Render runs agents in the cloud, but you still need local code for development and updates.

---

## 🎯 RECOMMENDED DISK SPACE OPTIMIZATION

### **Option 1: Archive Old Logs (RECOMMENDED)**
**Impact:** Free up ~800MB-1GB immediately

**What to Archive:**
- Logs older than 30 days
- Large log files (>100MB)
- Old state snapshots

**How:**
```bash
# Archive old logs to external drive
mkdir -p /Volumes/[YOUR_DRIVE]/neolight_archive/logs
find ~/neolight/logs -name "*.log" -mtime +30 -exec mv {} /Volumes/[YOUR_DRIVE]/neolight_archive/logs/ \;

# Or compress old logs
find ~/neolight/logs -name "*.log" -mtime +30 -exec gzip {} \;
```

**Keep Locally:**
- Last 7 days of logs (for debugging)
- Active agent logs (smart_trader.log, etc.)

---

### **Option 2: Move State/Runtime to External Drive (OPTIONAL)**
**Impact:** Free up ~30MB (minimal)

**What to Move:**
- Old state snapshots
- Archived runtime data
- Historical backups

**Keep Locally:**
- Current state/ (needed for agents)
- Current runtime/ (needed for agents)

**Note:** Only move if you have >100GB of state data. Current 28MB is negligible.

---

### **Option 3: Clean Python Cache (QUICK WIN)**
**Impact:** Free up ~100-500MB

```bash
# Find and remove Python cache
find ~/neolight -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find ~/neolight -name "*.pyc" -delete 2>/dev/null
```

---

### **Option 4: Move Code to External Drive (NOT RECOMMENDED)**
**Why Not:**
- ❌ Slower development (external drives are slower)
- ❌ Git operations will be slower
- ❌ IDE performance will suffer
- ❌ Risk of disconnection during work

**Only Consider If:**
- You have very limited space (<10GB free)
- You rarely edit code
- External drive is SSD and always connected

---

## 📋 RECOMMENDED ACTION PLAN

### **Step 1: Archive Old Logs (Do This First)**
```bash
cd ~/neolight

# Create archive directory on external drive
EXTERNAL_DRIVE="/Volumes/[YOUR_DRIVE_NAME]"
mkdir -p "$EXTERNAL_DRIVE/neolight_archive/logs"

# Archive logs older than 30 days
find logs -name "*.log" -mtime +30 -exec mv {} "$EXTERNAL_DRIVE/neolight_archive/logs/" \;

# Compress remaining old logs
find logs -name "*.log" -mtime +7 -mtime -30 -exec gzip {} \;
```

**Expected Result:** Free up ~800MB-1GB

---

### **Step 2: Clean Python Cache**
```bash
cd ~/neolight
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
```

**Expected Result:** Free up ~100-500MB

---

### **Step 3: Set Up Log Rotation (Prevent Future Growth)**
```bash
# Add to crontab or create cleanup script
# Keep only last 7 days of logs, compress older ones
```

---

## 🚀 ADD SPORTS BETTING TO RENDER (Optional)

If you want sports betting agent on Render 24/7:

**Add to `render_app_multi_agent.py`:**
```python
"sports_betting": {
    "script": ROOT / "agents" / "sports_betting_agent.py",
    "priority": 6,
    "required": False,
    "description": "Sports Betting Agent (paper trading)",
}
```

**Note:** Requires `NEOLIGHT_ENABLE_REVENUE_AGENTS=true` and Sportradar API key.

---

## ✅ FINAL RECOMMENDATIONS

### **DO THIS NOW:**
1. ✅ **Archive old logs** → Free up ~1GB immediately
2. ✅ **Clean Python cache** → Free up ~200MB
3. ✅ **Set up log rotation** → Prevent future growth

### **DON'T DO THIS:**
- ❌ Move code to external drive (too slow)
- ❌ Delete current state/ (needed for agents)
- ❌ Move active logs (needed for debugging)

### **RESULT:**
- **Before:** 5.1GB
- **After:** ~3.8GB (freed ~1.3GB)
- **Space Saved:** ~25%

---

## 📊 WHAT STAYS LOCAL vs CAN BE MOVED

### **MUST STAY LOCAL:**
- ✅ Code (agents/, trader/, phases/, etc.) - Needed for development
- ✅ Current state/ - Needed for agents
- ✅ Current runtime/ - Needed for agents
- ✅ Last 7 days of logs - Needed for debugging
- ✅ .git/ - Needed for version control
- ✅ Configuration files - Needed for setup

### **CAN BE MOVED TO EXTERNAL:**
- ✅ Logs older than 30 days
- ✅ Old state snapshots
- ✅ Archived backups
- ✅ Old model files (if any)

### **CAN BE DELETED:**
- ✅ Python cache (__pycache__)
- ✅ .pyc files
- ✅ Temporary files
- ✅ Old backups

---

## 🎯 SUMMARY

**Current Situation:**
- ✅ Agents running on Render 24/7 (trading agents)
- ⚠️ Sports betting agent NOT on Render (but can be added)
- 📊 Local disk: 5.1GB (logs are 1.1GB)

**Recommendation:**
1. **Archive old logs** → Free up ~1GB (biggest win)
2. **Clean Python cache** → Free up ~200MB
3. **Keep code local** → Needed for development
4. **Add sports betting to Render** → Optional, if you want it 24/7

**Result:** Free up ~1.3GB while keeping system fully operational.

---

**Last Updated:** 2025-11-20


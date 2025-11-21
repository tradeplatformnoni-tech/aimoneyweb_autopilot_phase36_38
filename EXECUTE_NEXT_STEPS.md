# Execute Next Steps - Manual Instructions

Due to shell environment issues preventing automated execution, please run these commands manually in your terminal.

## ✅ Changes Already Made

1. **Phase 301-340 (Equity Replay) added to `neo_light_fix.sh`** ✅
   - Location: Lines 236-241
   - Will start automatically when guardian runs

2. **Direct startup script created: `enable_missing_phases.sh`** ✅
   - Can start missing phases without guardian restart

3. **Verification script enhanced: `check_and_enable_phases.py`** ✅
   - Updated to include Phase 301-340

## 🚀 Manual Execution Steps

### Step 1: Check Current Phase Status

Open a new terminal and run:
```bash
cd ~/neolight
python3 check_and_enable_phases.py
```

This will show which phases are currently running and which need to be started.

### Step 2: Start Missing Phases (if any)

If any phases are not running, start them with:
```bash
cd ~/neolight
bash enable_missing_phases.sh all
```

Or start individual phases:
```bash
bash enable_missing_phases.sh equity_replay
bash enable_missing_phases.sh portfolio_optimization
# etc.
```

### Step 3: Restart Guardian to Pick Up Phase 301-340

To ensure Phase 301-340 starts automatically with the guardian:

```bash
cd ~/neolight

# Stop guardian if running
pkill -f neo_light_fix.sh

# Wait a moment
sleep 2

# Start guardian (will start all enabled phases including Phase 301-340)
nohup bash neo_light_fix.sh > logs/guardian_restart_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Check that it started
sleep 5
ps aux | grep neo_light_fix.sh | grep -v grep
```

### Step 4: Verify All Phases Are Running

After restarting the guardian, verify all phases:
```bash
cd ~/neolight
python3 check_and_enable_phases.py
```

### Step 5: Check Guardian Logs

Monitor the guardian startup:
```bash
cd ~/neolight
tail -f logs/guardian_restart_*.log
# or
tail -f logs/guardian_startup.log
```

Look for:
- "Launching equity replay (Phase 301-340)..."
- "Equity replay active (historical data, backtesting, yfinance)"

## 📋 Expected Results

After completing these steps, you should see:

1. **All 17 phases configured** in `neo_light_fix.sh`
2. **Phase 301-340 starting** when guardian runs
3. **All phases running** (check with `check_and_enable_phases.py`)

## 🔍 Troubleshooting

### If Phase 301-340 doesn't start:

1. Check if the env var is set to false:
   ```bash
   echo $NEOLIGHT_ENABLE_EQUITY_REPLAY
   ```
   Should be empty or "true" (empty = default true)

2. Check the guardian log for errors:
   ```bash
   tail -50 logs/guardian_startup.log | grep -i equity
   ```

3. Start it manually:
   ```bash
   bash enable_missing_phases.sh equity_replay
   ```

### If phases fail to start:

1. Check Python environment:
   ```bash
   cd ~/neolight
   source venv/bin/activate
   python3 --version
   ```

2. Check if scripts exist:
   ```bash
   ls -la phases/phase_301_340_equity_replay.py
   ```

3. Check logs:
   ```bash
   tail -50 logs/equity_replay.log
   ```

## ✅ Verification Checklist

- [ ] Phase 301-340 added to `neo_light_fix.sh` (lines 236-241)
- [ ] `enable_missing_phases.sh` is executable
- [ ] `check_and_enable_phases.py` runs without errors
- [ ] Guardian restarts successfully
- [ ] Phase 301-340 starts when guardian runs
- [ ] All 17 phases show as running in status check

## 📝 Notes

- All phases default to **enabled** (`true`) unless explicitly disabled
- Guardian will auto-start all enabled phases on startup
- Use `enable_missing_phases.sh` to start phases without guardian restart
- Check `logs/` directory for each phase's status and errors


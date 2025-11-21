# Phase 301-340 Fix Summary

## Issue Identified

**Problem**: Phase 301-340 was failing because:
1. The script was designed to run **once and exit** (batch job), not as a continuous service
2. The guardian's `ensure_running` function expects processes that run continuously
3. When the script completed and exited, the guardian kept trying to restart it

**External Drive**: ✅ **NOT the issue**
- Script uses `~/neolight/data` (local drive)
- Has self-healing: downloads from yfinance or generates synthetic data if local data is missing
- No dependency on external drives

## Solution Applied

### 1. Modified Script to Run Continuously
- Refactored `main()` to run in a `while True` loop
- Created `run_replay_cycle()` function for single replay execution
- Added `--interval` parameter (default: 86400 seconds = 24 hours)
- Runs replay cycle, then sleeps for the interval, then repeats

### 2. Updated Guardian Startup
- Modified `neo_light_fix.sh` to pass `--interval` parameter
- Added `NEOLIGHT_EQUITY_REPLAY_INTERVAL` environment variable support
- Default interval: 24 hours (86400 seconds)

## Changes Made

### File: `phases/phase_301_340_equity_replay.py`
- Added `run_replay_cycle(args)` function (extracted replay logic)
- Modified `main()` to run in continuous loop
- Added `--interval` CLI argument
- Added error handling with retry logic

### File: `neo_light_fix.sh`
- Updated Phase 301-340 section to pass `--interval` parameter
- Added `EQUITY_REPLAY_INTERVAL` environment variable support

## How It Works Now

1. Script starts and runs in continuous mode
2. Executes replay cycle (loads data, processes, saves results)
3. Sleeps for configured interval (default: 24 hours)
4. Repeats indefinitely
5. Guardian monitors and restarts if it crashes

## Configuration

### Environment Variables
- `NEOLIGHT_ENABLE_EQUITY_REPLAY` - Enable/disable phase (default: `true`)
- `NEOLIGHT_EQUITY_REPLAY_INTERVAL` - Interval in seconds (default: `86400` = 24 hours)

### Example: Run every 6 hours
```bash
export NEOLIGHT_EQUITY_REPLAY_INTERVAL=21600  # 6 hours
bash neo_light_fix.sh
```

## Testing

To test the fix:
1. Start the phase: `bash enable_missing_phases.sh equity_replay`
2. Check it's running: `pgrep -f phase_301_340_equity_replay`
3. Check logs: `tail -f logs/equity_replay.log`
4. Should see: "starting continuous mode" and "Next run in X hours"

## Status

✅ **Fixed** - Phase 301-340 now runs continuously like other phases
✅ **No external drive dependency** - Uses local storage with self-healing


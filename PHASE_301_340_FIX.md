# Phase 301-340 Equity Replay Fix

## Issue Identified

**Problem**: Phase 301-340 equity replay script is designed to run **once and exit**, not as a continuous service. The guardian's `ensure_running` function expects processes that run continuously, so it keeps trying to restart a script that completes successfully and exits.

**Root Cause**: The script processes data, runs replay, saves results, and exits. It's not a daemon/service like other phases.

**External Drive**: ✅ NOT the issue - script uses `~/neolight/data` (local drive)

## Solution Options

### Option 1: Modify Script to Run in Loop (Recommended)
Add a continuous loop with configurable interval (e.g., run every 24 hours).

### Option 2: Run as Scheduled Job
Use cron or scheduler to run periodically instead of as a continuous service.

### Option 3: Change Guardian Integration
Modify how guardian handles this phase (run-once vs continuous).

## Recommended Fix

Modify `phase_301_340_equity_replay.py` to run in a loop with a configurable interval, similar to other phases.


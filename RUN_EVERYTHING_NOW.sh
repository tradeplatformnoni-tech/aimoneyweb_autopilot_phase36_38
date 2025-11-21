#!/bin/bash
# Script to run all the next steps for enabling phases

cd ~/neolight || exit 1

echo "======================================================================"
echo "🚀 Running All Phase Enablement Steps"
echo "======================================================================"
echo ""

# Step 1: Check current status
echo "Step 1: Checking current phase status..."
python3 check_and_enable_phases.py
echo ""

# Step 2: Start missing phases
echo "Step 2: Starting missing phases..."
bash enable_missing_phases.sh all
echo ""

# Step 3: Restart guardian
echo "Step 3: Restarting guardian to pick up Phase 301-340..."
pkill -f neo_light_fix.sh
sleep 2
nohup bash neo_light_fix.sh > logs/guardian_restart_$(date +%Y%m%d_%H%M%S).log 2>&1 &
echo "Guardian started in background (PID: $!)"
echo ""

# Step 4: Wait and verify
echo "Step 4: Waiting 10 seconds for phases to start..."
sleep 10
echo ""

echo "Step 5: Verifying all phases are running..."
python3 check_and_enable_phases.py
echo ""

echo "======================================================================"
echo "✅ All steps completed!"
echo "======================================================================"
echo ""
echo "Check guardian logs: tail -f logs/guardian_restart_*.log"
echo "Check Phase 301-340: tail -f logs/equity_replay.log"


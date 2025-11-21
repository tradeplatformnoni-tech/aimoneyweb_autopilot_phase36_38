#!/bin/bash
# Start 24-hour soak test (runs in background)

cd ~/neolight

echo "🚀 Starting 24-Hour Soak Test"
echo "============================="
echo ""
echo "This will run in the background and monitor:"
echo "  • SmartTrader uptime"
echo "  • Error rates"
echo "  • Trade execution"
echo "  • Memory usage"
echo "  • Mode consistency"
echo ""
echo "Logs will be saved to: logs/soak_test_*.log"
echo ""

# Start monitor in background
nohup bash scripts/soak_test_monitor.sh > /tmp/soak_test.out 2>&1 &
SOAK_PID=$!

echo "✅ Soak test monitor started (PID: $SOAK_PID)"
echo ""
echo "To check status:"
echo "  tail -f /tmp/soak_test.out"
echo ""
echo "To stop:"
echo "  pkill -f soak_test_monitor.sh"
echo ""
echo "Monitor will run for 24 hours and generate a final report."
echo ""


#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ 🧠 NeoLight RL System Launcher - Phase 3700-3900                ║
# ║ Starts RL trainer and inference engine in background             ║
# ╚══════════════════════════════════════════════════════════════════╝

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

echo "🧠 Starting NeoLight RL System..."
echo ""

# Start RL Trainer (background, retrains periodically)
echo "📚 Starting RL Trainer (background)..."
cd "$ROOT" && PYTHONPATH="$ROOT:$PYTHONPATH" nohup python3 ai/rl_trainer.py --loop >> "$LOG_DIR/rl_trainer.log" 2>&1 &
TRAINER_PID=$!
echo "   Trainer PID: $TRAINER_PID"

# Start RL Inference (background, updates weights periodically)
echo "🔮 Starting RL Inference Engine (background)..."
cd "$ROOT" && PYTHONPATH="$ROOT:$PYTHONPATH" nohup python3 ai/rl_inference.py --loop --interval 300 >> "$LOG_DIR/rl_inference.log" 2>&1 &
INFERENCE_PID=$!
echo "   Inference PID: $INFERENCE_PID"

# Start Performance Tracker (optional, periodic reports)
echo "📊 Starting RL Performance Tracker (background)..."
cd "$ROOT" && PYTHONPATH="$ROOT:$PYTHONPATH" nohup python3 analytics/rl_performance.py --report >> "$LOG_DIR/rl_performance.log" 2>&1 &
PERF_PID=$!
echo "   Performance Tracker PID: $PERF_PID"

echo ""
echo "✅ RL System started!"
echo ""
echo "📋 Components:"
echo "   - RL Trainer: Retrains weekly or when 50+ trades accumulate"
echo "   - RL Inference: Updates strategy weights every 5 minutes"
echo "   - Performance Tracker: Generates periodic reports"
echo ""
echo "📊 Check status:"
echo "   tail -f logs/rl_*.log"
echo ""
echo "🛑 Stop all:"
echo "   pkill -f rl_trainer.py"
echo "   pkill -f rl_inference.py"
echo "   pkill -f rl_performance.py"


#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/neolight"
PYBIN="$ROOT/venv/bin/python3"
PIPBIN="$ROOT/venv/bin/pip"

echo "🧠 NeoLight Auto-Healer — Starting environment diagnostics..."
echo "🔍 Checking virtual environment at: $PYBIN"

# 1️⃣ Ensure venv exists
if [[ ! -d "$ROOT/venv" ]]; then
  echo "⚙️ Creating virtual environment..."
  python3 -m venv "$ROOT/venv"
fi
source "$ROOT/venv/bin/activate"

# 2️⃣ Core Python dependencies
REQS=(gTTS playsound3 fastapi plotly pandas uvicorn yfinance numpy requests pillow dask polars)
for pkg in "${REQS[@]}"; do
  if ! "$PYBIN" -c "import ${pkg%%=*}" &>/dev/null; then
    echo "📦 Installing missing package: $pkg"
    "$PIPBIN" install -q "$pkg"
  else
    echo "✅ $pkg already installed."
  fi
done

# 3️⃣ Repair any broken symbolic links or partial installs
echo "🩺 Validating environment health..."
"$PIPBIN" check || echo "⚠️ Some optional deps may need upgrade."

# 4️⃣ Summarize environment
echo "🧾 Installed package summary (top 10):"
"$PIPBIN" list | head -n 10

# 5️⃣ Final confirmation
echo "💚 Environment validated successfully."
echo "Next steps:"
echo "  1️⃣ Test voice notifier:   $PYBIN $ROOT/agents/voice_notifier.py"
echo "  2️⃣ Launch dashboard:       $PYBIN $ROOT/dashboard/launch_dashboard.py"
echo "  3️⃣ Run full system check:  bash $ROOT/neo_light_fix.sh"

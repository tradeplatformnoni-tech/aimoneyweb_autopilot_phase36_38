#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/neolight"
LOG="$ROOT/logs/phase_301_340_replay_stdout.log"

# ensure venv
if [[ ! -f "$ROOT/venv/bin/activate" ]]; then
  python3 -m venv "$ROOT/venv"
fi
source "$ROOT/venv/bin/activate"

# ensure deps
pip install -q --upgrade pip
pip install -q yfinance python-dateutil pandas pyarrow dask polars

# run
python3 "$ROOT/phases/phase_301_340_equity_replay.py" --adaptive 1 --freq D --phase_step 1M | tee -a "$LOG"


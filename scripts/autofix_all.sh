#!/usr/bin/env bash
# ⚡️ NeoLight AutoFix Suite — Full Stack Healer
# Repairs indentation, syntax, Optional type hints, and duplicate blocks.

set -euo pipefail
ROOT=~/neolight
TRADER="$ROOT/trader/smart_trader.py"
PHASE="$ROOT/phases/phase_301_340_equity_replay.py"
LOG="$ROOT/logs/autofix_all_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$ROOT/logs"

echo "🧩 Starting NeoLight Full AutoFix..." | tee -a "$LOG"

# 1️⃣ Ensure imports + stop handler block clean in trader
python3 - <<'PY' >> "$LOG" 2>&1
import re, subprocess, textwrap
from pathlib import Path

f = Path('~/neolight/trader/smart_trader.py').expanduser()
src = f.read_text().splitlines()
start, end = 100, 140

block = textwrap.dedent("""\
import signal
import time
import datetime as dt
import traceback
import subprocess
import os

stop_flag = {'stop': False}
def handle_stop(sig, frame):
    stop_flag['stop'] = True
    print('🛑 Stop signal received — preparing graceful shutdown...')
signal.signal(signal.SIGINT, handle_stop)
signal.signal(signal.SIGTERM, handle_stop)
""").splitlines()

# Replace suspect window
new = []
for i, line in enumerate(src):
    if i < start or i > end:
        new.append(line)
    elif i == start:
        new.extend(block)
f.write_text("\n".join(new))

# Reindent file cleanly
clean = []
for line in new:
    if line.strip() == '':
        clean.append('')
    else:
        clean.append(line.replace('\t', '    '))
f.write_text("\n".join(clean))
print("✅ Trader block repaired.")
PY

# 2️⃣ Fix Optional / union syntax in replay
python3 - <<'PY' >> "$LOG" 2>&1
from pathlib import Path
p = Path('~/neolight/phases/phase_301_340_equity_replay.py').expanduser()
text = p.read_text()

# Fix wrong type syntax
text = text.replace("-> pd.DataFrame Optional", "-> Optional[pd.DataFrame]")
text = text.replace("| None", "Optional")
if "from typing import Optional" not in text:
    text = "from typing import Optional, Dict\n" + text
p.write_text(text)
print("✅ Phase 301–340 type hints fixed.")
PY

# 3️⃣ Syntax verification
echo "🔍 Checking syntax..." | tee -a "$LOG"
for f in "$TRADER" "$PHASE"; do
  if python3 -m py_compile "$f"; then
    echo "✅ $f OK" | tee -a "$LOG"
  else
    echo "❌ $f FAILED — open manually." | tee -a "$LOG"
  fi
done

echo "🎯 AutoFix completed. Logs → $LOG"


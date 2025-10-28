#!/bin/bash
echo "🚀 Phase 3451–3500: Multi-Asset Feed Repair"

cat > ai/providers/data_feed.py <<'EOF'
import json, random
from ai.providers import alpaca_provider

def get_multi_asset_data():
    with open("config/symbols.json") as f:
        symbols = json.load(f)
    sym = random.choice(symbols)
    data = alpaca_provider.get_ohlc(sym, limit=60)
    return sym, data
EOF

echo "✅ Feed now dynamically rotates through all symbols."


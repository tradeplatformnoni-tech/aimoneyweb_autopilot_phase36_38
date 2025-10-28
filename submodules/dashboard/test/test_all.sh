#!/usr/bin/env bash
set -e
BASE=${1:-http://127.0.0.1:8000}
echo "→ Checking ${BASE}"
curl -s ${BASE}/api/alpaca_status | jq . || { echo "alpacastatus failed"; exit 1; }
curl -s ${BASE}/api/positions | jq . || { echo "positions failed"; exit 1; }
curl -s ${BASE}/api/stream_health | jq . || { echo "stream_health failed"; exit 1; }
echo "✅ All endpoints responded"

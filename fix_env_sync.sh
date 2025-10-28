#!/bin/bash
# --- AI Money Web :: Sync Correct Alpaca Keys ---
set -e
echo "🔁 Syncing ALPACA_API_KEY -> ALPACA_API_KEY_ID and SECRET..."

# ensure .env exists
if [ ! -f .env ]; then
  echo "⚠️  No .env file found!"
  exit 1
fi

# backup before modifying
cp .env .env.backup_$(date +"%Y%m%d_%H%M%S")

# extract values safely
key_val=$(grep "^ALPACA_API_KEY=" .env | cut -d'=' -f2-)
secret_val=$(grep "^ALPACA_SECRET_KEY=" .env | cut -d'=' -f2-)

# sync values into proper vars if found
if [ -n "$key_val" ]; then
  echo "🧩 Updating ALPACA_API_KEY_ID..."
  sed -i '' "s|^ALPACA_API_KEY_ID=.*|ALPACA_API_KEY_ID=$key_val|" .env
fi

if [ -n "$secret_val" ]; then
  echo "🧩 Updating ALPACA_API_SECRET..."
  sed -i '' "s|^ALPACA_API_SECRET=.*|ALPACA_API_SECRET=$secret_val|" .env
fi

# show result
echo "✅ Synced key values:"
grep "ALPACA_API" .env

# restart backend
echo "♻️  Restarting backend..."
pkill -f uvicorn || true
source venv/bin/activate
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

# verify environment
echo "🧩 Verifying environment..."
curl -s http://127.0.0.1:8000/api/env_check | jq .


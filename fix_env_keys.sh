# --- AI Money Web :: Auto Fix Missing Alpaca Keys ---
set -e
echo "🧠 Checking and fixing missing Alpaca keys..."

# ensure .env exists
if [ ! -f .env ]; then
  echo "⚠️  No .env found — creating one..."
  touch .env
fi

# add missing keys if needed
grep -q "ALPACA_API_KEY_ID" .env || echo "ALPACA_API_KEY_ID=YOUR_KEY_HERE" >> .env
grep -q "ALPACA_API_SECRET" .env || echo "ALPACA_API_SECRET=YOUR_SECRET_HERE" >> .env

# ensure proper formatting (no hidden characters)
sed -i '' 's/[[:space:]]*$//' .env

# display summary
echo "✅ Current .env keys:"
grep "ALPACA_" .env || true

# reload backend
echo "♻️  Restarting backend..."
pkill -f uvicorn || true
source venv/bin/activate
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

echo "🧩 Verifying environment..."
curl -s http://127.0.0.1:8000/api/env_check | jq .
	

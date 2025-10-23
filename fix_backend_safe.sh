# --- Safe backend restart helper ---
set -e
echo "🧹 Checking backend health ..."

# 1️⃣  make sure .env loader is installed
pip show python-dotenv >/dev/null 2>&1 || {
  echo "📦 Installing python-dotenv ..."
  pip install python-dotenv
}

# 2️⃣  clean any leftover uvicorns
for pid in $(sudo lsof -ti :8000 2>/dev/null); do
  echo "⚔️  Killing process on port 8000 (PID: $pid)"
  sudo kill -9 $pid 2>/dev/null || true
done

# 3️⃣  verify indentation / syntax quickly
python -m py_compile backend/main.py 2>/dev/null || {
  echo "⚠️  Syntax error in backend/main.py - please open it in nano to correct indentation."
  exit 1
}

# 4️⃣  restart backend
echo "🚀 Restarting FastAPI backend..."
source venv/bin/activate
nohup uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 > logs/backend.log 2>&1 &
sleep 3

# 5️⃣  verify startup
if curl -s http://127.0.0.1:8000/ | grep -q "AI Money Web"; then
  echo "✅ Backend is running on http://127.0.0.1:8000"
else
  echo "❌ Backend still not reachable; check logs/backend.log for details."
fi


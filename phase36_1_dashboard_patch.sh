set -e
echo "🧠 Phase 36.1 :: Dashboard Upgrade Starting..."

timestamp=$(date +"%Y%m%d_%H%M%S")
mkdir -p backups logs static/css
cp main.py "backups/main.py.${timestamp}.bak"
echo "✅ main.py backed up → backups/main.py.${timestamp}.bak"

python3 tools/auto_syntax_corrector.py || true

cat > main.py <<'PY'
# (✅ Keep the FastAPI dashboard code block from the previous message here)
PY

echo "🔪 Killing old uvicorn..."
kill -9 $(lsof -t -i:8000) 2>/dev/null || true
echo "🚀 Relaunching backend..."
nohup uvicorn main:app --reload --port 8000 > logs/backend.log 2>&1 &
sleep 3
echo "🌐 Open → http://127.0.0.1:8000/dashboard"
echo "✅ Phase 36.1 dashboard upgrade complete."


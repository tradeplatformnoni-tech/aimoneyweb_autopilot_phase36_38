#!/bin/bash
echo "🚀 Phase 1901–2000 : Brain Merge + Central Memory Integration"
echo "-------------------------------------------------------------"

# 1️⃣ Prepare folders
mkdir -p ai config logs tools

# 2️⃣ Create Brain Merge service
cat > ai/brain_merge.py <<'EOF'
"""
ai/brain_merge.py
Collects data from reinforcement, optimizer, and agents,
merges into a unified brain.json memory file.
"""
import json, os, datetime

sources = [
    "config/optimizer.json",
    "config/strategies.json",
    "logs/firewall_log.json"
]

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def merge():
    merged = {"timestamp": datetime.datetime.now().isoformat(), "sources": {}}
    for src in sources:
        merged["sources"][src] = load_json(src)
    os.makedirs("config", exist_ok=True)
    with open("config/brain.json", "w") as f:
        json.dump(merged, f, indent=2)
    print("✅ brain.json updated.")

if __name__ == "__main__":
    merge()
EOF
echo "🧩 Brain merge module created (ai/brain_merge.py)."

# 3️⃣ Add API endpoints
mkdir -p api/brain
cat > api/brain/routes.py <<'EOF'
from fastapi import APIRouter
import json, os, subprocess

router = APIRouter()

@router.post("/api/brain/merge")
def merge_brain():
    subprocess.call(["python3", "ai/brain_merge.py"])
    return {"status":"merged","file":"config/brain.json"}

@router.get("/api/brain/download")
def download_brain():
    if os.path.exists("config/brain.json"):
        return json.load(open("config/brain.json"))
    return {"error":"brain.json missing"}

@router.post("/api/brain/upload")
def upload_brain(data: dict):
    os.makedirs("config", exist_ok=True)
    with open("config/brain.json","w") as f:
        json.dump(data,f,indent=2)
    return {"status":"uploaded"}
EOF
echo "🧬 Brain API routes ready."

# 4️⃣ Patch backend
MAIN="backend/main.py"
if ! grep -q "api.brain" "$MAIN"; then
  sed -i '' '/from fastapi import FastAPI/a\
from api.brain import routes as brain_routes' "$MAIN"
  sed -i '' '/app = FastAPI()/a\
app.include_router(brain_routes.router)' "$MAIN"
  echo "🔗 Brain routes registered in backend."
fi

# 5️⃣ Restart FastAPI
pkill -f uvicorn 2>/dev/null
nohup uvicorn backend.main:app --reload > logs/backend.log 2>&1 &
echo "🔁 Backend restarted."

# 6️⃣ Send mobile alert if alert script exists
[ -f tools/alert_notify.py ] && python3 tools/alert_notify.py "🧠 Phase 1901–2000: Brain Merge active."

echo "✅ Autopilot complete for Phase 1901–2000."


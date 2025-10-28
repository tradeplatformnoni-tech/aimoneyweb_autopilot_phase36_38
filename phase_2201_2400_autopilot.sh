#!/bin/bash
echo "🚀 Phase 2201–2400 : Collaboration + Deal Engine Integration"
echo "-----------------------------------------------------------"

# 1️⃣ Ensure folders exist
mkdir -p ai api/collab api/deal logs config

# 2️⃣ Human-AI Collaboration module
cat > ai/collaboration_engine.py <<'EOF'
"""
ai/collaboration_engine.py
Simple local module that logs cooperative decisions between a human
operator and AI agents.
"""
import json, datetime, os
LOG = "logs/collaboration_log.json"
os.makedirs("logs", exist_ok=True)

def record(event:str, decision:str, agent:str="system"):
    entry={"timestamp":datetime.datetime.now().isoformat(),
           "event":event,"decision":decision,"agent":agent}
    data=[]
    if os.path.exists(LOG): data=json.load(open(LOG))
    data.append(entry)
    json.dump(data,open(LOG,"w"),indent=2)
    return entry
EOF
echo "🧩 Collaboration engine added."

# 3️⃣ Collaboration API
cat > api/collab/routes.py <<'EOF'
from fastapi import APIRouter
from ai import collaboration_engine

router = APIRouter()

@router.post("/api/collab/record")
def record(data:dict):
    return collaboration_engine.record(
        data.get("event",""),data.get("decision",""),data.get("agent","human"))
EOF

# 4️⃣ Autonomous Deal Engine
cat > ai/deal_engine.py <<'EOF'
"""
ai/deal_engine.py
Offline mock negotiation engine; logs proposals and results.
"""
import json, os, datetime, random
LOG="logs/deal_log.json"
os.makedirs("logs", exist_ok=True)

def propose(parties:list, asset:str, price:float):
    deal={"timestamp":datetime.datetime.now().isoformat(),
          "parties":parties,"asset":asset,"price":price,
          "accepted":random.choice([True,False])}
    data=[]
    if os.path.exists(LOG): data=json.load(open(LOG))
    data.append(deal)
    json.dump(data,open(LOG,"w"),indent=2)
    return deal
EOF
echo "🤝 Deal engine created."

# 5️⃣ Deal API
cat > api/deal/routes.py <<'EOF'
from fastapi import APIRouter
from ai import deal_engine

router = APIRouter()

@router.post("/api/deal/propose")
def propose(data:dict):
    return deal_engine.propose(
        data.get("parties",[]),
        data.get("asset",""),
        float(data.get("price",0)))
EOF

# 6️⃣ Hook routes into backend
MAIN="backend/main.py"
if ! grep -q "api.collab" "$MAIN"; then
  sed -i '' '/from fastapi import FastAPI/a\
from api.collab import routes as collab_routes' "$MAIN"
  sed -i '' '/app = FastAPI()/a\
app.include_router(collab_routes.router)' "$MAIN"
fi
if ! grep -q "api.deal" "$MAIN"; then
  sed -i '' '/from fastapi import FastAPI/a\
from api.deal import routes as deal_routes' "$MAIN"
  sed -i '' '/app = FastAPI()/a\
app.include_router(deal_routes.router)' "$MAIN"
fi
echo "🔗 Routes registered in backend."

# 7️⃣ Restart FastAPI
pkill -f uvicorn 2>/dev/null
nohup uvicorn backend.main:app --reload > logs/backend.log 2>&1 &
echo "🔁 Backend restarted."

# 8️⃣ Optional alert
[ -f tools/alert_notify.py ] && python3 tools/alert_notify.py "🧩 Phase 2201–2400 active | Collab + Deal Engine ready"

echo "✅ Autopilot complete for Phase 2201–2400."


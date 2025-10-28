#!/bin/bash
echo "🚀 Phase 2001–2200 : NLP Query + Marketplace Integration"
echo "-------------------------------------------------------"

# 1️⃣  Make sure directories exist
mkdir -p ai api/nlp api/marketplace config logs

# 2️⃣  NLP Query engine
cat > ai/nlp_query.py <<'EOF'
"""
ai/nlp_query.py
Tiny offline NLP parser to answer questions about agent status and trades.
"""
import json, re, os

DATA = {
    "agents": ["Atlas","SportsInsight","CollectiblesBot","Studio"],
    "symbols": json.load(open("config/symbols.json")) if os.path.exists("config/symbols.json") else []
}

def query(text:str):
    t=text.lower()
    if "agents" in t: 
        return {"agents":DATA["agents"]}
    if "symbols" in t or "assets" in t:
        return {"symbols":DATA["symbols"]}
    return {"message":"Query understood but no matching data."}

if __name__=="__main__":
    q=input("Ask NeoLight: ")
    print(query(q))
EOF
echo "🧩 NLP query module created (ai/nlp_query.py)."

# 3️⃣  NLP API endpoint
cat > api/nlp/routes.py <<'EOF'
from fastapi import APIRouter
from ai import nlp_query

router = APIRouter()

@router.post("/api/nlp/query")
def ask(data: dict):
    q=data.get("query","")
    return nlp_query.query(q)
EOF

# 4️⃣  Marketplace API skeleton
cat > api/marketplace/routes.py <<'EOF'
from fastapi import APIRouter
import json, os

router = APIRouter()
MARKET="config/marketplace.json"

def load():
    return json.load(open(MARKET)) if os.path.exists(MARKET) else []

@router.get("/api/marketplace/list")
def list_agents():
    return load()

@router.post("/api/marketplace/publish")
def publish(agent: dict):
    data=load()
    data.append(agent)
    json.dump(data,open(MARKET,"w"),indent=2)
    return {"status":"published","count":len(data)}
EOF
echo "🛍  Marketplace API ready."

# 5️⃣  Wire routes into backend/main.py
MAIN="backend/main.py"
if ! grep -q "api.nlp" "$MAIN"; then
  sed -i '' '/from fastapi import FastAPI/a\
from api.nlp import routes as nlp_routes' "$MAIN"
  sed -i '' '/app = FastAPI()/a\
app.include_router(nlp_routes.router)' "$MAIN"
fi
if ! grep -q "api.marketplace" "$MAIN"; then
  sed -i '' '/from fastapi import FastAPI/a\
from api.marketplace import routes as marketplace_routes' "$MAIN"
  sed -i '' '/app = FastAPI()/a\
app.include_router(marketplace_routes.router)' "$MAIN"
fi
echo "🔗 Routes registered in backend."

# 6️⃣  Restart FastAPI
pkill -f uvicorn 2>/dev/null
nohup uvicorn backend.main:app --reload > logs/backend.log 2>&1 &
echo "🔁 Backend restarted."

# 7️⃣  Optional alert
[ -f tools/alert_notify.py ] && python3 tools/alert_notify.py "💬 Phase 2001–2200 active | NLP + Marketplace ready"

echo "✅ Autopilot complete for Phase 2001–2200."


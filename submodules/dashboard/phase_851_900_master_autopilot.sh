#!/usr/bin/env bash
# ==========================================================
# NeoLight :: Phase 851–900 — Advisor Dashboard + Risk & Sentiment Panels
# ==========================================================
set -e

echo "🧠 NeoLight v4.8 — Advisor Dashboard + Insight Panels"
mkdir -p backend static tools ai runtime logs

# ------------- 851–870 : Frontend Risk & Sentiment Panels -----------------
cat > static/dashboard_v48.html <<'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NeoLight v4.8 — Advisor Dashboard</title>
<link rel="stylesheet" href="/static/style.css">
<style>
  body { background:#050505; color:#0ff; font-family: 'Consolas', monospace; }
  .tabs { display:flex; gap:8px; margin:10px; }
  .tab-content { display:none; padding:15px; }
  .tab-content.active { display:block; border:1px solid #0ff; }
  .panel { padding:10px; margin-top:10px; border:1px solid #099; border-radius:6px; }
  .data { font-size:0.9rem; color:#fff; background:#111; padding:6px; border-radius:4px; white-space:pre-wrap; }
  button { background:#0ff; border:none; padding:8px 14px; border-radius:4px; cursor:pointer; }
  button:hover { background:#099; }
</style>
</head>
<body>
<h1>💡 AI Money Web :: NeoLight v4.8 — Advisor Dashboard</h1>

<div class="tabs">
  <button data-tab="overview">Overview</button>
  <button data-tab="risk">Risk Panel</button>
  <button data-tab="sentiment">Sentiment Panel</button>
  <button data-tab="advisor">AI Advisor</button>
</div>

<div id="overview" class="tab-content active">
  <div class="panel"><h3>🧭 System Overview</h3>
    <pre class="data" id="overviewData">Loading...</pre>
  </div>
</div>

<div id="risk" class="tab-content">
  <div class="panel"><h3>⚖️ Risk Metrics</h3>
    <pre class="data" id="riskData">Loading...</pre>
  </div>
</div>

<div id="sentiment" class="tab-content">
  <div class="panel"><h3>💬 Market Sentiment</h3>
    <pre class="data" id="sentData">Loading...</pre>
  </div>
</div>

<div id="advisor" class="tab-content">
  <div class="panel"><h3>🧠 AI Advisor</h3>
    <textarea id="advisorInput" placeholder="Ask NeoLight..."></textarea><br>
    <button id="askBtn">Ask</button>
    <pre class="data" id="advisorReply">...</pre>
  </div>
</div>

<script>
const tabs=document.querySelectorAll('[data-tab]');
tabs.forEach(btn=>btn.addEventListener('click',()=>{
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.getElementById(btn.dataset.tab).classList.add('active');
}));
async function loadOverview(){ 
  const h=await fetch('/api/health').then(r=>r.json()); 
  document.getElementById('overviewData').textContent=JSON.stringify(h,null,2);
}
async function loadRisk(){ 
  const r=await fetch('/api/risk').then(r=>r.json()); 
  document.getElementById('riskData').textContent=JSON.stringify(r,null,2);
}
async function loadSent(){ 
  const s=await fetch('/api/sentiment/latest').then(r=>r.json()); 
  document.getElementById('sentData').textContent=JSON.stringify(s,null,2);
}
async function askAdvisor(){
  const msg=document.getElementById('advisorInput').value;
  const r=await fetch('/api/advisor',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:msg})});
  const j=await r.json();
  document.getElementById('advisorReply').textContent=JSON.stringify(j,null,2);
}
document.getElementById('askBtn').addEventListener('click',askAdvisor);
setInterval(loadOverview,5000);
setInterval(loadRisk,7000);
setInterval(loadSent,9000);
loadOverview();loadRisk();loadSent();
</script>
</body>
</html>
HTML

# ------------- 871–880 : Backend Advisor Response Logic -----------------
cat > backend/advisor_ai.py <<'PY'
"""
Simple AI Advisor logic — returns natural language explanation from metrics.
"""
import json, pathlib, random, datetime

RISK=pathlib.Path("runtime/risk_metrics.json")
SENT=pathlib.Path("runtime/sentiment_log.jsonl")

def answer(question:str):
    risk=json.load(open(RISK)) if RISK.exists() else {}
    lines=SENT.read_text().splitlines() if SENT.exists() else []
    mood="neutral"
    if lines: mood=json.loads(lines[-1]).get("mood","neutral")
    msg=f"As of {datetime.datetime.utcnow().isoformat()}, market mood is {mood}. "
    if risk:
        msg+=f"Volatility={risk.get('volatility',0):.3f}, Sharpe={risk.get('sharpe',0):.2f}, VaR={risk.get('var_95',0):.3f}. "
        if risk.get('sharpe',0)>1: msg+="Performance is strong — risk-adjusted returns look healthy. "
        elif risk.get('sharpe',0)<0: msg+="Returns are negative risk-adjusted — caution advised. "
    else:
        msg+="No risk metrics yet, still initializing."
    suggestions=[
        "consider rebalancing your momentum allocation",
        "stay defensive until volatility stabilizes",
        "AI will monitor mean reversion opportunities"
    ]
    msg+=random.choice(suggestions)
    return {"answer":msg}
PY

# ------------- 881–890 : Add POST /api/advisor -----------------
cat > backend/advisor_routes_v2.py <<'PY'
from fastapi import APIRouter, Request
from backend.advisor_ai import answer

router = APIRouter()

@router.post("/api/advisor")
async def post_advisor(req:Request):
    data = await req.json()
    q = data.get("question","")
    return answer(q)
PY

# Include this new router if not already done
if ! grep -q "advisor_routes_v2" backend/main.py; then
  sed -i.bak '1s|^|from backend.advisor_routes_v2 import router as advisor_v2_router\n|' backend/main.py
  sed -i '' 's|app = FastAPI.*|&\napp.include_router(advisor_v2_router)|' backend/main.py
fi

# ------------- 891–900 : AutoFix Pilot+ Upgrade -----------------
cat > tools/neolight_fix_upgrade_plus.sh <<'BASH'
#!/usr/bin/env bash
echo "🧠 NeoLight AutoFix Pilot+ running..."
chmod +x *.sh backend/*.py tools/*.py ai/**/*.py || true
pip install --upgrade fastapi uvicorn requests pandas numpy psutil || true
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
nohup python tools/risk_daemon.py >> logs/risk.log 2>&1 &
nohup python tools/sentiment_daemon.py >> logs/sentiment.log 2>&1 &
nohup python tools/allocator_cron.py >> logs/allocator.log 2>&1 &
sleep 2
echo "✅ AutoFix Complete — Dashboard: http://localhost:8000/dashboard_v48.html"
BASH
chmod +x tools/neolight_fix_upgrade_plus.sh

# Restart backend to apply routes
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
sleep 2
echo "✅ Phase 851–900 installed."
echo "💡 Open dashboard: http://localhost:8000/dashboard_v48.html"
echo "🧩 Heal anytime:   tools/neolight_fix_upgrade_plus.sh"


#!/bin/bash

echo "🧠 Starting Phase 1561–1600: AI Ops + Agent Orchestration + Remote Triggering..."

# 🛠️ 1. Create Orchestrator (agent scheduler)
mkdir -p tools

cat <<EOF > tools/orchestrator.py
# tools/orchestrator.py

import time, random, subprocess

agents = {
    "atlas": "python agents/atlas/runner.py",
    "dropship": "python agents/dropship/runner.py",
    "ticketbot": "python agents/ticketbot/runner.py",
    "sports": "python agents/sports/runner.py",
    "collectibles": "python agents/collectibles/runner.py",
    "luxury": "python agents/luxury/runner.py",
    "studio": "python agents/studio/runner.py"
}

print("🧠 Orchestrator started. Scheduling agents...")

while True:
    agent = random.choice(list(agents.keys()))
    print(f"⏱️ Running: {agent}")
    subprocess.call(agents[agent], shell=True)
    time.sleep(60)
EOF

# 🌐 2. Create API Trigger endpoint
mkdir -p api/orchestrator

cat <<EOF > api/orchestrator/trigger.py
# api/orchestrator/trigger.py

from fastapi import APIRouter
import subprocess

router = APIRouter()

@router.post("/api/trigger/{agent}")
def trigger(agent: str):
    try:
        subprocess.Popen(f"python agents/{agent}/runner.py", shell=True)
        return {"status": "launched", "agent": agent}
    except Exception as e:
        return {"error": str(e)}
EOF

# 🔧 3. Patch backend/main.py to include new routes
main_file="backend/main.py"

if grep -q "orchestrator" "$main_file"; then
    echo "✅ Orchestrator routes already integrated in backend."
else
    echo "⚙️ Injecting orchestrator trigger route into FastAPI..."

    sed -i '' '/from fastapi import FastAPI/a\
from api.orchestrator import trigger as orchestrator_trigger' "$main_file"

    sed -i '' '/app = FastAPI()/a\
app.include_router(orchestrator_trigger.router)' "$main_file"
fi

# 🖥️ 4. Add new agent buttons to dashboard (if not already present)
console_ui="console/index.html"

if grep -q "trigger('/api/trigger/sports')" "$console_ui"; then
    echo "✅ Dashboard already includes agent buttons."
else
    echo "🧠 Adding agent launch buttons to console..."

    sed -i '' '/<div id="output"><\/div>/a\
<button onclick="trigger(\\'/api/trigger/sports\\')">🏈 SportsInsight</button>\n\
<button onclick="trigger(\\'/api/trigger/collectibles\\')">💎 CollectiblesBot</button>\n\
<button onclick="trigger(\\'/api/trigger/luxury\\')">👠 ChicSniper</button>\n\
<button onclick="trigger(\\'/api/trigger/studio\\')">🎙️ StudioBot</button>' "$console_ui"
fi

echo "✅ AI Ops Layer Installed!"
echo "🚀 You can now:"
echo "   ➤ Start Orchestrator: python tools/orchestrator.py"
echo "   ➤ Trigger Agent API:  curl -X POST localhost:8000/api/trigger/{agent}"
echo "   ➤ Use Dashboard Buttons to Launch Agents"


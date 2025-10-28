from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import json, os

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    status = {
        "agents": [],
        "optimizer": {},
        "brain": {},
        "market": {},
    }
    if os.path.exists("config/agents.json"):
        status["agents"] = json.load(open("config/agents.json"))
    if os.path.exists("config/optimizer.json"):
        status["optimizer"] = json.load(open("config/optimizer.json"))
    if os.path.exists("config/brain.json"):
        status["brain"] = json.load(open("config/brain.json"))
    if os.path.exists("config/marketplace.json"):
        status["market"] = json.load(open("config/marketplace.json"))

    html = f"""
    <html>
      <head><title>NeoLight Core Console</title></head>
      <body style='font-family: Arial;'>
        <h1>🧠 NeoLight Core Console</h1>
        <h3>System Overview</h3>
        <pre>{json.dumps(status, indent=2)}</pre>
        <h3>Quick Actions</h3>
        <ul>
          <li><a href="/api/brain/download">Download Brain JSON</a></li>
          <li><a href="/api/nlp/query">NLP Query</a></li>
          <li><a href="/api/marketplace/list">Marketplace List</a></li>
          <li><a href="/api/collab/record">Collaboration Log</a></li>
        </ul>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

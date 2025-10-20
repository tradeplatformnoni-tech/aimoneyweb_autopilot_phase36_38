from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
import asyncio, datetime, random

app = FastAPI(title="AI Money Web :: K8s Canary (151–160)")

app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {
        "message": "✅ K8s Canary service online",
        "phase": "151–160",
        "version": "v1",  # override at build with ARG/ENV if desired
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return FileResponse("static/dashboard.html")

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json({
                "equity": round(100000 + random.uniform(-400, 400), 2),
                "var": round(random.uniform(0.005, 0.035), 4),
                "signal": random.choice(["BUY","SELL","HOLD"]),
                "ts": datetime.datetime.utcnow().isoformat()
            })
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass

from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/api/console/retrain")
def reinforce():
    return {"message": "🧠 Reinforcement triggered (simulated)"}

@router.get("/api/console/restart")
def restart():
    os.system("pm2 restart neolight")
    return {"message": "♻️ Restart command issued (via PM2)"}

@router.get("/api/console/atlas/launch")
def launch_atlas():
    return {"message": "⚡ Atlas Agent Launch initiated (stub)"}

@router.get("/api/console/health")
def health():
    return {"status": "ok", "uptime": "stable", "mode": "LIVE"}

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

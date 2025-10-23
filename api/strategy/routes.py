from fastapi import APIRouter
import subprocess

router = APIRouter()

@router.post("/api/strategy/generate")
def generate():
    try:
        subprocess.call(["python3", "ai/strategy_generator.py"])
        return {"status": "success", "message": "strategies regenerated"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

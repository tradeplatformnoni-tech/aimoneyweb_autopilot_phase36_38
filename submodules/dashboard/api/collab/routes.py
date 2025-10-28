from fastapi import APIRouter
from ai import collaboration_engine

router = APIRouter()

@router.post("/api/collab/record")
def record(data:dict):
    return collaboration_engine.record(
        data.get("event",""),data.get("decision",""),data.get("agent","human"))

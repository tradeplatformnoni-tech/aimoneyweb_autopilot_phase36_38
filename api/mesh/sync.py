# api/mesh/sync.py

from fastapi import APIRouter
from mesh.agentsync import agent_sync

router = APIRouter()

@router.post("/api/mesh/sync")
def sync_agent(agent_id: str, signal_data: str):
    return agent_sync(agent_id, signal_data)

# api/mesh/message.py

from fastapi import APIRouter
from mesh.core import mesh_bus

router = APIRouter()

@router.post("/api/mesh/message")
def message(sender: str, msg: str):
    return mesh_bus.broadcast(sender, msg)

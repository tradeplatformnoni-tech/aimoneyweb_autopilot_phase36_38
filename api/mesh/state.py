# api/mesh/state.py

from fastapi import APIRouter
from mesh.core import mesh_bus

router = APIRouter()

@router.get("/api/mesh/state")
def state():
    return mesh_bus.get_state()

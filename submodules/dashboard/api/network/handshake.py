# api/network/handshake.py

from fastapi import APIRouter
from network.node import node

router = APIRouter()

@router.get("/api/network/handshake")
def handshake():
    return node.get_identity()

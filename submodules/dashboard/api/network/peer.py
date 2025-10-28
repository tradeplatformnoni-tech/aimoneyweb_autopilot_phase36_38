# api/network/peer.py

from fastapi import APIRouter
from network.node import node

router = APIRouter()

@router.post("/api/network/peer")
def register(peer_id: str, address: str):
    peer_info = node.register_peer(peer_id, address)
    return {"registered": peer_info}

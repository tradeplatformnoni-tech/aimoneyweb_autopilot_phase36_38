# api/network/ping.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/api/network/ping")
def ping():
    return {"pong": True}

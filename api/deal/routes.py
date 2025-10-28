from fastapi import APIRouter
from ai import deal_engine

router = APIRouter()

@router.post("/api/deal/propose")
def propose(data:dict):
    return deal_engine.propose(
        data.get("parties",[]),
        data.get("asset",""),
        float(data.get("price",0)))

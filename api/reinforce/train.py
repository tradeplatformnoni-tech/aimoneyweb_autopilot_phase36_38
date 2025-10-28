# api/reinforce/train.py
from fastapi import APIRouter
from ai.reinforcement.reinforce_engine import ReinforceEngine

router = APIRouter()
engine = ReinforceEngine()

@router.post("/api/reinforce/train")
def train():
    engine.train()
    return {"message": "Training initiated"}

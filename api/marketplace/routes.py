from fastapi import APIRouter
import json, os

router = APIRouter()
MARKET="config/marketplace.json"

def load():
    return json.load(open(MARKET)) if os.path.exists(MARKET) else []

@router.get("/api/marketplace/list")
def list_agents():
    return load()

@router.post("/api/marketplace/publish")
def publish(agent: dict):
    data=load()
    data.append(agent)
    json.dump(data,open(MARKET,"w"),indent=2)
    return {"status":"published","count":len(data)}

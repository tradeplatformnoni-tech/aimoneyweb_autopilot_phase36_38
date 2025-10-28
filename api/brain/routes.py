from fastapi import APIRouter
import json, os, subprocess

router = APIRouter()

@router.post("/api/brain/merge")
def merge_brain():
    subprocess.call(["python3", "ai/brain_merge.py"])
    return {"status":"merged","file":"config/brain.json"}

@router.get("/api/brain/download")
def download_brain():
    if os.path.exists("config/brain.json"):
        return json.load(open("config/brain.json"))
    return {"error":"brain.json missing"}

@router.post("/api/brain/upload")
def upload_brain(data: dict):
    os.makedirs("config", exist_ok=True)
    with open("config/brain.json","w") as f:
        json.dump(data,f,indent=2)
    return {"status":"uploaded"}

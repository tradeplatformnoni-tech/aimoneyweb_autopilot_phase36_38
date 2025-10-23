from fastapi import APIRouter, Request
import json, os, time

router = APIRouter()
MAILBOX = "logs/mesh_inbox.json"

def _load():
    return json.load(open(MAILBOX)) if os.path.exists(MAILBOX) else []

def _save(data):
    json.dump(data, open(MAILBOX,"w"), indent=2)

@router.post("/api/mesh/send")
async def send_message(req: Request):
    msg = await req.json()
    data = _load()
    msg["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    data.append(msg)
    _save(data)
    return {"status":"sent","count":len(data)}

@router.get("/api/mesh/inbox")
def inbox():
    return _load()

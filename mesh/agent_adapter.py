# mesh/agent_adapter.py

import requests

def mesh_sync(agent_id, signal_data):
    payload = {"agent_id": agent_id, "signal_data": signal_data}
    try:
        res = requests.post("http://127.0.0.1:8000/api/mesh/sync", json=payload, timeout=2)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

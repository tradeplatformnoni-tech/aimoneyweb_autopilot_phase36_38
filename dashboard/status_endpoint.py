from fastapi import FastAPI
import psutil, os, time, datetime, json, glob

app = FastAPI(title="NeoLight Guardian v23.1", version="23.1")

def safe_json(obj):
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception as e:
        return {"error": str(e)}

@app.get("/status")
def status():
    try:
        logs = {os.path.basename(f): time.ctime(os.path.getmtime(f)) for f in glob.glob(os.path.expanduser("~/neolight/logs/*.log"))}
        processes = [p.info for p in psutil.process_iter(attrs=["pid","name","cpu_percent","memory_percent"]) if any(k in (p.info.get("name") or "") for k in ["uvicorn","intelligence_orchestrator","smart_trader","weights_bridge"])]
        system = {
            "cpu": psutil.cpu_percent(interval=0.3),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent,
            "uptime": datetime.datetime.now().isoformat(),
        }
        return safe_json({"system": system, "guardian": {"logs": logs, "agents": processes}})
    except Exception as e:
        return {"error": f"Guardian status failed: {e}"}

"""
NeoLight Experience Memory Engine
Records signals, risk, and sentiment into rolling memory files.
"""
import json, datetime, pathlib
RUNTIME = pathlib.Path("runtime")
MEMORY = RUNTIME / "experience_log.jsonl"

def record(event: dict):
    event["timestamp"] = datetime.datetime.utcnow().isoformat()
    MEMORY.open("a").write(json.dumps(event)+"\n")

def summarize(limit=50):
    lines = MEMORY.read_text().strip().splitlines()[-limit:] if MEMORY.exists() else []
    data = [json.loads(l) for l in lines]
    return {"entries": len(data), "sample": data[-3:] if data else []}

if __name__ == "__main__":
    record({"type":"init","msg":"Experience memory online"})
    print(summarize())

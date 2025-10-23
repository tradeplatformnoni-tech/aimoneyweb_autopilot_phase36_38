"""
ai/collaboration_engine.py
Simple local module that logs cooperative decisions between a human
operator and AI agents.
"""
import json, datetime, os
LOG = "logs/collaboration_log.json"
os.makedirs("logs", exist_ok=True)

def record(event:str, decision:str, agent:str="system"):
    entry={"timestamp":datetime.datetime.now().isoformat(),
           "event":event,"decision":decision,"agent":agent}
    data=[]
    if os.path.exists(LOG): data=json.load(open(LOG))
    data.append(entry)
    json.dump(data,open(LOG,"w"),indent=2)
    return entry

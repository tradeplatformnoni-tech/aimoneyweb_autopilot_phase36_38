"""
ai/brain_merge.py
Collects data from reinforcement, optimizer, and agents,
merges into a unified brain.json memory file.
"""
import json, os, datetime

sources = [
    "config/optimizer.json",
    "config/strategies.json",
    "logs/firewall_log.json"
]

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def merge():
    merged = {"timestamp": datetime.datetime.now().isoformat(), "sources": {}}
    for src in sources:
        merged["sources"][src] = load_json(src)
    os.makedirs("config", exist_ok=True)
    with open("config/brain.json", "w") as f:
        json.dump(merged, f, indent=2)
    print("✅ brain.json updated.")

if __name__ == "__main__":
    merge()

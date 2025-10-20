import os, time, json, requests

CMD_FILE = "voice_commands.txt"   # put lines like: set_strategy B  | pause | resume
BASE = os.environ.get("AIMW_BASE", "http://127.0.0.1:8000")

def _apply(cmd: str):
    c = cmd.strip().lower()
    if not c: return "skip"
    if c.startswith("set_strategy"):
        _, s = c.split()
        requests.post(f"{BASE}/api/strategy", json={"strategy": s.upper()}, timeout=2)
        return f"set_strategy {s}"
    if c == "pause":
        requests.post(f"{BASE}/api/mode", json={"mode": "paused"}, timeout=2)
        return "paused"
    if c == "resume":
        requests.post(f"{BASE}/api/mode", json={"mode": "trading"}, timeout=2)
        return "trading"
    if c.startswith("risk_cap"):
        _, val = c.split()
        requests.post(f"{BASE}/api/risk", json={"cap": float(val)}, timeout=2)
        return f"risk_cap {val}"
    return f"unknown:{c}"

def main():
    seen = set()
    while True:
        if os.path.exists(CMD_FILE):
            with open(CMD_FILE) as f:
                for i, line in enumerate(f):
                    if i in seen: continue
                    action = _apply(line)
                    print("🎙️ voice:", action)
                    seen.add(i)
        time.sleep(2)

if __name__ == "__main__":
    main()

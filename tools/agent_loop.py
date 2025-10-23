import os, json, time, datetime, requests, psutil, subprocess, traceback
from pathlib import Path

BASE = "http://127.0.0.1:8000"
RUNTIME = Path("runtime")
SIGNALS = RUNTIME/"signals.jsonl"
AGENT_STATE = RUNTIME/"agent_state.json"
AGENT_LOG = RUNTIME/"agent_log.jsonl"
NOTIFY_CFG = RUNTIME/"notify_config.json"

def jread(p, d): 
    try: return json.load(open(p,"r"))
    except: return d
def jwrite(p, o): json.dump(o, open(p,"w"), indent=2)
def append_log(entry): open(AGENT_LOG,"a").write(json.dumps(entry)+"\n")

def health_ok():
    try:
        r = requests.get(BASE+"/api/health", timeout=5)
        return r.ok
    except Exception:
        return False

def notify(message):
    try:
        # Use backend notify endpoint if available
        r = requests.post(BASE+"/api/notify/test", json={"message": message}, timeout=8)
        if r.ok: return True
    except Exception: pass
    # Offline fallback: print to stdout
    print("[ALERT]", message)
    append_log({"ts":datetime.datetime.utcnow().isoformat(),"type":"notify_fallback","message":message})
    return False

def ensure_services():
    # Ensure FastAPI exists
    backend_up = any("uvicorn" in p.name() for p in psutil.process_iter(attrs=["name"]))
    if not backend_up:
        notify("⚠️ Backend down. Attempting AutoFix…")
        try:
            subprocess.call(["neolight-fix"])
        except Exception:
            # fallback local bring-up
            subprocess.Popen(["nohup","uvicorn","backend.main:app","--host","0.0.0.0","--port","8000","--reload"])
        time.sleep(3)
    # Ensure strategy daemon exists
    daemon_up = any("strategy_daemon.py" in " ".join(p.cmdline()) for p in psutil.process_iter(attrs=["cmdline"]))
    if not daemon_up:
        notify("⚠️ Strategy daemon down. Restarting…")
        subprocess.Popen(["nohup","python","tools/strategy_daemon.py"])

def read_new_signals():
    state = jread(AGENT_STATE, {"last_ts": None})
    last_ts = state.get("last_ts")
    new = []
    if not SIGNALS.exists(): 
        return new
    with open(SIGNALS,"r") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                obj = json.loads(line)
                ts = obj.get("timestamp")
                if (last_ts is None) or (ts and ts > last_ts):
                    new.append(obj)
            except: pass
    if new:
        state["last_ts"] = new[-1].get("timestamp")
        jwrite(AGENT_STATE, state)
    return new

def summarize(signals):
    # Simple per-interval ensemble summary
    votes = {"BUY":0,"SELL":0,"HOLD":0}
    for s in signals: votes[s.get("signal","HOLD")] = votes.get(s.get("signal","HOLD"),0)+1
    if votes["BUY"]>=2: final="BUY"
    elif votes["SELL"]>=2: final="SELL"
    else: final="HOLD"
    return final, votes

def main_loop():
    print("🌩️  Cloud AI Agent running…")
    while True:
        try:
            ensure_services()
            ok = health_ok()
            if not ok: 
                notify("❌ Backend health failed after AutoFix attempt.")
                time.sleep(5); 
                continue

            news = read_new_signals()
            if news:
                final, votes = summarize(news)
                price = news[-1].get("price")
                msg = f"🧠 NeoLight signal update: {final} @ {price} | votes={votes}"
                notify(msg)
                append_log({"ts":datetime.datetime.utcnow().isoformat(),"type":"signal_summary","final":final,"votes":votes,"price":price})
        except Exception as e:
            append_log({"ts":datetime.datetime.utcnow().isoformat(),"type":"agent_error","err":str(e)})
            traceback.print_exc()
        time.sleep(10)

if __name__=="__main__":
    main_loop()

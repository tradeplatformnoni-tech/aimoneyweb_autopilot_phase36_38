import os, time, subprocess, requests
PORT = "8000"
BASE = f"http://127.0.0.1:{PORT}"

def start():
    with open("logs/backend.log","a") as f:
        return subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",PORT],stdout=f,stderr=f)

def healthy():
    try:
        requests.get(BASE+"/",timeout=2); requests.get(BASE+"/api/alpaca_status",timeout=2)
        return True
    except:
        return False

def main():
    os.makedirs("logs",exist_ok=True)
    p=start()
    while True:
        if p.poll() is not None or not healthy():
            os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
            p=start()
        time.sleep(7)

if __name__=="__main__":
    main()

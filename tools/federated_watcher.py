import subprocess, time, requests, os

PORT = "8000"
BASE = f"http://127.0.0.1:{PORT}"

def healthy():
    try:
        r = requests.get(BASE, timeout=2)
        return r.status_code == 200
    except:
        return False

def start():
    return subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",PORT],
        stdout=open("logs/backend.log","a"), stderr=subprocess.STDOUT)

def loop():
    p = start()
    while True:
        if p.poll() is not None or not healthy():
            os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
            p = start()
        if time.time() % 120 < 2: # upload every ~2 minutes
            requests.post(BASE+"/api/cloud_backup",timeout=3)
        time.sleep(8)

if __name__=="__main__":
    os.makedirs("logs",exist_ok=True)
    loop()

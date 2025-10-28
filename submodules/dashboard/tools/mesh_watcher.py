import subprocess, requests, time, os
PORT = "8000"
BASE = f"http://127.0.0.1:{PORT}"

def start():
  return subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",PORT],
    stdout=open("logs/backend.log","a"), stderr=subprocess.STDOUT)

def healthy():
  try:
    r = requests.get(BASE,timeout=2)
    return r.status_code == 200
  except Exception:
    return False

def loop():
  p = start()
  while True:
    if p.poll() is not None or not healthy():
      os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
      p = start()
    time.sleep(8)

if __name__ == "__main__":
  os.makedirs("logs",exist_ok=True)
  loop()

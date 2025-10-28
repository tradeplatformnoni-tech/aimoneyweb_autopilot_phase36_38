import subprocess, requests, os, time, random

PORT="8000"
BASE=f"http://127.0.0.1:{PORT}"
NODES=["clusterA","clusterB","clusterC"]

def launch_cluster(name):
  log=open(f"logs/{name}.log","a")
  print(f"🚀 Launching {name}...")
  return subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",PORT],
    stdout=log,stderr=log)

def healthy():
  try:
    return requests.get(BASE,timeout=2).status_code==200
  except:
    return False

def loop():
  p=launch_cluster("orchestrator_main")
  while True:
    if p.poll() is not None or not healthy():
      os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
      p=launch_cluster("orchestrator_restarted")
    if random.random()<0.2:
      with open("logs/scale_activity.log","a") as f:
        f.write(f"Scaled nodes at {time.asctime()}\n")
    time.sleep(10)

if __name__=="__main__":
  os.makedirs("logs",exist_ok=True)
  loop()

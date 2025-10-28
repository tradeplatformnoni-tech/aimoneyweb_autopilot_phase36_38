import os, time, subprocess, requests
PORT = 8000
def health(): 
    try: return requests.get(f"http://127.0.0.1:{PORT}/").ok
    except Exception: return False
def main():
    while True:
        if not health():
            os.system(f"kill -9 $(lsof -t -i:{PORT}) 2>/dev/null || true")
            subprocess.Popen(["venv/bin/python3","-m","uvicorn","main:app","--host","127.0.0.1","--port",str(PORT)])
        time.sleep(10)
if __name__ == "__main__": main()

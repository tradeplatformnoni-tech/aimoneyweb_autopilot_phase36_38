import os, time, subprocess, requests, signal, sys, threading

APP_PORT = 8000
CHECK_INTERVAL = 5
SERVER_CMD = ["uvicorn", "main:app", "--reload", "--port", str(APP_PORT)]
LOG_FILE = "logs/autopilot.log"

os.makedirs("logs", exist_ok=True)

def kill_port(port):
    os.system(f"kill -9 $(lsof -t -i:{port}) 2>/dev/null || true")

def start_server():
    print("🚀 Launching FastAPI backend...")
    with open(LOG_FILE, "a") as f:
        process = subprocess.Popen(SERVER_CMD, stdout=f, stderr=f)
    return process

def check_endpoint(url):
    try:
        r = requests.get(url, timeout=3)
        return r.status_code == 200
    except Exception:
        return False

def monitor_server(proc):
    print("🧠 Monitoring FastAPI health...")
    while True:
        alive = proc.poll() is None
        root_ok = check_endpoint(f"http://127.0.0.1:{APP_PORT}/")
        alpaca_ok = check_endpoint(f"http://127.0.0.1:{APP_PORT}/api/alpaca_status")

        if not alive or not (root_ok and alpaca_ok):
            print("⚠️  Server unhealthy. Restarting...")
            kill_port(APP_PORT)
            proc.terminate()
            time.sleep(2)
            proc = start_server()
        else:
            print("✅ Server healthy — all endpoints OK.")
        time.sleep(CHECK_INTERVAL)

def start_tests():
    while True:
        print("🧪 Running integration tests...")
        subprocess.run(["pytest", "test/test_integrations.py", "-q"])
        time.sleep(30)

def main():
    kill_port(APP_PORT)
    server_proc = start_server()

    threading.Thread(target=monitor_server, args=(server_proc,), daemon=True).start()
    threading.Thread(target=start_tests, daemon=True).start()

    print("🧠 AI Money Web Autopilot engaged. Monitoring every", CHECK_INTERVAL, "seconds.")
    print(f"🌐 Dashboard: http://127.0.0.1:{APP_PORT}/dashboard")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down gracefully...")
        kill_port(APP_PORT)
        sys.exit(0)

if __name__ == "__main__":
    main()

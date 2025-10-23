import os, time, json, subprocess, requests, datetime

LOG_PATH = "logs/autopilot_observer.jsonl"
PUSH_URL = "https://api.pushover.net/1/messages.json"
PUSH_USER = os.getenv("PUSHOVER_USER")
PUSH_TOKEN = os.getenv("PUSHOVER_TOKEN")

def push_alert(title, msg):
    if not PUSH_USER or not PUSH_TOKEN:
        print("⚠️  Pushover creds missing; alert suppressed.")
        return
    data = {"token": PUSH_TOKEN, "user": PUSH_USER, "title": title, "message": msg}
    requests.post(PUSH_URL, data=data)

def monitor():
    while True:
        now = datetime.datetime.now().isoformat()
        output = subprocess.getoutput("docker ps --format '{{.Names}} {{.Status}}'")
        status = {line.split()[0]: " ".join(line.split()[1:]) for line in output.splitlines()}
        record = {"timestamp": now, "status": status}
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f: f.write(json.dumps(record) + "\n")
        for name, state in status.items():
            if "Exited" in state or "Restarting" in state:
                push_alert("NeoLight Auto-Heal", f"{name} => {state}")
                subprocess.run(["docker", "restart", name])
        time.sleep(60)

if __name__ == "__main__":
    print("🛡️ Observer active — monitoring containers...")
    monitor()


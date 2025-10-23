#!/bin/bash

echo "🧠 Phase 1651–1700: Self-Healing AI + Alerting Ops Autopilot..."

# Create tools folder
mkdir -p tools

# -------------------------------
# 1. AI Log Scanner
cat <<EOF > tools/log_ai_scanner.py
import re

def scan_log(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    errors = [line for line in lines if re.search(r'(Traceback|ERROR|Exception|KeyError|ValueError)', line)]
    if errors:
        print("❗ AI Scanner detected issues:")
        for err in errors[-5:]:
            print("🧠", err.strip())
    else:
        print("✅ No major errors detected.")

if __name__ == "__main__":
    scan_log("logs/backend.log")
EOF

# -------------------------------
# 2. Watchdog Script
cat <<EOF > tools/watchdog_loop.sh
#!/bin/bash

echo "🔁 Starting NeoLight Watchdog..."

while true; do
  STATUS=\$(curl -s http://127.0.0.1:8000/api/health | grep ok)
  if [ -z "\$STATUS" ]; then
    echo "❗ FastAPI DOWN — healing with neolight-fix..."
    ./neolight-fix

    echo "📟 Triggering alert..."
    python3 tools/alert_notify.py "FastAPI was down and has been auto-healed."
  else
    echo "✅ FastAPI healthy."
  fi
  sleep 60
done
EOF

chmod +x tools/watchdog_loop.sh

# -------------------------------
# 3. Mobile Alert Script
cat <<EOF > tools/alert_notify.py
import sys
import requests

def send_alert(message):
    # Replace with your real Pushover credentials
    user_key = "YOUR_USER_KEY"
    token = "YOUR_API_TOKEN"

    payload = {
        "token": token,
        "user": user_key,
        "message": message
    }

    r = requests.post("https://api.pushover.net/1/messages.json", data=payload)
    print("📲 Alert sent!" if r.status_code == 200 else "❗ Alert failed.")

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "🧠 NeoLight Alert"
    send_alert(msg)
EOF

echo "✅ Self-Healing & Notification Layer Installed!"
echo "📈 Start Watchdog with:   ./tools/watchdog_loop.sh"
echo "🧪 Scan Logs Manually:    python3 tools/log_ai_scanner.py"
echo "📲 Test Alert:            python3 tools/alert_notify.py 'Test message'"


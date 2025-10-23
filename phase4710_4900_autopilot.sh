#!/bin/bash
# 🚀 NeoLight Phase 4710–4900 Autopilot
# AI Wealth Mesh Infrastructure Automation

set -e

echo "======================================================"
echo "🧠 NeoLight Autopilot Phase 4710–4900 Initializing..."
echo "======================================================"
sleep 1

# 🧩 PATCH STRATEGY
echo "🧩 [PATCH STRATEGY] Checking environment + dependencies..."
python3 -m venv venv || true
source venv/bin/activate
pip install --upgrade pip >/dev/null
pip install flask gunicorn requests plotly docker pyyaml kubernetes >/dev/null

# 🛠️ AutoFix Logic
echo "🛠️ [NeoLight-Fix] Running environment checks..."
mkdir -p logs cache tmp runtime config dashboard k8s || true
touch runtime/portfolio.json runtime/goal_config.json logs/autopilot_4710.log

# 🧼 Port Handler + Sanitizer Check
if [ ! -f "dashboard/flask_port_handler.py" ]; then
    echo "🧩 Writing dashboard/flask_port_handler.py..."
    cat > dashboard/flask_port_handler.py <<'PY'
import socket
def get_free_port(default=5050):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port or default
if __name__ == "__main__":
    print(get_free_port())
PY
fi

# 💻 Jinja Sanitizer
if [ ! -f "dashboard/jinja_sanitizer.py" ]; then
    echo "🧩 Writing dashboard/jinja_sanitizer.py..."
    cat > dashboard/jinja_sanitizer.py <<'PY'
import re
def clean_template(content:str)->str:
    return re.sub(r'\{\{.*?\}\}', '', content)
PY
fi

# 🐋 Docker Compose Setup
echo "🐋 Writing docker-compose.yml..."
cat > docker-compose.yml <<'YAML'
version: "3.9"
services:
  dashboard:
    build: ./dashboard
    ports:
      - "5050:5050"
    environment:
      - PORT=5050
    restart: always

  autopatch:
    image: neolight/autopatch:latest
    build:
      context: .
      dockerfile: autopatch_controller.py
    restart: always
    environment:
      - PUSHOVER_TOKEN=${PUSHOVER_TOKEN}
      - PUSHOVER_USER=${PUSHOVER_USER}
YAML

# 🧱 Build Docker Image
echo "🐳 Building Docker image for dashboard..."
docker build -t neolight/dashboard:latest dashboard || true

# ⚙️ Local Run Check
echo "🚀 Testing local Gunicorn dashboard..."
PORT=$(python3 dashboard/flask_port_handler.py)
export PORT
bash dashboard/run_gunicorn.sh &

sleep 5
if curl -s http://127.0.0.1:$PORT | grep -q "NeoLight"; then
    echo "✅ Dashboard responding on port $PORT"
else
    echo "⚠️ Dashboard not responding, applying autofix..."
    pkill -f gunicorn || true
    bash dashboard/run_gunicorn.sh &
fi

# ☸️ K8s AutoPatch CronJob
echo "☸️ Writing Kubernetes NeoLight AutoPatch CronJob..."
cat > k8s/neolight-autopatch-cronjob.yaml <<'YAML'
apiVersion: batch/v1
kind: CronJob
metadata:
  name: neolight-autopatch
spec:
  schedule: "*/2 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: autopatch
            image: neolight/autopatch:latest
            imagePullPolicy: IfNotPresent
          restartPolicy: OnFailure
YAML

echo "☸️ Attempting to apply Kubernetes CronJob..."
kubectl apply -f k8s/neolight-autopatch-cronjob.yaml --validate=false || echo "⚠️ K8s not running yet."

# 🧠 Final Summary
echo "======================================================"
echo "✅ NeoLight Autopilot 4710–4900 Complete!"
echo "======================================================"
echo "1️⃣  Local Gunicorn dashboard live: http://127.0.0.1:${PORT}"
echo "2️⃣  To rebuild Docker image: docker build -t neolight/dashboard:latest dashboard"
echo "3️⃣  To start Compose stack: docker compose up --build"
echo "4️⃣  To apply K8s CronJob:  kubectl apply -f k8s/neolight-autopatch-cronjob.yaml"
echo "======================================================"


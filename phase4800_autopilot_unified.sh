#!/bin/bash
# 🧠  NeoLight Phase 4800 AutoPilot + Self-Healing Fix
# One-touch repair & redeploy script for Flask / Docker / Gunicorn stacks.

echo "🚀 Starting NeoLight Phase 4800 AutoPilot Fix..."

ROOT_DIR="$(pwd)"
DASHBOARD_DIR="${ROOT_DIR}/dashboard"
echo "📁 Project Root: $ROOT_DIR"

# --------------------------------------------------------------------
# 1. Ensure dashboard folder + files exist
# --------------------------------------------------------------------
if [ ! -d "$DASHBOARD_DIR" ]; then
  echo "⚠️ Missing dashboard folder — creating..."
  mkdir -p "$DASHBOARD_DIR"
fi

if [ ! -f "$DASHBOARD_DIR/flask_app.py" ]; then
  echo "⚙️ Creating default flask_app.py"
  cat > "$DASHBOARD_DIR/flask_app.py" <<'EOF'
from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "🧠 NeoLight Dashboard Active — Phase 4800"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
EOF
fi

# Guarantee Python treats dashboard as package
touch "$DASHBOARD_DIR/__init__.py"

# --------------------------------------------------------------------
# 2. Auto-repair Dockerfile
# --------------------------------------------------------------------
cat > "$DASHBOARD_DIR/Dockerfile" <<'EOF'
# 🧠 NeoLight Dashboard Dockerfile — Phase 4800 Stable
FROM python:3.12-slim
WORKDIR /app

# Copy entire project context
COPY . /app

RUN pip install --no-cache-dir flask gunicorn plotly requests pandas numpy pyyaml

EXPOSE 5050
ENV PYTHONPATH=/app

# ✅ Directly call flask_app (no ' dashboard. ' prefix)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5050", "flask_app:app"]
EOF
echo "✅ Dockerfile patched."

# --------------------------------------------------------------------
# 3. Auto-generate docker-compose.yml
# --------------------------------------------------------------------
if [ ! -f "${ROOT_DIR}/docker-compose.yml" ]; then
  echo "⚙️ Generating docker-compose.yml..."
  cat > "${ROOT_DIR}/docker-compose.yml" <<'EOF'
version: "3.9"
services:
  dashboard:
    build:
      context: .
      dockerfile: dashboard/Dockerfile
    ports:
      - "5050:5050"
    restart: unless-stopped
EOF
fi

# --------------------------------------------------------------------
# 4. Permission & Dependency Fix
# --------------------------------------------------------------------
echo "🔧 Repairing permissions and dependencies..."
chmod -R 755 dashboard || true
chmod +x *.sh || true
pip install --upgrade pip > /dev/null 2>&1
pip install flask gunicorn requests plotly pandas numpy pyyaml > /dev/null 2>&1

# --------------------------------------------------------------------
# 5. Docker Rebuild & Launch
# --------------------------------------------------------------------
echo "🧱 Rebuilding Docker images..."
docker compose down --remove-orphans
docker compose build --no-cache

if [ $? -eq 0 ]; then
  echo "✅ Build successful — starting containers..."
  docker compose up -d
else
  echo "❌ Build failed — check Docker permissions or daemon."
  exit 1
fi

# --------------------------------------------------------------------
# 6. Self-Healing Monitor (Neo Light-Fix)
# --------------------------------------------------------------------
echo "🩺 Activating Neo Light-Fix monitor..."
cat > neo_lightfix_watchdog.sh <<'EOF'
#!/bin/bash
# Auto-restart any container that fails
while true; do
  for c in $(docker ps -a --format '{{.Names}}'); do
    status=$(docker inspect -f '{{.State.Running}}' "$c")
    if [ "$status" != "true" ]; then
      echo "⚙️ Restarting $c..."
      docker restart "$c" > /dev/null
    fi
  done
  sleep 15
done
EOF
chmod +x neo_lightfix_watchdog.sh
nohup ./neo_lightfix_watchdog.sh >/dev/null 2>&1 &

echo "✅ NeoLight Phase 4800 AutoPilot Fix complete!"
echo "🌐 Visit http://127.0.0.1:5050 after containers start."


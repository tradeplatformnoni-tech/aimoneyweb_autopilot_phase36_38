#!/bin/bash
# 🧠 NeoLight Phase 4770 AutoPilot Fix + Context Healer
# Combines all fixes, path checks, permissions, and rebuild logic.
# Run this from your project root (e.g. aimoneyweb_autopilot_phase36_38)

echo "🚀 Starting NeoLight Phase 4770 AutoPilot Fix..."

PROJECT_ROOT="$(pwd)"
DASHBOARD_DIR="${PROJECT_ROOT}/dashboard"

echo "📁 Checking build context: $PROJECT_ROOT"

# --------------------------------------------------------------------
# 1. Verify dashboard folder exists and has files
# --------------------------------------------------------------------
if [ ! -d "$DASHBOARD_DIR" ]; then
  echo "⚠️  Missing dashboard directory. Creating..."
  mkdir -p "$DASHBOARD_DIR"
  echo 'print("🧠 Flask dashboard placeholder")' > "$DASHBOARD_DIR/flask_app.py"
fi

if [ ! -f "$DASHBOARD_DIR/__init__.py" ]; then
  echo "✅ Creating __init__.py"
  touch "$DASHBOARD_DIR/__init__.py"
fi

# --------------------------------------------------------------------
# 2. Fix Dockerfile — ensure COPY source is visible to Docker
# --------------------------------------------------------------------
cat > "$DASHBOARD_DIR/Dockerfile" <<'EOF'
# 🧠 NeoLight Dashboard Dockerfile (Phase 4770 Context Healer)
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir flask gunicorn plotly requests pandas numpy pyyaml

ENV PYTHONPATH=/app
EXPOSE 5050

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5050", "dashboard.flask_app:app"]
EOF
echo "✅ Dockerfile rewritten."

# --------------------------------------------------------------------
# 3. Rebuild docker-compose.yml if missing
# --------------------------------------------------------------------
if [ ! -f "${PROJECT_ROOT}/docker-compose.yml" ]; then
  echo "⚙️  Creating docker-compose.yml..."
  cat > "${PROJECT_ROOT}/docker-compose.yml" <<'EOF'
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
# 4. Permissions and dependency fixes
# --------------------------------------------------------------------
echo "🔧 Fixing permissions and Python deps..."
chmod -R 755 dashboard || true
chmod +x *.sh || true
pip install --upgrade pip > /dev/null 2>&1
pip install flask gunicorn requests plotly pandas numpy pyyaml > /dev/null 2>&1

# --------------------------------------------------------------------
# 5. Rebuild Docker image with visible context
# --------------------------------------------------------------------
echo "🧱 Rebuilding Docker context..."
cd "$PROJECT_ROOT"
docker compose down
docker compose build --no-cache

if [ $? -eq 0 ]; then
  echo "✅ Build succeeded — launching containers..."
  docker compose up
else
  echo "❌ Build failed — checking context visibility..."
  echo "🔍 Run 'ls -R dashboard' to verify files exist inside build context."
fi

echo "🧠 Phase 4770 AutoPilot Fix complete!"


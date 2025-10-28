#!/bin/bash
# 🧠 NeoLight Phase 4760 AutoPilot Fix — Resolves Docker build context errors automatically

echo "🚀 Phase 4760: Scanning and repairing dashboard build context..."

# Ensure correct working directory
if [ ! -d "dashboard" ]; then
  echo "⚠️  dashboard directory missing — recreating..."
  mkdir -p dashboard
fi

# Confirm flask_app.py presence
if [ ! -f "dashboard/flask_app.py" ]; then
  echo "❌ flask_app.py missing! Restoring backup if available..."
  if [ -f "dashboard/flask_app.py.bak"* ]; then
    cp dashboard/flask_app.py.bak-* dashboard/flask_app.py
    echo "✅ Restored from backup."
  else
    echo "⚙️  Creating placeholder flask_app.py..."
    echo 'print("🧠 Flask dashboard initialized")' > dashboard/flask_app.py
  fi
fi

# Repair Dockerfile with correct relative paths
cat > dashboard/Dockerfile <<'EOF'
# 🧠 NeoLight Wealth Mesh Dashboard (Phase 4760 Stable)
FROM python:3.12-slim

WORKDIR /app
COPY ./dashboard /app/dashboard

# Install all dependencies
RUN pip install --no-cache-dir flask gunicorn plotly requests pandas numpy pyyaml

ENV PYTHONPATH=/app
EXPOSE 5050

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5050", "dashboard.flask_app:app"]
EOF

echo "✅ Dockerfile fixed."

# Check docker-compose.yml
if [ ! -f "docker-compose.yml" ]; then
  echo "⚙️  Creating docker-compose.yml..."
  cat > docker-compose.yml <<'EOF'
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

echo "🔧 Fixing permissions..."
chmod -R 755 dashboard
chmod +x *.sh || true

# Rebuild docker image
echo "🧱 Rebuilding Docker image..."
docker compose down
docker compose build --no-cache

if [ $? -eq 0 ]; then
  echo "✅ Build successful. Starting containers..."
  docker compose up
else
  echo "❌ Build failed. Please verify docker path visibility."
fi

echo "🧠 Phase 4760 AutoPilot Fix complete!"


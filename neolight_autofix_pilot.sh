#!/bin/bash
# 🧠 NeoLight Auto-Fix Pilot v2 — Repairs missing Docker paths and restarts builds.

echo "🚀 Starting NeoLight Auto-Fix Pilot..."
echo "📁 Checking directory structure..."

# Ensure you are in project root
if [ ! -d "dashboard" ]; then
  echo "⚠️  dashboard folder not found. Creating it..."
  mkdir -p dashboard
  echo 'print("🧠 Flask dashboard placeholder")' > dashboard/flask_app.py
fi

# Ensure Dockerfile exists in the dashboard folder
if [ ! -f "dashboard/Dockerfile" ]; then
  echo "⚙️  Creating missing dashboard/Dockerfile..."
  cat > dashboard/Dockerfile <<'EOF'
# 🧠 NeoLight Wealth Mesh Dashboard (Auto-Fix)
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir flask gunicorn plotly requests pandas numpy pyyaml

ENV PYTHONPATH=/app
EXPOSE 5050

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5050", "flask_app:app"]
EOF
fi

# Fix import paths for Flask app
if ! grep -q "__init__.py" dashboard/__init__.py 2>/dev/null; then
  echo "✅ Adding __init__.py..."
  touch dashboard/__init__.py
fi

# Fix permission denied issues
echo "🔧 Fixing permissions..."
chmod +x *.sh || true
chmod -R 755 dashboard || true

# Check for venv or install base dependencies
if [ -d "venv" ]; then
  echo "🐍 Using local virtual environment..."
  source venv/bin/activate
else
  echo "📦 Installing Python dependencies globally..."
  pip install flask gunicorn requests plotly pandas numpy pyyaml
fi

# Repair Docker build context
echo "🧩 Fixing Docker context..."
if [ ! -f "docker-compose.yml" ]; then
  echo "⚠️ docker-compose.yml not found — creating a basic one..."
  cat > docker-compose.yml <<'EOF'
version: "3.9"
services:
  dashboard:
    build:
      context: .
      dockerfile: dashboard/Dockerfile
    ports:
      - "5050:5050"
    restart: always
EOF
fi

echo "🚀 Running docker compose build..."
docker compose down
docker compose up --build

echo "✅ NeoLight Auto-Fix Pilot complete!"


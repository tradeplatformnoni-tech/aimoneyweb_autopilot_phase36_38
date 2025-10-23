#!/usr/bin/env bash
# ==============================================================
# NeoLight Phase 4700 — Implementation Autopilot
# Patches dashboard (port handler + sanitizer), upgrades to Gunicorn,
# adds /health, writes Dockerfile, and deploys K8s Auto-Patch CronJob.
# Idempotent & safe: backs up files before change.
# ==============================================================

set -euo pipefail

echo "🚀 Phase 4700: Starting implementation…"

ROOT_DIR="$(pwd)"
TS="$(date +%Y%m%d-%H%M%S)"
mkdir -p logs dashboard k8s ai agents scripts runtime config

# ---------- helpers ----------
backup_file () {
  local f="$1"
  if [[ -f "$f" ]]; then
    cp "$f" "${f}.bak-${TS}"
    echo "🗄️  Backed up $f -> ${f}.bak-${TS}"
  fi
}

have_cmd () { command -v "$1" >/dev/null 2>&1; }

# ---------- deps ----------
echo "📦 Ensuring Python deps (flask, gunicorn, requests, plotly)…"
PYDEPS=(flask gunicorn requests plotly)
for p in "${PYDEPS[@]}"; do
  python3 - <<PY || pip install "$p"
import importlib, sys
try:
    sys.exit(0 if importlib.util.find_spec("${p}") else 1)
except AttributeError:
    sys.exit(0)
PY
done

# ---------- port handler ----------
mkdir -p dashboard
PORT_HANDLER="dashboard/flask_port_handler.py"
cat > "$PORT_HANDLER" <<'PY'
# NEOLIGHT_PHASE4700_PORT_HANDLER
import socket, os

def get_available_port(default=5050):
    # Respect env override if provided
    env_port = os.environ.get("PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass
    # Try default first
    if _is_free(default):
        return default
    # Otherwise find a free ephemeral
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def _is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0
PY
echo "🧩 Wrote $PORT_HANDLER"

# ---------- jinja sanitizer ----------
SANITIZER="dashboard/jinja_sanitizer.py"
cat > "$SANITIZER" <<'PY'
# NEOLIGHT_PHASE4700_JINJA_SANITIZER
import re

def sanitize_template(raw_html: str) -> str:
    # Strip non-printable chars that break Jinja parsing
    return re.sub(r'[^\x09\x0A\x0D\x20-\x7E]', '', raw_html)
PY
echo "🧼 Wrote $SANITIZER"

# ---------- patch / write Flask app ----------
APP="dashboard/flask_app.py"
NEEDS_WRITE=0
if [[ ! -f "$APP" ]]; then
  NEEDS_WRITE=1
else
  # If not already patched by Phase 4700, rewrite (with backup)
  if ! grep -q "NEOLIGHT_PHASE4700" "$APP"; then
    NEEDS_WRITE=1
  fi
fi

if [[ "$NEEDS_WRITE" -eq 1 ]]; then
  backup_file "$APP"
  cat > "$APP" <<'PY'
# NEOLIGHT_PHASE4700 — Flask Visualization Layer (clean rewrite)
from flask import Flask, jsonify, render_template_string
import json, pathlib, os, time, requests, plotly.graph_objects as go

from dashboard.flask_port_handler import get_available_port
from dashboard.jinja_sanitizer import sanitize_template

app = Flask(__name__)

def load_json_safe(path):
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as e:
        return {"error": str(e)}

def fetch_crypto_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        ids = "bitcoin,ethereum,gold"
        r = requests.get(url, params={"ids": ids, "vs_currencies": "usd"}, timeout=6)
        data = r.json()
        return {
            "BTC": data.get("bitcoin", {}).get("usd"),
            "ETH": data.get("ethereum", {}).get("usd"),
            "GOLD": data.get("gold", {}).get("usd"),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {"error": str(e)}

@app.route("/health")
def health():
    # Simple liveness endpoint for K8s
    return jsonify({"status":"ok","ts":time.time()})

@app.route("/")
def index():
    portfolio = load_json_safe("runtime/portfolio.json")
    telemetry = load_json_safe("logs/telemetry_push.json")
    risk = load_json_safe("config/risk_policy.json")
    prices = fetch_crypto_prices()

    # Build Plotly
    fig = go.Figure()
    if isinstance(prices, dict) and "BTC" in prices and isinstance(prices.get("BTC"), (int, float, float)):
        labels = [k for k in ["BTC","ETH","GOLD"] if isinstance(prices.get(k), (int, float))]
        values = [prices[k] for k in labels]
        fig.add_trace(go.Bar(x=labels, y=values, marker_color=['#f2a900','#627eea','#ffd700']))
        fig.update_layout(title="Live Prices (USD)", template="plotly_dark", height=320)
        chart_html = fig.to_html(full_html=False)
    else:
        chart_html = "<p>❌ Could not fetch prices from CoinGecko.</p>"

    html = """
    {% raw %}
    <html>
      <head>
        <title>NeoLight Wealth Mesh Dashboard</title>
        <meta http-equiv="refresh" content="15">
        <style>
          body { background-color:#0a0f14; color:#e8e8e8; font-family:monospace; }
          h1 { color:#00ff9d; }
          h2 { color:#00ffff; }
          .section { margin-bottom:20px; padding:10px; border:1px solid #222; border-radius:8px; }
          pre { color:#b2f7ff; white-space: pre-wrap; word-break: break-word; }
          footer { color:#777; margin-top:30px; }
        </style>
      </head>
      <body>
        <h1>🧠 NeoLight Wealth Mesh Dashboard</h1>

        <div class="section">
          <h2>🪙 Live BTC/ETH/GOLD Prices</h2>
          <pre>{{ prices }}</pre>
          {{ chart_html|safe }}
        </div>

        <div class="section">
          <h2>💰 Portfolio (runtime/portfolio.json)</h2>
          <pre>{{ portfolio }}</pre>
        </div>

        <div class="section">
          <h2>📊 Telemetry (logs/telemetry_push.json)</h2>
          <pre>{{ telemetry }}</pre>
        </div>

        <div class="section">
          <h2>🛡️ Risk Policy (config/risk_policy.json)</h2>
          <pre>{{ risk }}</pre>
        </div>

        <footer>
          <small>Auto-refresh every 15s • Last updated {{ now }}</small>
        </footer>
      </body>
    </html>
    {% endraw %}
    """
    html = sanitize_template(html)
    return render_template_string(
        html,
        prices=json.dumps(prices, indent=2),
        portfolio=json.dumps(portfolio, indent=2),
        telemetry=json.dumps(telemetry, indent=2),
        risk=json.dumps(risk, indent=2),
        chart_html=chart_html,
        now=time.strftime('%Y-%m-%d %H:%M:%S')
    )

if __name__ == "__main__":
    port = get_available_port(default=int(os.environ.get("PORT", "5050") or 5050))
    print(f"🌍 Dashboard live on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port)
PY
  echo "🖥️  Wrote clean dashboard app to $APP"
else
  echo "✅ $APP already patched (NEOLIGHT_PHASE4700), skipping rewrite."
fi

# ---------- dashboard Dockerfile (Gunicorn) ----------
DOCKERFILE="dashboard/Dockerfile"
backup_file "$DOCKERFILE"
cat > "$DOCKERFILE" <<'DOCK'
# NEOLIGHT_PHASE4700 Dockerfile for Dashboard
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flask gunicorn requests plotly
EXPOSE 5050
CMD ["gunicorn","-w","4","-b","0.0.0.0:5050","dashboard.flask_app:app"]
DOCK
echo "🐳 Wrote $DOCKERFILE"

# ---------- k8s autopatch cronjob ----------
mkdir -p k8s
CRON="k8s/neolight-autopatch-cronjob.yaml"
cat > "$CRON" <<'YAML'
# NEOLIGHT_PHASE4700 Autopatch CronJob
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
          restartPolicy: OnFailure
          containers:
            - name: autopatch
              image: neolight/autopatch:latest  # replace with your built image
              imagePullPolicy: IfNotPresent
              env:
                - name: PUSHOVER_TOKEN
                  valueFrom:
                    secretKeyRef:
                      name: pushover-secrets
                      key: token
                - name: PUSHOVER_USER
                  valueFrom:
                    secretKeyRef:
                      name: pushover-secrets
                      key: user
              # Example command (adjust to your repo layout)
              command: ["python","autopatch_controller.py"]
YAML
echo "☸️  Wrote $CRON"

# ---------- optional: apply CronJob if kubectl exists ----------
if have_cmd kubectl; then
  echo "☸️  Applying K8s CronJob (neolight-autopatch)…"
  kubectl apply -f "$CRON" || echo "⚠️ kubectl apply failed — configure K8s first."
else
  echo "ℹ️  kubectl not found — skipped CronJob apply."
fi

# ---------- local dashboard run helper (Gunicorn) ----------
RUNNER="dashboard/run_gunicorn.sh"
cat > "$RUNNER" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT:-}"
if [[ -z "$PORT" ]]; then PORT=5050; fi
echo "🚀 Starting dashboard via Gunicorn on :$PORT"
exec gunicorn -w 4 -b "0.0.0.0:${PORT}" "dashboard.flask_app:app"
SH
chmod +x "$RUNNER"
echo "▶️  Wrote $RUNNER"

echo "✅ Phase 4700 implementation complete."
echo "Next:"
echo "1) Local Gunicorn run:   PORT=5050 bash dashboard/run_gunicorn.sh"
echo "2) Build Docker image:   docker build -t neolight/dashboard:latest dashboard"
echo "3) Run with Docker:      docker run -p 5050:5050 neolight/dashboard:latest"
echo "4) Apply K8s CronJob:    kubectl apply -f k8s/neolight-autopatch-cronjob.yaml"


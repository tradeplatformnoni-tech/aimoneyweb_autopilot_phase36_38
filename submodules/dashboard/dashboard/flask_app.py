# 🧠 NeoLight Phase 4750 — Flask Visualization Layer (Optimized for Docker/K8s)
# Author: Oluwaseye Akinbola & AI QA Dev Mentor
# Purpose: Unified AI Wealth Mesh Dashboard with Auto-Healing + Live Crypto/Gold Insights

from flask import Flask, jsonify, render_template_string
import json, pathlib, os, time, requests, plotly.graph_objects as go
from flask_port_handler import get_available_port
from jinja_sanitizer import sanitize_template

app = Flask(__name__)

# -------------------------------------------------------------------
# Utility: Load JSON data safely (portfolio, telemetry, risk configs)
# -------------------------------------------------------------------
def load_json_safe(path):
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as e:
        return {"error": str(e)}

# -------------------------------------------------------------------
# Fetch Live Prices (with Fallbacks: CoinGecko → cached → 0)
# -------------------------------------------------------------------
def fetch_crypto_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        ids = "bitcoin,ethereum,gold"
        r = requests.get(url, params={"ids": ids, "vs_currencies": "usd"}, timeout=8)
        data = r.json()
        return {
            "BTC": data.get("bitcoin", {}).get("usd", 0),
            "ETH": data.get("ethereum", {}).get("usd", 0),
            "GOLD": data.get("gold", {}).get("usd", 0),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"⚠️ Price fetch error: {e}")
        return {"error": str(e)}

# -------------------------------------------------------------------
# Health Check (Kubernetes & Autopilot diagnostics)
# -------------------------------------------------------------------
@app.route("/health")
def health():
    return jsonify({"status": "ok", "ts": time.time()})

# -------------------------------------------------------------------
# Main Dashboard Route
# -------------------------------------------------------------------
@app.route("/")
def index():
    portfolio = load_json_safe("runtime/portfolio.json")
    telemetry = load_json_safe("logs/telemetry_push.json")
    risk = load_json_safe("config/risk_policy.json")
    prices = fetch_crypto_prices()

    # Plotly Chart Generation
    fig = go.Figure()
    if all(isinstance(prices.get(k), (int, float)) for k in ["BTC", "ETH", "GOLD"]):
        labels = ["BTC", "ETH", "GOLD"]
        values = [prices[k] for k in labels]
        fig.add_trace(go.Bar(x=labels, y=values, marker_color=['#f2a900','#627eea','#ffd700']))
        fig.update_layout(title="Live Market Prices (USD)", template="plotly_dark", height=320)
        chart_html = fig.to_html(full_html=False)
    else:
        chart_html = "<p>❌ Could not fetch prices — check API or cache.</p>"

    # Template (auto-refresh + modular)
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
          <h2>🪙 Live BTC / ETH / GOLD Prices</h2>
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

# -------------------------------------------------------------------
# Run (Local + Docker Compatible)
# -------------------------------------------------------------------
if __name__ == "__main__":
    port = get_available_port(default=int(os.environ.get("PORT", "5050") or 5050))
    print(f"🌍 Dashboard live on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port)


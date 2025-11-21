#!/usr/bin/env bash
set -e
echo "🧠 Nuking and rewriting NeoLight Dashboard..."

DASH_DIR="$HOME/neolight/dashboard"
mkdir -p "$DASH_DIR"

cat > "$DASH_DIR/launch_dashboard.py" <<'PY'
#!/usr/bin/env python3
# NeoLight — Self-Healing Wealth Dashboard
# Auto-installs dependencies if missing

import os, sys, subprocess, json, time
from pathlib import Path

def ensure_deps():
    try:
        import fastapi, uvicorn, pandas, plotly
    except ModuleNotFoundError:
        print("⚙️ Installing missing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "plotly", "pandas"])

ensure_deps()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import pandas as pd, plotly.express as px
import uvicorn

app = FastAPI(title="NeoLight Wealth Dashboard")

@app.get("/", response_class=HTMLResponse)
def home():
    html = "<h1>🧠 NeoLight Dashboard</h1><ul>"
    for f in Path.home().joinpath("neolight/state").glob("*.csv"):
        html += f"<li><a href='/chart?file={f.name}'>{f.name}</a></li>"
    html += "</ul>"
    return html

@app.get("/chart", response_class=HTMLResponse)
def chart(file: str):
    f = Path.home() / "neolight/state" / file
    if not f.exists():
        return f"<h3>❌ File {file} not found.</h3>"
    df = pd.read_csv(f)
    if "date" not in df.columns:
        df.columns = [c.lower() for c in df.columns]
    if "date" not in df.columns:
        return f"<h3>⚠️ No date column found in {file}.</h3>"
    fig = px.line(df, x="date", y=df.columns[-1], title=f"{file}")
    return fig.to_html(full_html=True)

if __name__ == "__main__":
    print("🌐 Launching NeoLight Dashboard → http://127.0.0.1:8090")
    uvicorn.run(app, host="127.0.0.1", port=8090)
PY

chmod +x "$DASH_DIR/launch_dashboard.py"
echo "✅ Dashboard rewritten and self-healing ready."
echo "🚀 To start, run:"
echo "python3 ~/neolight/dashboard/launch_dashboard.py"

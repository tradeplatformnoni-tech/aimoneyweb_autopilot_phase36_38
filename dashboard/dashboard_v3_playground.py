#!/usr/bin/env python3
import os
import socket
from pathlib import Path

import pandas as pd
import plotly.express as px
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

ROOT = Path(os.path.expanduser("~/neolight"))
STATE, RUNTIME = ROOT / "state", ROOT / "runtime"
STATE.mkdir(parents=True, exist_ok=True)
RUNTIME.mkdir(parents=True, exist_ok=True)
STRAT_FILE = RUNTIME / "strategy_weights.json"

app = FastAPI()


def find_free_port(start=8095, end=8099):
    for p in range(start, end + 1):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", p))
            s.close()
            return p
        except OSError:
            s.close()
    raise RuntimeError("no free port")


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html><head><title>NeoLight V3 — Strategy Lab</title>
    <script>
    async function saveWeights(){
      const text = document.getElementById('weights').value;
      await fetch('/save_weights', {method:'POST',body:text});
      alert('✅ Saved to strategy_weights.json');
    }
    setInterval(()=>{location.reload();},10000);
    </script>
    </head>
    <body style='background:#0b0f17;color:#d7e1f8;font-family:Inter,system-ui,Arial;'>
      <h1>NeoLight Strategy Lab</h1>
      <textarea id='weights' rows='6' cols='60'>
{"BTC-USD":0.25,"ETH-USD":0.20,"SPY":0.15,"QQQ":0.20,"GLD":0.20}
      </textarea><br>
      <button onclick='saveWeights()'>💾 Save to weights</button>
      <p>Auto-refreshes every 10 seconds.</p>
      <p><a href='/equity_vs_spy'>Equity vs SPY</a></p>
    </body></html>
    """


@app.post("/save_weights")
async def save_weights(req: Request):
    txt = await req.body()
    STRAT_FILE.write_text(txt.decode())
    return {"saved": True}


@app.get("/equity_vs_spy", response_class=HTMLResponse)
def equity_vs_spy():
    eq_path, spy_path = STATE / "performance_metrics.csv", STATE / "spy_benchmark.csv"
    if not eq_path.exists() or not spy_path.exists():
        return HTMLResponse("<pre>Missing data — run orchestrator and benchmark.</pre>")
    eq, spy = pd.read_csv(eq_path), pd.read_csv(spy_path)
    eq["date"] = pd.to_datetime(eq.iloc[:, 0], errors="coerce")
    spy["date"] = pd.to_datetime(spy.iloc[:, 0], errors="coerce")
    eq["equity_norm"] = (eq["equity"] / eq["equity"].iloc[0]) * 100
    spy["spy_norm"] = (spy["SPY_Close"] / spy["SPY_Close"].iloc[0]) * 100
    merged = pd.merge_asof(eq.sort_values("date"), spy.sort_values("date"), on="date")
    fig = px.line(merged, x="date", y=["equity_norm", "spy_norm"], title="Equity vs SPY")
    return HTMLResponse(fig.to_html(include_plotlyjs="cdn"))


if __name__ == "__main__":
    port = int(os.environ.get("NEOLIGHT_DASH_PORT") or find_free_port())
    print(f"🌐 Launching NeoLight V3+ → http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)

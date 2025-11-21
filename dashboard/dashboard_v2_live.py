#!/usr/bin/env python3
import json
import os
import socket
from pathlib import Path

import pandas as pd
import plotly.express as px
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

ROOT = os.path.expanduser("~/neolight")
STATE = Path(ROOT) / "state"
RUNTIME = Path(ROOT) / "runtime"
STATE.mkdir(parents=True, exist_ok=True)
RUNTIME.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="NeoLight Dashboard V2.5")


def find_free_port(start=8090, end=8099):
    for p in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError(f"No free port in {start}-{end}")


def chosen_port():
    env_port = os.environ.get("NEOLIGHT_DASH_PORT")
    if env_port and env_port.isdigit():
        return int(env_port)
    return find_free_port(8090, 8099)


@app.get("/healthz")
def healthz():
    return {"ok": True}


INDEX_HTML = """
<html><head><title>NeoLight Dashboard V2.5</title></head>
<body style="background:#0b0f17;color:#d7e1f8;font-family:Inter,system-ui,Arial;">
  <h1>NeoLight — Live Intelligence</h1>
  <div style="margin:8px 0;padding:6px 10px;background:#121826;border:1px solid #1c2333;border-radius:8px;">
    <b>Panels:</b>
    <a style="color:#7dd3fc" href="/chart?file=performance_metrics.csv">Performance</a> •
    <a style="color:#7dd3fc" href="/chart?file=pnl_history.csv">PnL</a> •
    <a style="color:#7dd3fc" href="/brain">Atlas Brain</a> •
    <a style="color:#7dd3fc" href="/strategy_lab">Strategy Lab</a> •
    <a style="color:#7dd3fc" href="/equity_vs_spy">Equity vs SPY</a> •
    <a style="color:#7dd3fc" href="/healthz">Health</a>
  </div>
</body></html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return INDEX_HTML


@app.get("/chart")
def chart(file: str):
    f = STATE / file
    if not f.exists():
        return JSONResponse({"error": "missing " + file}, status_code=404)
    df = pd.read_csv(f)
    x = "date" if "date" in df.columns else ("Date" if "Date" in df.columns else df.columns[0])
    y = [c for c in df.columns if c.lower() not in ("date", "timestamp")]
    if not y:
        return JSONResponse({"error": "no numeric cols"}, status_code=400)
    fig = px.line(df, x=x, y=y, title=file)
    return HTMLResponse(fig.to_html(include_plotlyjs="cdn"))


@app.get("/brain")
def brain():
    p = RUNTIME / "atlas_brain.json"
    return JSONResponse(json.loads(p.read_text()) if p.exists() else {"error": "no brain"})


@app.get("/strategy_lab")
def strategy_lab():
    f = STATE / "deep_research_rank.csv"
    if not f.exists():
        return JSONResponse({"error": "no deep_research_rank.csv"}, status_code=404)
    try:
        df = pd.read_csv(f)
    except Exception as e:
        return JSONResponse({"error": f"read fail: {e}"}, status_code=500)
    # show top 10
    df = df.head(10)
    html = df.to_html(index=False)
    return HTMLResponse(
        f"<html><body style='background:#0b0f17;color:#d7e1f8;font-family:Inter,system-ui,Arial;'>{html}</body></html>"
    )


@app.get("/equity_vs_spy")
def equity_vs_spy():
    pnl = STATE / "pnl_history.csv"
    if not pnl.exists():
        return JSONResponse({"error": "no pnl_history.csv"}, status_code=404)
    df = pd.read_csv(pnl)
    # Expect 'date' and 'wealth' columns from your replay
    x = "date" if "date" in df.columns else ("Date" if "Date" in df.columns else df.columns[0])
    y = [c for c in df.columns if c.lower() not in ("date", "timestamp")]
    import pandas as pd
    import yfinance as yf

    try:
        spy = yf.download(
            "SPY", period="1y", interval="1d", auto_adjust=True, progress=False
        ).reset_index()
        spy = spy.rename(columns={"Date": "date", "Close": "SPY"})
        # build our equity series if available (wealth or cumulative pnl proxy)
        if "wealth" in df.columns:
            ours = df[[x, "wealth"]].rename(columns={x: "date"})
        else:
            ours = df[[x, y[0]]].rename(columns={x: "date", y[0]: "ours"})
        merged = pd.merge(ours, spy[["date", "SPY"]], on="date", how="inner")
        fig = px.line(
            merged, x="date", y=[c for c in merged.columns if c != "date"], title="Equity vs SPY"
        )
        return HTMLResponse(fig.to_html(include_plotlyjs="cdn"))
    except Exception as e:
        return JSONResponse({"error": f"benchmark failed: {e}"}, status_code=500)


if __name__ == "__main__":
    port = int(os.environ.get("NEOLIGHT_DASH_PORT") or 0) or chosen_port()
    print(f"🌐 Launching NeoLight Dashboard V2.5 → http://127.0.0.1:{port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port)

#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/neolight"
LOG="$ROOT/logs/phase_461_520_$(date +%Y%m%d_%H%M%S).log"
PYBIN="${ROOT}/venv/bin/python3"
PIP="${ROOT}/venv/bin/pip"

echo "🧩 Phase 461–520 Upgrade starting..." | tee -a "$LOG"
[ -d "$ROOT/venv" ] || python3 -m venv "$ROOT/venv"
source "$ROOT/venv/bin/activate"

echo "📦 Installing Python deps..." | tee -a "$LOG"
$PIP -q install --upgrade pip
$PIP -q install fastapi "uvicorn[standard]" plotly pandas numpy yfinance gTTS playsound schedule

# ────────────────────────────────────────────────────────────────────
# Voice Notifier
# ────────────────────────────────────────────────────────────────────
cat > "$ROOT/agents/voice_notifier.py" <<'PY'
#!/usr/bin/env python3
from gtts import gTTS
import os, sys, tempfile, platform, subprocess

def speak(text: str):
    try:
        # prefer system speech for speed if available (macOS)
        if platform.system() == "Darwin":
            subprocess.run(["say", text], check=False)
            return
        # fallback to gTTS
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts = gTTS(text=text)
        tts.save(tmp.name)
        # attempt to play (macOS) or generic playsound
        if platform.system() == "Darwin":
            subprocess.run(["afplay", tmp.name], check=False)
        else:
            try:
                from playsound import playsound
                playsound(tmp.name)
            except Exception:
                print(f"[voice] saved TTS at: {tmp.name}")
    except Exception as e:
        print(f"[voice] WARN: {e}", file=sys.stderr)

if __name__ == "__main__":
    speak("NeoLight voice notifier installed successfully.")
PY
chmod +x "$ROOT/agents/voice_notifier.py"

# ────────────────────────────────────────────────────────────────────
# Strategies Library (toy samples + metadata)
# ────────────────────────────────────────────────────────────────────
cat > "$ROOT/strategies/strategies_library.py" <<'PY'
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Strategy:
    key: str
    name: str
    family: str
    lookback: str
    desc: str

# This is a seed set — extend freely. The orchestrator will blend/score.
STRATEGIES: List[Strategy] = [
    Strategy("trend_ema_20_50", "EMA 20/50 Trend-Follow", "trend", "2y",
             "Go long when EMA20>EMA50 and RSI>50; exit on crossover."),
    Strategy("breakout_donch_20", "Donchian Breakout 20", "trend", "3y",
             "Long on 20-day high breakout; ATR stop; pyramid on strength."),
    Strategy("meanrev_rsi_30_70", "RSI Mean-Reversion 30/70", "meanrev", "2y",
             "Fade extremes: enter long when RSI<30, exit near 50; symmetric short."),
    Strategy("carry_term_structure", "Carry / Term-Structure", "macro", "5y",
             "Bias toward positive carry assets; reduced risk in backwardation."),
    Strategy("quality_momentum", "Quality + Momentum", "factor", "5y",
             "Rank assets by 6–12m momentum and vol-adjusted quality; tilt weights."),
]

def as_dicts() -> List[Dict]:
    return [s.__dict__ for s in STRATEGIES]
PY

# ────────────────────────────────────────────────────────────────────
# Intelligence Orchestrator (reads state, blends strategies, speaks updates)
# ────────────────────────────────────────────────────────────────────
cat > "$ROOT/agents/intelligence_orchestrator.py" <<'PY'
#!/usr/bin/env python3
import json, time, os
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from strategies.strategies_library import as_dicts
from agents.voice_notifier import speak

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
STATE.mkdir(exist_ok=True, parents=True)

def safe_load_json(p: Path, default):
    try:
        if p.exists():
            return json.loads(p.read_text())
    except Exception:
        pass
    return default

def atlas_brain() -> Dict[str, Any]:
    # seed brain if missing
    p = STATE / "atlas_brain.json"
    brain = safe_load_json(p, {"risk_scaler": 0.5, "confidence": 0.25})
    return brain

def risk_allocations() -> Dict[str, float]:
    p = STATE / "risk_allocations.json"
    return safe_load_json(p, {})

def research_rank() -> pd.DataFrame:
    p = STATE / "deep_research_rank.csv"
    if p.exists():
        try:
            return pd.read_csv(p)
        except Exception:
            pass
    return pd.DataFrame(columns=["symbol","return_%","vol_%","sharpe"])

def summarize():
    brain = atlas_brain()
    allocs = risk_allocations()
    deep = research_rank().sort_values("sharpe", ascending=False).head(5)
    msg = (
        f"Atlas confidence {brain.get('confidence',0):.2f}, "
        f"risk {brain.get('risk_scaler',1):.2f}×, "
        f"top assets: {', '.join(deep['symbol'].astype(str).tolist()) or 'n/a'}."
    )
    (ROOT/"state"/"intelligence_summary.json").write_text(json.dumps({
        "brain": brain,
        "top_assets": deep.to_dict(orient="records"),
        "allocations": allocs
    }, indent=2))
    return msg

def main():
    s1 = summarize()
    speak(f"NeoLight update. {s1}")
    # simple change-detection: if allocations changed notably, announce
    alloc = risk_allocations()
    if alloc:
        tops = sorted(alloc.items(), key=lambda x: -x[1])[:3]
        tops_msg = ", ".join([f"{k} {v:.0%}" for k,v in tops])
        speak(f"Top targets: {tops_msg}")

if __name__ == "__main__":
    main()
PY
chmod +x "$ROOT/agents/intelligence_orchestrator.py"

# ────────────────────────────────────────────────────────────────────
# Dashboard V2 (FastAPI + Plotly, benchmark overlay + Strategy Lab)
# ────────────────────────────────────────────────────────────────────
cat > "$ROOT/dashboard/dashboard_v2_live.py" <<'PY'
#!/usr/bin/env python3
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, JSONResponse
import pandas as pd, plotly.graph_objects as go
from pathlib import Path
import json, datetime as dt
import yfinance as yf

ROOT = Path.home() / "neolight"
STATE = ROOT / "state"
app = FastAPI(title="NeoLight Dashboard V2")

def load_csv(name: str) -> pd.DataFrame:
    p = STATE / name
    if p.exists():
        try:
            return pd.read_csv(p)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def equity_vs_spy() -> go.Figure:
    pnl = load_csv("pnl_history.csv")
    if pnl.empty:  # defensive
        pnl = pd.DataFrame({"date": [dt.date.today().isoformat()], "wealth": [100000.0]})
    pnl["date"] = pd.to_datetime(pnl["date"])
    eq = pnl.groupby("date")["wealth"].last().ffill()
    # fetch SPY for same window
    start = eq.index.min().date().isoformat()
    end = eq.index.max().date().isoformat()
    spy = yf.download("SPY", start=start, end=end, interval="1d", auto_adjust=True, progress=False)
    spy = spy.reset_index()
    spy["Date"] = pd.to_datetime(spy["Date"])
    spy_eq = (spy["Close"] / spy["Close"].iloc[0]) * float(eq.iloc[0])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eq.index, y=eq.values, name="NeoLight Equity", mode="lines"))
    fig.add_trace(go.Scatter(x=spy["Date"], y=spy_eq, name="SPY (scaled)", mode="lines"))
    fig.update_layout(margin=dict(l=20,r=20,t=30,b=20), height=420, title="Equity vs SPY Benchmark")
    return fig

def performance_tiles() -> dict:
    perf = load_csv("performance_metrics.csv")
    if perf.empty:
        return {"sharpe": None, "max_drawdown": None, "volatility": None}
    last = perf.tail(1).iloc[0].to_dict()
    return {k: (None if k not in last else last[k]) for k in ["sharpe","max_drawdown","volatility"]}

@app.get("/", response_class=HTMLResponse)
def home():
    tiles = performance_tiles()
    html = f"""
    <html><head><meta charset='utf-8'><title>NeoLight V2</title></head>
    <body style="font-family: -apple-system, Inter, Segoe UI; background: #0b0f14; color: #e6f1ff; padding: 20px;">
      <h1 style="margin:0 0 10px 0;">💡 NeoLight Dashboard V2</h1>
      <div style="opacity:.8;margin-bottom:12px">Live equity, benchmark overlay, and Strategy Lab.</div>
      <div style="display:flex; gap:16px; flex-wrap:wrap;">
        <div style="background:#121826;border:1px solid #243244;border-radius:10px;padding:12px;min-width:220px;">
          <div style="opacity:.6">Sharpe</div>
          <div style="font-size:28px;">{tiles.get('sharpe','—')}</div>
        </div>
        <div style="background:#121826;border:1px solid #243244;border-radius:10px;padding:12px;min-width:220px;">
          <div style="opacity:.6">Max Drawdown</div>
          <div style="font-size:28px;">{tiles.get('max_drawdown','—')}</div>
        </div>
        <div style="background:#121826;border:1px solid #243244;border-radius:10px;padding:12px;min-width:220px;">
          <div style="opacity:.6">Volatility</div>
          <div style="font-size:28px;">{tiles.get('volatility','—')}</div>
        </div>
      </div>
      <div style="margin-top:18px;background:#121826;border:1px solid #243244;border-radius:10px;padding:10px;">
        <iframe src="/equity_bench" style="width:100%;height:460px;border:0;background:#0b0f14;"></iframe>
      </div>
      <div style="margin-top:18px;">
        <a href="/lab" style="color:#66d9ef;">🧪 Strategy Lab</a>
      </div>
      <script>
        // Auto-refresh tiles every 30s by reloading the page tiles
        setTimeout(()=>location.reload(), 30000);
      </script>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/equity_bench", response_class=HTMLResponse)
def equity_bench():
    fig = equity_vs_spy()
    return HTMLResponse(fig.to_html(include_plotlyjs="cdn", full_html=False, config={"displayModeBar": False}))

@app.get("/lab", response_class=HTMLResponse)
def lab():
    p = STATE / "deep_research_rank.csv"
    tbl = ""
    if p.exists():
        df = pd.read_csv(p).sort_values("sharpe", ascending=False).head(15)
        rows = "".join([f"<tr><td>{r.symbol}</td><td>{r['return_%']:.2f}</td><td>{r['vol_%']:.2f}</td><td>{r['sharpe']:.3f}</td></tr>"
                        for r in df.itertuples(index=False)])
        tbl = f"""
        <table style="width:100%;border-collapse:collapse">
          <thead><tr>
            <th align='left'>Symbol</th><th align='left'>Return %</th><th align='left'>Vol %</th><th align='left'>Sharpe</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""
    html = f"""
    <html><head><meta charset='utf-8'><title>Strategy Lab</title></head>
    <body style="font-family: -apple-system, Inter, Segoe UI; background: #0b0f14; color: #e6f1ff; padding: 20px;">
      <h2>🧪 Strategy Lab</h2>
      <div style="opacity:.8;margin-bottom:12px">Top research picks by Sharpe (from deep_research_rank.csv)</div>
      <div style="background:#121826;border:1px solid #243244;border-radius:10px;padding:12px;">{tbl or 'No research yet.'}</div>
      <div style="margin-top:16px"><a href="/" style="color:#66d9ef;">← Back</a></div>
    </body></html>
    """
    return HTMLResponse(html)

@app.get("/health")
def health():
    return JSONResponse({"ok": True, "ts": pd.Timestamp.now().isoformat()})

if __name__ == "__main__":
    import uvicorn
    print("🌐 Launching NeoLight Dashboard V2 → http://127.0.0.1:8090")
    uvicorn.run(app, host="127.0.0.1", port=8090)
PY
chmod +x "$ROOT/dashboard/dashboard_v2_live.py"

# ────────────────────────────────────────────────────────────────────
# Simple Scheduler (bash loop + nohup)
# ────────────────────────────────────────────────────────────────────
cat > "$ROOT/scripts/schedule_all.sh" <<'BASH2'
#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/neolight"
PY="$ROOT/venv/bin/python3"

# Every 4h: intelligence orchestrator (speaks + updates summaries)
while true; do
  NOW="$(date '+%F %T')"
  echo "[$NOW] 🔁 Running intelligence orchestrator..."
  nohup "$PY" "$ROOT/agents/intelligence_orchestrator.py" >> "$ROOT/logs/intel_orchestrator.log" 2>&1 || true
  # sleep 4 hours (14400s)
  sleep 14400
done
BASH2
chmod +x "$ROOT/scripts/schedule_all.sh"

echo "✅ Phase 461–520 upgrade complete."
echo "Next:"
echo "  1) Run Intelligence now:  ${PYBIN} ${ROOT}/agents/intelligence_orchestrator.py"
echo "  2) Launch Dashboard V2:   ${PYBIN} ${ROOT}/dashboard/dashboard_v2_live.py"
echo "  3) (Optional) Start scheduler (in its own tab):"
echo "     nohup bash ${ROOT}/scripts/schedule_all.sh >> ${ROOT}/logs/schedule_stdout.log 2>&1 &"

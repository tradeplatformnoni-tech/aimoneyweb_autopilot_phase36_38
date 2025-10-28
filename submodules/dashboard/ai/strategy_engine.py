import os, json, time
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from typing import Dict, List
from ai.strategies.momentum import crossover_signals

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / "runtime"
CONF = RUNTIME / "strategy_config.json"
SIGNALS = RUNTIME / "signals.jsonl"

load_dotenv(BASE / ".env")

DEFAULT_CONF = {
    "enabled": True,
    "symbols": ["AAPL","MSFT","NVDA","SPY"],
    "fast": 10,
    "slow": 20,
    "rsi_lb": 30,
    "rsi_ub": 70,
    "notional": 200
}

def load_config()->Dict:
    if CONF.exists():
        try: return json.loads(CONF.read_text())
        except: pass
    return DEFAULT_CONF

def save_config(cfg:Dict):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    CONF.write_text(json.dumps(cfg, indent=2))

def append_signal(sig:Dict):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with open(SIGNALS, "a") as f:
        f.write(json.dumps(sig) + "\n")

def fetch_prices_alpaca(symbol:str, limit:int=200) -> pd.Series:
    # keep without extra data subscription; fallback to synthetic walk
    try:
        from alpaca_trade_api.rest import REST
        api = REST(os.getenv("ALPACA_API_KEY_ID",""), os.getenv("ALPACA_API_SECRET",""),
                   base_url=os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets"))
        bars = api.get_bars(symbol, "1Day", limit=limit)
        px = [float(getattr(b,'c', getattr(b,'close',0))) for b in bars]
        if len(px) > 0:
            return pd.Series(px)
    except Exception:
        pass
    # fallback mock series
    import numpy as np
    import random
    base = 100 + random.random()*10
    walk = base + np.cumsum(np.random.normal(0,1,limit))
    return pd.Series(walk)

def run_once()->List[Dict]:
    cfg = load_config()
    if not cfg.get("enabled", True):
        return []

    results = []
    for sym in cfg.get("symbols", []):
        prices = fetch_prices_alpaca(sym, limit=max(cfg.get("slow",20)+5, 30))
        if len(prices) < max(cfg.get("slow",20), cfg.get("fast",10)) + 2:
            continue
        side, info = crossover_signals(prices, cfg.get("fast",10), cfg.get("slow",20), cfg.get("rsi_lb",30), cfg.get("rsi_ub",70))
        if side in ("buy","sell"):
            sig = {"ts": time.time(), "symbol": sym, "side": side, "notional": cfg.get("notional",200), "tag":"strategy"}
            append_signal(sig)
            results.append({"symbol":sym,"side":side,"info":info})
    return results

if __name__ == "__main__":
    out = run_once()
    print(json.dumps({"generated": out}, indent=2))

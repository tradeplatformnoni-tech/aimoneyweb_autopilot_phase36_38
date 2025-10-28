import os, json
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / "runtime"
ORDERS = RUNTIME / "orders.jsonl"

def load_env():
    return {
        "SYMBOL_WHITELIST": set(os.getenv("SYMBOL_WHITELIST","AAPL,MSFT,GOOGL,SPY,BTC,ETH,SOL,NVDA,GOLD,SILVER").split(",")),
        "MAX_NOTIONAL_PER_TRADE": float(os.getenv("MAX_NOTIONAL_PER_TRADE","1000")),
        "MAX_OPEN_POSITIONS": int(os.getenv("MAX_OPEN_POSITIONS","3")),
        "RISK_CAP": float(os.getenv("RISK_CAP","0.03")),
        "VAR_LOOKBACK_DAYS": int(os.getenv("VAR_LOOKBACK_DAYS","10")),
    }

def approve(symbol:str, side:str, notional:float, open_positions:int) -> (bool,str):
    env = load_env()
    if symbol.upper() not in env["SYMBOL_WHITELIST"]:
        return False, f"symbol {symbol} not in whitelist"
    if notional <= 0:
        return False, "notional must be > 0"
    if notional > env["MAX_NOTIONAL_PER_TRADE"]:
        return False, f"notional exceeds MAX_NOTIONAL_PER_TRADE={env['MAX_NOTIONAL_PER_TRADE']}"
    if open_positions >= env["MAX_OPEN_POSITIONS"] and side.lower()=="buy":
        return False, f"open positions >= MAX_OPEN_POSITIONS={env['MAX_OPEN_POSITIONS']}"
    # Simple VaR guard: if recent drawdowns in orders exceed RISK_CAP, block buys
    try:
        if ORDERS.exists():
            rows = [json.loads(l) for l in ORDERS.read_text().strip().splitlines() if l.strip()]
            df = pd.DataFrame(rows)
            df = df.tail(env["VAR_LOOKBACK_DAYS"])
            if "pnl" in df.columns and len(df) >= 3:
                dd = df["pnl"].sum()
                if dd < 0 and abs(dd)/max(1.0, df.get("equity_before", pd.Series([1])).iloc[-1]) > env["RISK_CAP"]:
                    if side.lower()=="buy":
                        return False, f"blocked by VaR guard (dd={dd:.2f})"
    except Exception:
        pass
    return True, "ok"

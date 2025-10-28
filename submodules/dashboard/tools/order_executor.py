import os, time, json, math
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict
from ai.risk import approve

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / "runtime"
SIGNALS = RUNTIME / "signals.jsonl"
ORDERS = RUNTIME / "orders.jsonl"
STATUS = RUNTIME / "alpaca_status.json"

load_dotenv(BASE / ".env")
PAPER = os.getenv("PAPER_TRADE","0") == "1"
ALPACA_BASE = os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets")
KEY = os.getenv("ALPACA_API_KEY_ID","")
SECRET = os.getenv("ALPACA_API_SECRET","")

def read_status()->Dict:
    try:
        if STATUS.exists():
            return json.loads(STATUS.read_text())
    except Exception: pass
    return {"equity":0,"cash":0,"status":"unknown","source":"mock"}

def append_order(obj:dict):
    with open(ORDERS, "a") as f:
        f.write(json.dumps(obj) + "\n")

def open_positions_count(api=None) -> int:
    if api is None: return 0
    try:
        pos = api.list_positions()
        return len(pos)
    except Exception:
        return 0

def get_last_price(api, symbol:str)->float:
    try:
        # Alpaca data v2 could be used; keep minimal for simplicity:
        quote = api.get_latest_trade(symbol)
        return float(getattr(quote, "price", 0) or getattr(quote, "p", 0) or 0)
    except Exception:
        return 0.0

def execute_mock(sig:dict):
    now = datetime.utcnow().isoformat()
    st = read_status()
    notional = sig.get("notional") or 0
    pnl = round((0.002 * (1 if sig["side"]=="buy" else -1)) * max(1, notional), 2)
    rec = {
        "ts": now, "symbol": sig["symbol"], "side": sig["side"],
        "mode": "mock", "status": "filled", "notional": notional,
        "qty": sig.get("qty"), "pnl": pnl, "equity_before": st.get("equity")
    }
    append_order(rec)

def execute_paper(sig:dict):
    from alpaca_trade_api.rest import REST, TimeInForce, OrderSide, AssetClass
    api = REST(KEY, SECRET, base_url=ALPACA_BASE)
    st = read_status()
    open_pos = open_positions_count(api)

    notional = float(sig.get("notional") or 0.0)
    symbol = sig["symbol"].upper()
    side = sig["side"].lower()

    ok, why = approve(symbol, side, notional, open_pos)
    if not ok:
        append_order({"ts":datetime.utcnow().isoformat(),"symbol":symbol,"side":side,"mode":"paper","status":"rejected","reason":why})
        return

    # compute qty if notional given (prefer notional orders for simplicity)
    qty = sig.get("qty")
    if notional and not qty:
        last = get_last_price(api, symbol) or 0
        if last > 0:
            qty = max(1, int(notional // last))
        else:
            qty = max(1, int(notional // 100))  # conservative fallback

    params = dict(symbol=symbol, side=side, type="market", time_in_force="day")
    if notional and hasattr(api, "submit_order"):
        params["notional"] = float(notional)
    else:
        params["qty"] = int(qty or 1)

    try:
        o = api.submit_order(**params)
        rec = {
            "ts": datetime.utcnow().isoformat(),
            "symbol": symbol, "side": side,
            "mode":"paper","status":"submitted",
            "id": getattr(o, "id", None), "notional": notional, "qty": params.get("qty"),
            "equity_before": st.get("equity")
        }
    except Exception as e:
        rec = {"ts": datetime.utcnow().isoformat(), "symbol":symbol, "side":side, "mode":"paper","status":"error","error":str(e)}
    append_order(rec)

def consume():
    """tail-like consumer that processes new signals and truncates the file to prevent growth."""
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if not SIGNALS.exists():
        SIGNALS.write_text("")

    while True:
        lines = []
        with open(SIGNALS) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                lines.append(line)

        if lines:
            # process then truncate
            SIGNALS.write_text("")
            for ln in lines:
                try:
                    sig = json.loads(ln)
                    if PAPER and KEY and SECRET:
                        execute_paper(sig)
                    else:
                        execute_mock(sig)
                except Exception as e:
                    append_order({"ts": datetime.utcnow().isoformat(), "mode":"executor", "status":"error", "error": str(e)})
        time.sleep(1.5)

if __name__ == "__main__":
    consume()

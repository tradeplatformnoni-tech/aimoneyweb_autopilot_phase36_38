import os, time, json, random, traceback
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Optional Alpaca imports – guarded to avoid crash if not installed yet
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except Exception:
    ALPACA_AVAILABLE = False

load_dotenv()

KEY = os.getenv("ALPACA_KEY_ID")
SEC = os.getenv("ALPACA_SECRET_KEY")
IS_PAPER = os.getenv("ALPACA_PAPER", "TRUE").upper() in ("TRUE","1","YES")
ENABLE_TRADES = os.getenv("PAPER_TRADING_ENABLE","0") == "1"

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
STATUS_FILE = LOG_DIR / "alpaca_status.json"
EQUITY_CSV  = LOG_DIR / "equity_history.csv"
TRADES_CSV  = LOG_DIR / "trades.csv"

def write_status(payload: dict):
    with open(STATUS_FILE, "w") as f:
        json.dump(payload, f)

def append_csv(path: Path, row: dict, header: bool):
    exists = path.exists()
    with open(path, "a") as f:
        if (not exists) and header:
            f.write(",".join(row.keys()) + "\n")
        f.write(",".join(str(v) for v in row.values()) + "\n")

def get_client():
    if not ALPACA_AVAILABLE or not KEY or not SEC:
        return None
    return TradingClient(KEY, SEC, paper=IS_PAPER)

def safe_account_snapshot(client):
    # Return a dict with at least: status, equity, cash
    try:
        if client is None:
            raise RuntimeError("No Alpaca client (missing keys or lib)")
        acct = client.get_account()
        return {
            "status": "connected",
            "equity": float(acct.equity),
            "cash": float(acct.cash),
            "buying_power": float(acct.buying_power),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "alpaca-paper"
        }
    except Exception:
        # Fallback mock snapshot
        return {
            "status": "connected",
            "equity": 100000.0 + random.uniform(-200, 200),
            "cash": 25000.0 + random.uniform(-50, 50),
            "buying_power": 50000.0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "mock"
        }

def maybe_place_tiny_trade(client):
    if client is None or not ENABLE_TRADES:
        return None
    try:
        side = random.choice([OrderSide.BUY, OrderSide.SELL])
        symbol = random.choice(["AAPL","MSFT","NVDA","SPY"])
        req = MarketOrderRequest(
            symbol=symbol,
            qty=1,
            side=side,
            time_in_force=TimeInForce.DAY
        )
        order = client.submit_order(req)
        return {
            "ts": datetime.utcnow().isoformat()+"Z",
            "symbol": symbol,
            "side": str(side),
            "qty": 1,
            "id": getattr(order, "id", "")
        }
    except Exception as e:
        return {"error": str(e), "ts": datetime.utcnow().isoformat()+"Z"}

def main():
    client = get_client()
    print("🚀 Paper trader starting…",
          "(real Alpaca paper)" if client else "(mock mode)")

    # Init CSV headers if needed
    if not EQUITY_CSV.exists():
        append_csv(EQUITY_CSV, {"timestamp":"", "equity":"", "cash":""}, header=True)
    if not TRADES_CSV.exists():
        append_csv(TRADES_CSV, {"ts":"", "symbol":"", "side":"", "qty":"", "id":""}, header=True)

    while True:
        try:
            snap = safe_account_snapshot(client)
            write_status(snap)
            append_csv(EQUITY_CSV, {
                "timestamp": snap["timestamp"],
                "equity": snap["equity"],
                "cash": snap["cash"]
            }, header=False)

            if ENABLE_TRADES:
                t = maybe_place_tiny_trade(client)
                if t:
                    append_csv(TRADES_CSV, t, header=False)

            time.sleep(4)  # heartbeat
        except KeyboardInterrupt:
            break
        except Exception:
            err = traceback.format_exc()
            write_status({"status":"error","message":err,"timestamp":datetime.utcnow().isoformat()+"Z"})
            time.sleep(4)

if __name__ == "__main__":
    main()

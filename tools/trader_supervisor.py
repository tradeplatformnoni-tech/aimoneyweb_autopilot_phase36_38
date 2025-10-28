import os, time, json, random, math
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parents[1]
RUNTIME = BASE / "runtime"
STATUS_FILE = RUNTIME / "alpaca_status.json"

load_dotenv(BASE / ".env")
PAPER = os.getenv("PAPER_TRADE","0") == "1"
ALPACA_BASE = os.getenv("ALPACA_BASE_URL","https://paper-api.alpaca.markets")
KEY = os.getenv("ALPACA_API_KEY_ID","")
SECRET = os.getenv("ALPACA_API_SECRET","")

def write(s):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(s, indent=2))

def mock_loop():
    equity = 100000.0
    cash   = 25000.0
    t0 = time.time()
    while True:
        # small random walk
        equity += random.uniform(-20, 30)
        s = {
            "status":"connected","equity":round(equity,2),"cash":round(cash,2),
            "buying_power": 50000, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source":"mock"
        }
        write(s)
        time.sleep(2)

def alpaca_loop():
    try:
        from alpaca_trade_api.rest import REST
        api = REST(KEY, SECRET, base_url=ALPACA_BASE)
    except Exception as e:
        write({"status":"error","error":f"alpaca import/connect failed: {e}","source":"paper"})
        time.sleep(3)
        return

    while True:
        try:
            acct = api.get_account()
            s = {
                "status":"connected",
                "equity": float(getattr(acct,"equity",0)),
                "cash": float(getattr(acct,"cash",0)),
                "buying_power": float(getattr(acct,"buying_power",0)),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source":"paper"
            }
            write(s)
        except Exception as e:
            write({"status":"error","error":str(e),"source":"paper"})
        time.sleep(3)

def main():
    # honor toggle flag; reload .env if user flips mode
    last_flag = None
    while True:
        flag_file = RUNTIME / "toggle.flag"
        now_flag = flag_file.read_text().strip() if flag_file.exists() else None

        if now_flag != last_flag:
            load_dotenv(BASE / ".env", override=True)
        last_flag = now_flag

        PAPER = os.getenv("PAPER_TRADE","0") == "1"
        if PAPER and os.getenv("ALPACA_API_KEY_ID") and os.getenv("ALPACA_API_SECRET"):
            write({"status":"connecting","source":"paper"})
            alpaca_loop()   # returns only on error
        else:
            write({"status":"connecting","source":"mock"})
            mock_loop()     # never returns

if __name__ == "__main__":
    main()

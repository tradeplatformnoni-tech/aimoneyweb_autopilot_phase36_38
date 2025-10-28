import os, time, json
from ai.providers.data_feed import get_bars_for_symbol
from ai.providers.fallback_provider import get_commodity_price, get_crypto_price
from tools.alert_notify import send_alert

LOG_PATH = "logs/watchdog.log"

def watchdog_loop():
    with open("config/symbols.json") as f:
        symbols = json.load(f)
    while True:
        for sym in symbols:
            bars = get_bars_for_symbol(sym, limit=5)
            if not bars:
                print(f"⚠️ Feed failure for {sym} — attempting fallback ...")
                if "/" in sym:
                    fb = get_crypto_price(sym)
                else:
                    fb = get_commodity_price(sym)
                if fb:
                    print(f"✅ Fallback success for {sym}")
                else:
                    msg = f"🚨 Feed still down for {sym} after fallback attempt"
                    print(msg)
                    send_alert(msg)
                with open(LOG_PATH, "a") as log:
                    log.write(f"{time.asctime()} — {sym} fallback attempted\n")
            else:
                print(f"✅ Feed OK for {sym}")
            time.sleep(5)
        print("🔁 Next Watchdog cycle ...")
        time.sleep(60)

if __name__ == "__main__":
    print("🧠 Starting Feed Watchdog ...")
    watchdog_loop()

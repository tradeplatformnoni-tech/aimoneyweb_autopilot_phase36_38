import os, json, requests, datetime

ALPACA_KEY=os.getenv("ALPACA_API_KEY")
ALPACA_SECRET=os.getenv("ALPACA_SECRET_KEY")
HEADERS={"APCA-API-KEY-ID":ALPACA_KEY,"APCA-API-SECRET-KEY":ALPACA_SECRET}

symbols = [
    "AAPL","MSFT","GOOGL","AMZN","NVDA","SPY",
    "BTC/USD","ETH/USD","SOL/USD","BNB/USD","XRP/USD","GOLD","SILVER"
]

valid_symbols = []
log_file = "logs/feed_diagnostics.log"
open(log_file, "w").write(f"🔍 Feed Diagnostic Run: {datetime.datetime.now()}\n\n")

def test_symbol(sym):
    url = ""
    if "/" in sym:  # crypto
        url = f"https://data.alpaca.markets/v1beta3/crypto/us/{sym.replace('/', '')}/bars?timeframe=1Hour&limit=1"
    else:  # stocks
        url = f"https://data.alpaca.markets/v2/stocks/{sym}/bars?timeframe=1Day&limit=1"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200 and "bars" in r.text:
        valid_symbols.append(sym)
        print(f"✅ {sym} feed OK")
    else:
        print(f"❌ {sym} feed unavailable ({r.status_code})")
    with open(log_file, "a") as f:
        f.write(f"{sym}: {r.status_code}\n")

for sym in symbols:
    test_symbol(sym)

if valid_symbols:
    with open("config/symbols.json", "w") as f:
        json.dump(valid_symbols, f, indent=2)
    print(f"\n✅ Feed Diagnostic Complete — {len(valid_symbols)} symbols validated.")
    print("🧩 Updated config/symbols.json with valid symbols:")
    print(valid_symbols)
else:
    print("❗ No valid symbols detected; check API tier or permissions.")

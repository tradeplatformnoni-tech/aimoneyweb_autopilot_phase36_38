import json, random, requests, os

def get_bars_from_alpaca(symbol, limit=60, timeframe="1Hour"):
    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?timeframe={timeframe}&limit={limit}"
    headers = {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"❌ Alpaca error {r.status_code} for {symbol}")
            return []

        # Some responses might not include 'bars' key or might have null
        response_json = r.json()
        data = response_json.get("bars", [])
        if not data:
            print(f"⚠️ No bars found for {symbol}")
            return []

        bars = []
        for b in data or []:
            try:
                bars.append({
                    "t": b.get("t"),
                    "o": b.get("o"),
                    "h": b.get("h"),
                    "l": b.get("l"),
                    "c": b.get("c")
                })
            except Exception as e:
                print(f"⚠️ Skipping malformed bar for {symbol}: {e}")
                continue

        print(f"✅ {symbol}: {len(bars)} bars")
        return bars

    except Exception as e:
        print(f"💥 Error fetching {symbol}: {e}")
        return []

# ✅ Backward-compatible alias
def get_bars_for_symbol(symbol, limit=60, timeframe="1Hour"):
    return get_bars_from_alpaca(symbol, limit, timeframe)

def get_multi_asset_data():
    with open("config/symbols.json") as f:
        symbols = json.load(f)
    sym = random.choice(symbols)
    bars = get_bars_from_alpaca(sym)
    return sym, bars


import requests, datetime, random

def get_commodity_price(symbol):
    try:
        mapping = {"GOLD": "XAU", "SILVER": "XAG"}
        code = mapping.get(symbol)
        if not code:
            return []

        # --- Primary Source: Metals.live ---
        try:
            url = "https://api.metals.live/v1/spot"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                price_map = {k: v for item in data for k, v in item.items()}
                price = price_map.get(code)
                if price:
                    print(f"🏅 Fetched {symbol} = {price} USD from Metals.live")
                    return [{
                        "t": datetime.datetime.utcnow().isoformat(),
                        "o": price, "h": price, "l": price, "c": price
                    }]
            else:
                print(f"⚠️ Metals.live error {r.status_code} for {symbol}")

        except Exception as e:
            print(f"⚠️ Metals.live unavailable: {e}")

        # --- Backup Source: TradingEconomics ---
        url = f"https://api.tradingeconomics.com/markets/{code}/USD?c=guest:guest"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, list) and "Close" in data[0]:
                price = data[0]["Close"]
                print(f"💰 Fetched {symbol} = {price} USD from TradingEconomics")
                return [{
                    "t": datetime.datetime.utcnow().isoformat(),
                    "o": price, "h": price, "l": price, "c": price
                }]
            else:
                print(f"⚠️ No valid price in TradingEconomics for {symbol}")

        print(f"❌ No valid commodity data for {symbol}")
        return []

    except Exception as e:
        print(f"⚠️ Commodity fallback failed for {symbol}: {e}")
        return []

# --- CoinGecko for Crypto Fallback ---
def get_crypto_price(symbol):
    cg_map = {
        "BTC/USD": "bitcoin",
        "ETH/USD": "ethereum",
        "SOL/USD": "solana"
    }
    if symbol not in cg_map:
        return None
    coin = cg_map[symbol]
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=1"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()["prices"]
        bars = []
        for t, c in data[-60:]:
            bars.append({
                "t": datetime.datetime.fromtimestamp(t/1000).isoformat(),
                "o": c, "h": c, "l": c, "c": c
            })
        print(f"💰 Fetched {len(bars)} bars for {symbol} from CoinGecko")
        return bars
    except Exception as e:
        print(f"⚠️ CoinGecko fallback failed for {symbol}: {e}")
        return []

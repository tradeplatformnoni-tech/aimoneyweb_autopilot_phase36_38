import os, requests, datetime

ALPACA_KEY = os.getenv("ALPACA_API_KEY","")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY","")
# Alpaca crypto data base (v1beta3)
ALPACA_CRYPTO_BASE = os.getenv("ALPACA_CRYPTO_BASE","https://data.alpaca.markets/v1beta3/crypto/us")

HEADERS = {"APCA-API-KEY-ID": ALPACA_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET}

# Basic symbol -> coingecko id map
COINGECKO_IDS = {
    "BTC/USD": "bitcoin",
    "ETH/USD": "ethereum",
    "SOL/USD": "solana",
    "BNB/USD": "binancecoin",
    "XRP/USD": "ripple",
    "USDT/USD": "tether"
}

def _alpaca_bars(symbol, limit=60, interval="1Hour"):
    sym = symbol.replace("/","")  # BTC/USD -> BTCUSD
    url = f"{ALPACA_CRYPTO_BASE}/{sym}/bars?timeframe={interval}&limit={limit}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return []
    data = r.json()
    bars = data.get("bars", [])
    out = []
    for b in bars:
        # Alpaca crypto bar fields: t (ISO), o,h,l,c,v,n, vw, etc.
        out.append({
            "t": b.get("t"),
            "o": float(b.get("o",0)),
            "h": float(b.get("h",0)),
            "l": float(b.get("l",0)),
            "c": float(b.get("c",0))
        })
    return out

def _coingecko_bars(symbol, limit=60, interval="hourly"):
    cg_id = COINGECKO_IDS.get(symbol)
    if not cg_id: 
        return []
    # 2 days gives enough hourly points; you can tweak
    url = f"https://api.coingecko.com/api/v3/coins/{cg_id}/market_chart?vs_currency=usd&days=2&interval={interval}"
    r = requests.get(url, timeout=20)
    if r.status_code != 200:
        return []
    data = r.json()
    prices = data.get("prices", [])
    # prices: [ [timestamp_ms, price], ... ]
    out = []
    # Build OHLC from adjacent points (approx) since CG gives price series
    # For simplicity, we’ll treat each entry as a 'close' and synthesize small OHLC
    for i, p in enumerate(prices[-limit:]):
        ts_ms, close = p
        close = float(close)
        o = close
        h = close
        l = close
        # If we have previous point, create tiny range
        if i > 0:
            prev = float(prices[-limit:][i-1][1])
            o = prev
            h = max(prev, close)
            l = min(prev, close)
        out.append({
            "t": datetime.datetime.utcfromtimestamp(ts_ms/1000.0).isoformat(),
            "o": o, "h": h, "l": l, "c": close
        })
    return out

def get_ohlc(symbol, limit=60, interval="1Hour"):
    """
    Try Alpaca crypto first; if no bars/404, fall back to CoinGecko (no key required).
    """
    # First try Alpaca (if keys present)
    if ALPACA_KEY and ALPACA_SECRET:
        bars = _alpaca_bars(symbol, limit=limit, interval=interval)
        if bars:
            return bars
    # Fallback: CoinGecko
    return _coingecko_bars(symbol, limit=limit, interval="hourly")

import os, json, time, requests
from datetime import datetime, timedelta

CACHE_PATH = "logs/commodity_cache.json"

def _read_cache():
    try:
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"XAU": None, "XAG": None, "updated": None, "source": None}

def _write_cache(xau, xag, source):
    data = {"XAU": xau, "XAG": xag, "source": source, "updated": datetime.utcnow().isoformat()}
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return data

class CommodityProvider:
    """
    Returns spot-like XAU/XAG with multi-source fallback and caching.
    Prefers:
      1) MetalpriceAPI (if METALPRICEAPI_KEY set)
      2) Gold-API.com (no key) — may be rate-limited
      3) CoinGecko (PAXG + 'silver' token)
      4) TradingEconomics (guest)
      5) Alpaca GLD/SLV ETF proxy (stocks) if Alpaca keys are present
      6) Cache (last good)
    """
    def __init__(self, max_age_minutes=180, allow_stale_hours=30):
        self.key = os.getenv("METALPRICEAPI_KEY", "").strip()
        self.max_age = timedelta(minutes=max_age_minutes)
        self.allow_stale = timedelta(hours=allow_stale_hours)

    def get_latest_prices(self):
        # 0) Fresh cache usable?
        cache = _read_cache()
        if cache["updated"]:
            age = datetime.utcnow() - datetime.fromisoformat(cache["updated"])
            if age <= self.max_age and cache["XAU"] and cache["XAG"]:
                print(f"📦 Using cached XAU/XAG (age={age}).")
                return {**cache, "source": f"Cache({cache.get('source')})"}

        # 1) MetalpriceAPI (live or 1-day delayed on free plan)
        if self.key:
            try:
                url = f"https://api.metalpriceapi.com/v1/latest?api_key={self.key}&base=USD&currencies=XAU,XAG"
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    rates = r.json().get("rates", {})
                    xau, xag = rates.get("XAU"), rates.get("XAG")
                    if xau and xag:
                        print(f"💰 MetalpriceAPI OK: XAU={xau}, XAG={xag}")
                        return _write_cache(xau, xag, "MetalpriceAPI")
            except Exception as e:
                print(f"⚠️ MetalpriceAPI error: {e}")

        # 2) Gold-API.com
        try:
            r = requests.get("https://api.gold-api.com/price", timeout=10)
            if r.status_code == 200:
                data = r.json()
                xau, xag = data.get("XAU"), data.get("XAG")
                if xau and xag:
                    print(f"🏅 Gold-API OK: XAU={xau}, XAG={xag}")
                    return _write_cache(xau, xag, "GoldAPI")
        except Exception as e:
            print(f"⚠️ Gold-API error: {e}")

        # 3) CoinGecko — PAX Gold + 'silver' market proxy
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=pax-gold,silver&vs_currencies=usd", timeout=10)
            if r.status_code == 200:
                j = r.json()
                xau = j.get("pax-gold", {}).get("usd")
                xag = j.get("silver", {}).get("usd")
                if xau and xag:
                    print(f"🪙 CoinGecko OK: XAU~PAXG={xau}, XAG={xag}")
                    return _write_cache(xau, xag, "CoinGecko")
        except Exception as e:
            print(f"⚠️ CoinGecko error: {e}")

        # 4) TradingEconomics guest
        try:
            # XAU/USD and XAG/USD, guest creds
            for code in [("XAU","XAU/USD"), ("XAG","XAG/USD")]:
                url = f"https://api.tradingeconomics.com/markets/{code[1]}?c=guest:guest"
                rr = requests.get(url, timeout=10)
                if rr.status_code != 200: 
                    raise Exception(f"TE HTTP {rr.status_code}")
                arr = rr.json()
                if not arr or "Close" not in arr[0]: 
                    raise Exception("TE no Close")
                if code[0] == "XAU": xau = arr[0]["Close"]
                if code[0] == "XAG": xag = arr[0]["Close"]
            if xau and xag:
                print(f"📊 TradingEconomics OK: XAU={xau}, XAG={xag}")
                return _write_cache(xau, xag, "TradingEconomics")
        except Exception as e:
            print(f"⚠️ TradingEconomics error: {e}")

        # 5) Alpaca GLD/SLV ETF proxy (if keys exist)
        try:
            if os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY"):
                from ai.providers.alpaca_provider import get_ohlc
                gld = get_ohlc("GLD", timeframe="1Day", limit=1)
                slv = get_ohlc("SLV", timeframe="1Day", limit=1)
                def last_close(bars): 
                    if isinstance(bars, list) and bars: 
                        b = bars[-1]
                        # alpaca v2 returns dicts with 'c' close or keyed fields
                        return float(b.get("c") or b.get("close", 0))
                    return None
                xau = last_close(gld)
                xag = last_close(slv)
                if xau and xag:
                    print(f"🟡 GLD/SLV proxy OK: GLD={xau}, SLV={xag}")
                    return _write_cache(xau, xag, "GLD/SLV Proxy")
        except Exception as e:
            print(f"⚠️ GLD/SLV proxy error: {e}")

        # 6) Use stale cache if allowed
        if cache["updated"]:
            age = datetime.utcnow() - datetime.fromisoformat(cache["updated"])
            if age <= self.allow_stale and (cache["XAU"] or cache["XAG"]):
                print(f"♻️ Using STALE cache (age={age}) due to upstream failures.")
                return {**cache, "source": f"StaleCache({cache.get('source')})"}

        print("❌ All commodity sources failed and cache unusable.")
        return {"XAU": None, "XAG": None, "source": None, "updated": None}

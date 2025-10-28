import requests
# Public Candlestick endpoint (no key needed for data)
API_URL="https://api.crypto.com/v2/public/get-candlestick"
def get_ohlc(symbol="BTC_USDT", interval="5m", limit=180):
    r=requests.get(API_URL,params={"instrument_name":symbol,"timeframe":interval},timeout=10)
    if not r.ok: return None
    data=r.json().get("result",{}).get("data",[])
    out=[]
    for d in data[-limit:]:
        out.append({
            "t": d.get("t"),
            "open": float(d.get("o")), "high": float(d.get("h")),
            "low": float(d.get("l")), "close": float(d.get("c")),
            "volume": float(d.get("v",0))
        })
    return out

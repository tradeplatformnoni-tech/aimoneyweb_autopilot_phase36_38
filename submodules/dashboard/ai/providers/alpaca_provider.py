import os, requests
ALPACA_KEY=os.getenv("ALPACA_API_KEY","")
ALPACA_SECRET=os.getenv("ALPACA_SECRET_KEY","")
DATA_BASE=os.getenv("ALPACA_DATA_BASE","https://data.alpaca.markets/v2")
HEADERS={"APCA-API-KEY-ID":ALPACA_KEY,"APCA-API-SECRET-KEY":ALPACA_SECRET}

def get_ohlc(symbol, timeframe="1Day", limit=60):
    # Stocks/ETFs/Commodities: /stocks/{symbol}/bars
    url=f"{DATA_BASE}/stocks/{symbol}/bars?timeframe={timeframe}&limit={limit}"
    r=requests.get(url,headers=HEADERS,timeout=20)
    if r.status_code!=200: return []
    data=r.json()
    return data.get("bars",[])

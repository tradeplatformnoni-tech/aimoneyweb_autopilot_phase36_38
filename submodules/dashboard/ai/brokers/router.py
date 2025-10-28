import os, time, random
from dotenv import load_dotenv; load_dotenv()
BROKER=os.getenv("BROKER","ALPACA").upper()
ALPACA_MODE=os.getenv("ALPACA_MODE","paper")
# Lazy imports to keep env light
def _alpaca_api():
    import alpaca_trade_api as tradeapi, os
    base = "https://paper-api.alpaca.markets" if ALPACA_MODE=="paper" else "https://api.alpaca.markets"
    return tradeapi.REST(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), base)
def _binance():
    import ccxt, os
    key=os.getenv("BINANCE_API_KEY"); sec=os.getenv("BINANCE_SECRET_KEY")
    ex=ccxt.binance({'apiKey':key,'secret':sec,'enableRateLimit':True})
    return ex

def account_equity_cash():
    try:
        if BROKER=="ALPACA":
            api=_alpaca_api(); a=api.get_account()
            return float(a.equity), float(a.cash)
        elif BROKER=="BINANCE":
            ex=_binance(); bal=ex.fetch_balance()
            eq = bal.get('total',{}).get('USDT', 100000.0)
            ca = bal.get('free',{}).get('USDT', 25000.0)
            return float(eq), float(ca)
        else: # MOCK
            return 100000.0+random.uniform(-400,400), 25000.0+random.uniform(-200,200)
    except Exception:
        return 100000.0+random.uniform(-400,400), 25000.0+random.uniform(-200,200)

def submit_market(symbol, side, qty):
    try:
        if BROKER=="ALPACA":
            api=_alpaca_api()
            o=api.submit_order(symbol=symbol,qty=int(qty),side=side,type="market",time_in_force="gtc")
            return {"id":o.id,"broker":"ALPACA"}
        elif BROKER=="BINANCE":
            ex=_binance()
            # market orders require lot sizes; treat qty as notional in USDT for simple demo
            o=ex.create_order(symbol=f"{symbol}/USDT", type="market", side=side, amount=max(float(qty)/200.0,0.001))
            return {"id":o.get('id','binance'),"broker":"BINANCE"}
        else:
            return {"id":f"mock-{int(time.time())}","broker":"MOCK"}
    except Exception as e:
        return {"error":str(e),"broker":BROKER}

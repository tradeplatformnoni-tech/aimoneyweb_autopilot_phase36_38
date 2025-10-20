import os, time, alpaca_trade_api as tradeapi
from dotenv import load_dotenv
load_dotenv()

def get_api():
    key=os.getenv("ALPACA_API_KEY")
    secret=os.getenv("ALPACA_SECRET_KEY")
    mode=os.getenv("ALPACA_MODE","paper")
    base="https://paper-api.alpaca.markets" if mode=="paper" else "https://api.alpaca.markets"
    return tradeapi.REST(key,secret,base)

def place_trade(signal,size):
    api=get_api()
    side="buy" if signal>0 else "sell"
    symbol="AAPL"
    qty=max(int(size/200),1)
    try:
        order=api.submit_order(symbol=symbol,qty=qty,side=side,type="market",time_in_force="gtc")
        print(f"📈 Order Placed: {side.upper()} {qty} {symbol}")
        return order.id
    except Exception as e:
        print("⚠️ Trade failed:",e)
        return None

def get_positions():
    api=get_api()
    try:return [p._raw for p in api.list_positions()]
    except: return []

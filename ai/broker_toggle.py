import os,alpaca_trade_api as tradeapi
from dotenv import load_dotenv
load_dotenv()
def get_api():
    key=os.getenv("ALPACA_API_KEY");secret=os.getenv("ALPACA_SECRET_KEY")
    paper=os.getenv("ALPACA_MODE","paper")
    base="https://paper-api.alpaca.markets" if paper=="paper" else "https://api.alpaca.markets"
    return tradeapi.REST(key,secret,base)
def get_account():
    api=get_api()
    a=api.get_account()
    return {"equity":float(a.equity),"cash":float(a.cash),"status":a.status}

import sqlite3,time,os,pandas as pd
DB="db/trades.db"
os.makedirs("db",exist_ok=True)

def log_trade(symbol,side,qty,price,equity,signal,drawdown):
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trades(
        ts TEXT, symbol TEXT, side TEXT, qty INT, price REAL, equity REAL,
        signal REAL, drawdown REAL)""")
    c.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?)",
              (time.strftime("%Y-%m-%d %H:%M:%S"),symbol,side,qty,price,equity,signal,drawdown))
    conn.commit();conn.close()

def analyze():
    conn=sqlite3.connect(DB)
    df=pd.read_sql("SELECT * FROM trades",conn)
    conn.close()
    if len(df)==0:return {"count":0,"avg_pnl":0}
    df["pnl"]=df["price"].diff().fillna(0)
    return {
        "count":len(df),
        "avg_pnl":round(df["pnl"].mean(),2),
        "last_signal":round(df["signal"].iloc[-1],3)
    }

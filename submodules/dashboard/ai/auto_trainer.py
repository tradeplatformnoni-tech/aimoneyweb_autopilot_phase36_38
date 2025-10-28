import os, time, sqlite3, pandas as pd, numpy as np, joblib
os.makedirs("models",exist_ok=True)
DB="db/trades.db"
def data():
    if not os.path.exists(DB): return None
    c=sqlite3.connect(DB); df=pd.read_sql("SELECT * FROM trades",c); c.close()
    return df if not df.empty else None
def train():
    df=data()
    if df is None: print("no data yet"); return
    # simple linear metric on (price changes vs signal)
    pnl=df["price"].diff().fillna(0)
    sig=df["signal"].fillna(0)
    if len(sig)<5: return
    w=float(np.dot(pnl, sig)/ (np.linalg.norm(sig)+1e-6))
    score=float(pnl.mean())
    model={"weights":[w], "score":score, "ts":time.time()}
    path=f"models/model_{int(model['ts'])}.pkl"
    joblib.dump(model, path); joblib.dump(model, "models/active_model.pkl")
    print("🧠 model saved:", path, "score:",score)
if __name__=="__main__":
    while True:
        train(); time.sleep(60*60*24)

import sqlite3, numpy as np, os, time
DB="learning_data.db"
os.makedirs("ai",exist_ok=True)
def ensure_db():
    con=sqlite3.connect(DB)
    cur=con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS trades(ts TEXT, equity REAL, pnl REAL, risk REAL)")
    con.commit();con.close()
def log_trade(equity,pnl,risk):
    con=sqlite3.connect(DB);cur=con.cursor()
    cur.execute("INSERT INTO trades VALUES(datetime('now'),?,?,?)",(equity,pnl,risk))
    con.commit();con.close()
def learn():
    con=sqlite3.connect(DB);cur=con.cursor()
    cur.execute("SELECT pnl,risk FROM trades ORDER BY ts DESC LIMIT 50")
    rows=cur.fetchall();con.close()
    if not rows:return 0
    pnl=np.array([r[0] for r in rows]);risk=np.array([r[1] for r in rows])+1e-9
    score=float(np.mean(pnl/risk))
    open("ai/policy.txt","w").write(str(score))
    return score
if __name__=="__main__":
    ensure_db()
    while True:
        s=learn()
        print(f"🧩 Learned adaptive score: {s:.4f}")
        time.sleep(10)

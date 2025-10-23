import sqlite3,time,json
def replay(db="db/fills.db"):
    con=sqlite3.connect(db); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS fills(ts TEXT, broker TEXT, order_id TEXT, symbol TEXT, side TEXT, qty REAL, price REAL)")
    rows=c.execute("SELECT * FROM fills ORDER BY ts ASC").fetchall()
    con.close()
    for r in rows:
        print(f"⏪ {r[0]} {r[4]} {r[3]} @{r[6]}")
        time.sleep(0.2)

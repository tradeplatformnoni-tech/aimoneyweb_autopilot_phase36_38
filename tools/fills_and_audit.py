import os, sqlite3, time
os.makedirs("db",exist_ok=True)
FILLS="db/fills.db"; AUDIT="db/audit.db"

def log_fill(data:dict):
    con=sqlite3.connect(FILLS); c=con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS fills(
        ts TEXT, broker TEXT, order_id TEXT, symbol TEXT, side TEXT, qty REAL, price REAL)""")
    c.execute("INSERT INTO fills VALUES (?,?,?,?,?,?,?)",(
        time.strftime("%Y-%m-%d %H:%M:%S"),
        data.get("broker","?"), data.get("order_id","?"), data.get("symbol","?"),
        data.get("side","?"), float(data.get("qty",0)), float(data.get("price",0))
    ))
    con.commit(); con.close()

def list_fills(limit=50):
    con=sqlite3.connect(FILLS); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS fills(ts TEXT, broker TEXT, order_id TEXT, symbol TEXT, side TEXT, qty REAL, price REAL)")
    rows=c.execute("SELECT * FROM fills ORDER BY ts DESC LIMIT ?",(limit,)).fetchall()
    con.close()
    return [{"ts":r[0],"broker":r[1],"order_id":r[2],"symbol":r[3],"side":r[4],"qty":r[5],"price":r[6]} for r in rows]

def audit_event(kind:str, detail:str):
    con=sqlite3.connect(AUDIT); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS audit(ts TEXT, kind TEXT, detail TEXT)")
    c.execute("INSERT INTO audit VALUES (?,?,?)",(time.strftime("%Y-%m-%d %H:%M:%S"), kind, detail))
    con.commit(); con.close()

def list_audit(limit=100):
    con=sqlite3.connect(AUDIT); c=con.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS audit(ts TEXT, kind TEXT, detail TEXT)")
    rows=c.execute("SELECT * FROM audit ORDER BY ts DESC LIMIT ?",(limit,)).fetchall()
    con.close()
    return [{"ts":r[0],"kind":r[1],"detail":r[2]} for r in rows]

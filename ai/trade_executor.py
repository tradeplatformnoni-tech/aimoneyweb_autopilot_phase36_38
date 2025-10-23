import random, json, os, datetime

with open("config/symbols.json") as f:
    SYMBOLS=json.load(f)

def execute_trades(signals):
    orders=[]
    for s in signals:
        if s["signal"] in ["BUY","SELL"]:
            orders.append({
                "timestamp":datetime.datetime.now().isoformat(),
                "symbol":s["symbol"],
                "action":s["signal"],
                "price":s["price"],
                "status":"executed"
            })
    open("logs/orders.jsonl","a").write("\n".join([json.dumps(o) for o in orders])+"\n")
    return orders

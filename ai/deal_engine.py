"""
ai/deal_engine.py
Offline mock negotiation engine; logs proposals and results.
"""
import json, os, datetime, random
LOG="logs/deal_log.json"
os.makedirs("logs", exist_ok=True)

def propose(parties:list, asset:str, price:float):
    deal={"timestamp":datetime.datetime.now().isoformat(),
          "parties":parties,"asset":asset,"price":price,
          "accepted":random.choice([True,False])}
    data=[]
    if os.path.exists(LOG): data=json.load(open(LOG))
    data.append(deal)
    json.dump(data,open(LOG,"w"),indent=2)
    return deal

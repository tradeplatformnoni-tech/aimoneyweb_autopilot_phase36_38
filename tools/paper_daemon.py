#!/usr/bin/env python3
import time, json, random, requests

def mock_price(base):
    return base + random.uniform(-1,1)

symbols = ["AAPL","TSLA","MSFT"]
while True:
    for sym in symbols:
        price = mock_price(100)
        action = random.choice(["buy","sell"])
        payload={"symbol":sym,"price":price,"action":action,"qty":1}
        try:
            r = requests.post("http://127.0.0.1:8000/api/paper_trade",json=payload,timeout=3)
            print(r.json())
        except Exception as e:
            print("Error:", e)
    time.sleep(5)

import time
import random

print("🚀 AI Paper Trader starting...")
while True:
    price = round(random.uniform(100, 200), 2)
    print(f"[MOCK TRADE] Bought at $ {price}")
    time.sleep(5)

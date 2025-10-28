import time
import random

def run_paper_trading_loop():
    print("📈 Paper trading loop started...")
    balance = 10000
    for i in range(5):
        price = random.uniform(90, 110)
        balance += random.uniform(-50, 50)
        print(f"🔁 Trade {i+1} | Price: ${price:.2f} | Balance: ${balance:.2f}")
        time.sleep(1)
    print("✅ Paper trading loop complete.")

if __name__ == "__main__":
    run_paper_trading_loop()

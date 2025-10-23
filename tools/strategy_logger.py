import json, random, time, os, datetime

runtime_dir = "runtime"
os.makedirs(runtime_dir, exist_ok=True)
log_file = os.path.join(runtime_dir, "signals.jsonl")

signals = ["BUY", "SELL", "HOLD"]

print("🧩 Strategy Logger started... Press CTRL+C to stop.")
while True:
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "strategy": random.choice(["momentum", "crossover", "mean_reversion"]),
        "signal": random.choice(signals),
        "confidence": round(random.uniform(0.5, 0.99), 2)
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print("💾 Logged:", entry)
    time.sleep(5)

import json
import random

def auto_tune():
    with open("config/optimizer.json", "w") as f:
        json.dump({
            "sharpe_threshold": round(random.uniform(1.0, 2.5), 2),
            "drawdown_limit": round(random.uniform(0.1, 0.3), 2)
        }, f, indent=2)

if __name__ == "__main__":
    auto_tune()

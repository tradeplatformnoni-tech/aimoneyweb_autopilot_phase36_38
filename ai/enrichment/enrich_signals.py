"""
Adds confidence/volatility metrics to signals before logging.
Simulation-safe; no external data pulled.
"""
import json, math, random, datetime, pathlib
RUNTIME = pathlib.Path("runtime"); OUT = RUNTIME/"signals_enriched.jsonl"

def enrich(signal: dict):
    base = signal.copy()
    closes = [random.uniform(90,110) for _ in range(20)]
    volatility = round(float(max(closes)-min(closes))/sum(closes)*len(closes)*100,2)
    confidence = round(100 - volatility + random.uniform(-5,5),2)
    base.update({
        "volatility": volatility,
        "confidence": confidence,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })
    OUT.open("a").write(json.dumps(base)+"\n")
    return base

if __name__ == "__main__":
    s = {"strategy":"demo","symbol":"SPY","signal":"BUY"}
    print(enrich(s))

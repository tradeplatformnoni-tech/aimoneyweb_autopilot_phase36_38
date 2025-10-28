"""
Analyzes experience memory to identify best-performing strategy configs.
"""
import json, pathlib, random
RUNTIME=pathlib.Path("runtime")
MEMORY=RUNTIME/"experience_log.jsonl"
BEST=RUNTIME/"strategy_best.json"

def rebuild():
    if not MEMORY.exists(): return {"status":"no_memory"}
    data=[json.loads(l) for l in MEMORY.open()]
    # simulate scoring
    scores={"momentum":random.uniform(-1,1),"mean_reversion":random.uniform(-1,1),"crossover":random.uniform(-1,1)}
    best=max(scores,key=scores.get)
    result={"best_strategy":best,"scores":scores}
    json.dump(result,open(BEST,"w"),indent=2)
    return result
if __name__=="__main__":
    print(rebuild())

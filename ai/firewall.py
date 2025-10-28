import json, os
RULES = {"max_drawdown":0.3, "min_sharpe":1.0}
LOG = "logs/firewall_log.json"

def validate(strategy):
    ok = strategy.get("drawdown",0)<=RULES["max_drawdown"] \
         and strategy.get("sharpe",0)>=RULES["min_sharpe"]
    rec = {"strategy":strategy,"valid":ok}
    data=[]
    if os.path.exists(LOG): data=json.load(open(LOG))
    data.append(rec)
    json.dump(data, open(LOG,"w"), indent=2)
    return ok

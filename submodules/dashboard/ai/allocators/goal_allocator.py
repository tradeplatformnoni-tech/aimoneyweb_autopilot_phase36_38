"""
Adjusts strategy weights based on progress toward wealth goals.
"""
import json, pathlib
CFG=pathlib.Path("runtime/goal_config.json")
WFILE=pathlib.Path("runtime/portfolio_weights.json")

def adapt():
    if not CFG.exists() or not WFILE.exists(): return
    cfg=json.load(open(CFG)); w=json.load(open(WFILE))
    cur=cfg.get("current_equity",100000); tgt=cfg.get("target_milestones",{}).get("2_years",1000000)
    ratio=min(cur/tgt,1.0)
    w["momentum"]=round(0.3+0.2*ratio,2)
    w["mean_reversion"]=round(0.4-0.2*ratio,2)
    w["crossover"]=round(1-w["momentum"]-w["mean_reversion"],2)
    json.dump(w,open(WFILE,"w"),indent=2)
    return w

if __name__=="__main__":
    print(adapt())

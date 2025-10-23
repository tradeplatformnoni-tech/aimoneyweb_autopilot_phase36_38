import json, datetime, os
CFG="runtime/goal_config.json"
def update_progress(current_equity: float):
    cfg=json.load(open(CFG)) if os.path.exists(CFG) else {"target_milestones":{}}
    out={"equity":current_equity,"report":[]}
    for yr, tgt in cfg.get("target_milestones",{}).items():
        pct=0 if tgt==0 else round((current_equity/float(tgt))*100,2)
        out["report"].append({"year":yr,"target":float(tgt),"progress":pct})
    out["timestamp"]=datetime.datetime.utcnow().isoformat()
    return out

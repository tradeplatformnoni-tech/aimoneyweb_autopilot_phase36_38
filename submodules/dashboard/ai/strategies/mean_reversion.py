DEFAULT_CONFIG = {"window": 20, "z_entry": 1.0}
def mean(a): return sum(a)/len(a)
def generate_signal(history, cfg=DEFAULT_CONFIG):
    w = cfg.get("window",20)
    if len(history) < w: return {"signal":"HOLD","confidence":0.5,"meta":{"reason":"not_enough"}}
    closes = [x["close"] for x in history[-w:]]
    m = mean(closes); var = sum((c-m)**2 for c in closes)/len(closes); std = var**0.5 if var>0 else 0
    z = 0 if std==0 else (history[-1]["close"]-m)/std
    if z > cfg.get("z_entry",1.0): return {"signal":"SELL","confidence":min(0.6+abs(z)/3,0.95),"meta":{"z":z,"mean":m}}
    if z < -cfg.get("z_entry",1.0): return {"signal":"BUY","confidence":min(0.6+abs(z)/3,0.95),"meta":{"z":z,"mean":m}}
    return {"signal":"HOLD","confidence":0.5,"meta":{"z":z,"mean":m}}

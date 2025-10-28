DEFAULT_CONFIG = {"lookback": 10, "threshold": 0.002}
def generate_signal(history, cfg=DEFAULT_CONFIG):
    n = cfg.get("lookback", 10)
    if len(history) < n+1: return {"signal":"HOLD","confidence":0.5,"meta":{"reason":"not_enough"}}
    c0 = history[-1]["close"]; cN = history[-1-n]["close"]
    r = (c0-cN)/cN
    if r > cfg.get("threshold",0.002): return {"signal":"BUY","confidence":min(0.5+r*40,0.95),"meta":{"r":r}}
    if r < -cfg.get("threshold",0.002): return {"signal":"SELL","confidence":min(0.5+abs(r)*40,0.95),"meta":{"r":r}}
    return {"signal":"HOLD","confidence":0.55,"meta":{"r":r}}

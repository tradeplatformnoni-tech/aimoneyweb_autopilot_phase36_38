DEFAULT_CONFIG = {"fast": 5, "slow": 20}
def sma(series, n): 
    if len(series) < n: return None
    return sum(x["close"] for x in series[-n:]) / n
def generate_signal(history, cfg=DEFAULT_CONFIG):
    f = cfg.get("fast",5); s = cfg.get("slow",20)
    if len(history) < s+1: return {"signal":"HOLD","confidence":0.5,"meta":{"reason":"not_enough"}}
    fast_prev = sum(x["close"] for x in history[-(f+1):-1]) / f
    slow_prev = sum(x["close"] for x in history[-(s+1):-1]) / s
    fast_now  = sma(history, f); slow_now = sma(history, s)
    if fast_prev <= slow_prev and fast_now > slow_now: return {"signal":"BUY","confidence":0.8,"meta":{"fast":fast_now,"slow":slow_now}}
    if fast_prev >= slow_prev and fast_now < slow_now: return {"signal":"SELL","confidence":0.8,"meta":{"fast":fast_now,"slow":slow_now}}
    return {"signal":"HOLD","confidence":0.55,"meta":{"fast":fast_now,"slow":slow_now}}

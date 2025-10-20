def is_canary_good(metrics):
    # accept if recent pnl positive and latency reasonable
    return (metrics.get("pnl",0)>0) and (metrics.get("latency_ms",100)<150)

import json, numpy as np, datetime, pathlib, random
RUNTIME = pathlib.Path("runtime"); OUT = RUNTIME/"risk_metrics.json"

def compute_from_equity_series(eq):
    ret = np.diff(eq)/eq[:-1] if len(eq)>1 else np.array([0.0])
    volatility = float(np.std(ret)*np.sqrt(252)) if ret.size>1 else 0.0
    sharpe = float((np.mean(ret)/(np.std(ret)+1e-9))*np.sqrt(252)) if ret.size>2 else 0.0
    var95 = float(np.percentile(ret,5)) if ret.size>1 else 0.0
    drawdown = float(((eq - np.maximum.accumulate(eq))/np.maximum.accumulate(eq)).min()) if len(eq)>0 else 0.0
    return volatility, sharpe, var95, drawdown

def compute():
    # Simulation-safe equity curve (replace with portfolio history later)
    eq = 100000 + np.cumsum(np.random.normal(0, 120, 300))
    vol, sharpe, var95, dd = compute_from_equity_series(eq)
    metrics = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "volatility": vol, "sharpe": sharpe,
        "var_95": var95, "max_drawdown": dd
    }
    json.dump(metrics, open(OUT,"w"), indent=2)
    return metrics

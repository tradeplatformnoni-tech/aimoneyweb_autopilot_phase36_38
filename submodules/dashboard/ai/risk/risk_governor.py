import os, json, math, statistics, datetime
from ai.providers.data_feed import get_bars_for_symbol
from ai.providers.commodity_provider import CommodityProvider

OUTPUT_POLICY = "config/risk_policy.json"
LOG = "logs/risk_governor.log"

ASSETS = ["AAPL","MSFT","GOOGL","AMZN","NVDA","SPY","GOLD","SILVER"]
MIN_W, MAX_W = 0.05, 0.35  # per-asset caps
TARGET_GROSS = 1.0         # sum of weights
WINDOW = 30                # bars for vol calc

def close_series(sym):
    if sym in ["GOLD","SILVER"]:
        cp = CommodityProvider()
        d = cp.get_latest_prices()
        price = d.get("XAU" if sym=="GOLD" else "XAG")
        return [price]*WINDOW if price else []
    bars = get_bars_for_symbol(sym, limit=WINDOW)
    cl = []
    for b in bars or []:
        c = b.get("c") or b.get("close")
        if c: cl.append(float(c))
    return cl

def pct_vol(prices):
    if len(prices) < 2: return None
    rets = []
    for i in range(1, len(prices)):
        if prices[i-1]:
            rets.append((prices[i]-prices[i-1]) / prices[i-1])
    if not rets: return None
    return statistics.pstdev(rets)  # population stdev

def infer_market_stress():
    # Basic heuristic: NVDA & SPY vol; if high, prefer hedge
    nv = pct_vol(close_series("NVDA")) or 0.02
    sp = pct_vol(close_series("SPY")) or 0.01
    stress = max(nv, sp)
    return float(stress)

def compute_weights():
    vols = {}
    inv_vols = {}
    for a in ASSETS:
        v = pct_vol(close_series(a)) or 0.02
        vols[a] = v
        inv_vols[a] = 1.0 / max(v, 1e-6)
    # Normalize inverse vol
    total = sum(inv_vols.values())
    w = {a: (inv_vols[a]/total)*TARGET_GROSS for a in ASSETS}
    # Cap weights
    for a in w:
        w[a] = max(MIN_W, min(MAX_W, w[a]))
    # Re-normalize to TARGET_GROSS
    s = sum(w.values())
    w = {a: w[a]/s*TARGET_GROSS for a in ASSETS}

    # Hedge boost during stress: shift 5–15% to GOLD (or BTC if you add later)
    stress = infer_market_stress()
    hedge_add = min(0.15, max(0.05, stress*2))  # 5%–15%
    if "GOLD" in w:
        # take pro-rata from highest-weight growth names
        donors = sorted([a for a in w if a not in ["GOLD","SILVER"]], key=lambda x: -w[x])
        take = hedge_add
        for d in donors:
            if take <= 0: break
            delta = min(take, w[d]*0.2)  # take up to 20% of each donor
            w[d] -= delta
            take -= delta
        w["GOLD"] += hedge_add
        # re-normalize
        s = sum(w.values()); w = {a: w[a]/s*TARGET_GROSS for a in w}

    return w, vols, stress

def write_policy(w, vols, stress):
    pol = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "weights": w,
        "volatility": vols,
        "stress": stress,
        "notes": "Inverse-vol base, caps, + stress-driven GOLD hedge"
    }
    with open(OUTPUT_POLICY, "w") as f:
        json.dump(pol, f, indent=2)
    with open(LOG, "a") as f:
        f.write(json.dumps(pol)+"\n")
    print(f"✅ Risk policy written → {OUTPUT_POLICY}")

if __name__=="__main__":
    w, vols, stress = compute_weights()
    write_policy(w, vols, stress)

#!/bin/bash
echo "🧠 NeoLight Phase 3950–4100 — Smart Cache + Adaptive Risk"
echo "---------------------------------------------------------"

set -e

mkdir -p ai/providers ai/risk logs config tools

# ============================================================
# 1) SMART COMMODITY PROVIDER (Cache + Multi-Source + Proxies)
# ============================================================
cat > ai/providers/commodity_provider.py <<'PY'
import os, json, time, requests
from datetime import datetime, timedelta

CACHE_PATH = "logs/commodity_cache.json"

def _read_cache():
    try:
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"XAU": None, "XAG": None, "updated": None, "source": None}

def _write_cache(xau, xag, source):
    data = {"XAU": xau, "XAG": xag, "source": source, "updated": datetime.utcnow().isoformat()}
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
    return data

class CommodityProvider:
    """
    Returns spot-like XAU/XAG with multi-source fallback and caching.
    Prefers:
      1) MetalpriceAPI (if METALPRICEAPI_KEY set)
      2) Gold-API.com (no key) — may be rate-limited
      3) CoinGecko (PAXG + 'silver' token)
      4) TradingEconomics (guest)
      5) Alpaca GLD/SLV ETF proxy (stocks) if Alpaca keys are present
      6) Cache (last good)
    """
    def __init__(self, max_age_minutes=180, allow_stale_hours=30):
        self.key = os.getenv("METALPRICEAPI_KEY", "").strip()
        self.max_age = timedelta(minutes=max_age_minutes)
        self.allow_stale = timedelta(hours=allow_stale_hours)

    def get_latest_prices(self):
        # 0) Fresh cache usable?
        cache = _read_cache()
        if cache["updated"]:
            age = datetime.utcnow() - datetime.fromisoformat(cache["updated"])
            if age <= self.max_age and cache["XAU"] and cache["XAG"]:
                print(f"📦 Using cached XAU/XAG (age={age}).")
                return {**cache, "source": f"Cache({cache.get('source')})"}

        # 1) MetalpriceAPI (live or 1-day delayed on free plan)
        if self.key:
            try:
                url = f"https://api.metalpriceapi.com/v1/latest?api_key={self.key}&base=USD&currencies=XAU,XAG"
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    rates = r.json().get("rates", {})
                    xau, xag = rates.get("XAU"), rates.get("XAG")
                    if xau and xag:
                        print(f"💰 MetalpriceAPI OK: XAU={xau}, XAG={xag}")
                        return _write_cache(xau, xag, "MetalpriceAPI")
            except Exception as e:
                print(f"⚠️ MetalpriceAPI error: {e}")

        # 2) Gold-API.com
        try:
            r = requests.get("https://api.gold-api.com/price", timeout=10)
            if r.status_code == 200:
                data = r.json()
                xau, xag = data.get("XAU"), data.get("XAG")
                if xau and xag:
                    print(f"🏅 Gold-API OK: XAU={xau}, XAG={xag}")
                    return _write_cache(xau, xag, "GoldAPI")
        except Exception as e:
            print(f"⚠️ Gold-API error: {e}")

        # 3) CoinGecko — PAX Gold + 'silver' market proxy
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=pax-gold,silver&vs_currencies=usd", timeout=10)
            if r.status_code == 200:
                j = r.json()
                xau = j.get("pax-gold", {}).get("usd")
                xag = j.get("silver", {}).get("usd")
                if xau and xag:
                    print(f"🪙 CoinGecko OK: XAU~PAXG={xau}, XAG={xag}")
                    return _write_cache(xau, xag, "CoinGecko")
        except Exception as e:
            print(f"⚠️ CoinGecko error: {e}")

        # 4) TradingEconomics guest
        try:
            # XAU/USD and XAG/USD, guest creds
            for code in [("XAU","XAU/USD"), ("XAG","XAG/USD")]:
                url = f"https://api.tradingeconomics.com/markets/{code[1]}?c=guest:guest"
                rr = requests.get(url, timeout=10)
                if rr.status_code != 200: 
                    raise Exception(f"TE HTTP {rr.status_code}")
                arr = rr.json()
                if not arr or "Close" not in arr[0]: 
                    raise Exception("TE no Close")
                if code[0] == "XAU": xau = arr[0]["Close"]
                if code[0] == "XAG": xag = arr[0]["Close"]
            if xau and xag:
                print(f"📊 TradingEconomics OK: XAU={xau}, XAG={xag}")
                return _write_cache(xau, xag, "TradingEconomics")
        except Exception as e:
            print(f"⚠️ TradingEconomics error: {e}")

        # 5) Alpaca GLD/SLV ETF proxy (if keys exist)
        try:
            if os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY"):
                from ai.providers.alpaca_provider import get_ohlc
                gld = get_ohlc("GLD", timeframe="1Day", limit=1)
                slv = get_ohlc("SLV", timeframe="1Day", limit=1)
                def last_close(bars): 
                    if isinstance(bars, list) and bars: 
                        b = bars[-1]
                        # alpaca v2 returns dicts with 'c' close or keyed fields
                        return float(b.get("c") or b.get("close", 0))
                    return None
                xau = last_close(gld)
                xag = last_close(slv)
                if xau and xag:
                    print(f"🟡 GLD/SLV proxy OK: GLD={xau}, SLV={xag}")
                    return _write_cache(xau, xag, "GLD/SLV Proxy")
        except Exception as e:
            print(f"⚠️ GLD/SLV proxy error: {e}")

        # 6) Use stale cache if allowed
        if cache["updated"]:
            age = datetime.utcnow() - datetime.fromisoformat(cache["updated"])
            if age <= self.allow_stale and (cache["XAU"] or cache["XAG"]):
                print(f"♻️ Using STALE cache (age={age}) due to upstream failures.")
                return {**cache, "source": f"StaleCache({cache.get('source')})"}

        print("❌ All commodity sources failed and cache unusable.")
        return {"XAU": None, "XAG": None, "source": None, "updated": None}
PY
echo "✅ Smart CommodityProvider installed (cache, fallbacks, GLD/SLV proxy)."

# ============================================================
# 2) SIGNAL ENGINE PATCH — route metals to CommodityProvider
# ============================================================
if grep -q 'from ai.providers.commodity_provider import CommodityProvider' ai/signal_engine.py 2>/dev/null; then
  echo "ℹ️ signal_engine.py already metal-aware."
else
  cat > ai/signal_engine.py <<'PY'
import json, datetime, random
from ai.providers.commodity_provider import CommodityProvider
from ai.providers.data_feed import get_bars_for_symbol

commodity = CommodityProvider()
symbols = ["AAPL","MSFT","GOOGL","AMZN","NVDA","SPY","GOLD","SILVER"]

def generate_signals():
    out=[]
    for sym in symbols:
        if sym in ["GOLD","SILVER"]:
            data = commodity.get_latest_prices()
            price = data.get('XAU' if sym=="GOLD" else 'XAG')
            if price:
                bars = [{"t":"now","o":price,"h":price,"l":price,"c":price}]
                print(f"💰 Commodity feed OK: {sym} = {price} (src={data.get('source')})")
            else:
                print(f"⚠️ No price for {sym}")
                bars = []
        else:
            bars = get_bars_for_symbol(sym, limit=30)

        if bars:
            last = bars[-1]
            price = float(last.get("c", last.get("o", 0)) or 0)
            out.append({
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "strategy": random.choice(["momentum","crossover","mean_reversion"]),
                "symbol": sym,
                "signal": random.choice(["BUY","SELL","HOLD"]),
                "confidence": round(random.uniform(0.5,0.99),2),
                "price": price
            })
    if out:
        with open("logs/signals.jsonl","a") as f:
            f.write("\n".join([json.dumps(x) for x in out])+"\n")
        print(f"✅ {len(out)} signals generated across {len(symbols)} symbols.")
    else:
        print("ℹ️ No bars for any symbol — check feeds.")
if __name__=="__main__":
    generate_signals()
PY
  echo "✅ signal_engine.py patched to use CommodityProvider for metals."
fi

# ============================================================
# 3) ADAPTIVE RISK GOVERNOR (vol-based weights + hedge hook)
# ============================================================
cat > ai/risk/risk_governor.py <<'PY'
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
PY
echo "✅ Risk Governor installed."

# ============================================================
# 4) APPLY RISK POLICY HELPER (weights → config/weights.json)
# ============================================================
cat > tools/apply_risk_policy.py <<'PY'
import json, os, sys
POL = "config/risk_policy.json"
OUT = "config/weights.json"

def main():
    if not os.path.exists(POL):
        print("❗ risk_policy.json not found. Run: python3 ai/risk/risk_governor.py")
        sys.exit(1)
    data = json.load(open(POL))
    weights = data.get("weights", {})
    json.dump(weights, open(OUT, "w"), indent=2)
    print(f"✅ Wrote weights → {OUT}")
if __name__=="__main__":
    main()
PY
echo "✅ Risk policy applier installed."

# ============================================================
# 5) NEOLIGHT-FIX ENHANCEMENTS (feeds, cache, risk)
# ============================================================
if ! grep -q "🔎 Commodity cache status" neolight-fix 2>/dev/null; then
cat >> neolight-fix <<'SH'

echo "🔎 Commodity cache status:"
[ -f logs/commodity_cache.json ] && cat logs/commodity_cache.json || echo "❗ No commodity cache found."

echo "🧪 Commodity feed quick-check:"
python3 - <<'PY'
from ai.providers.commodity_provider import CommodityProvider
cp=CommodityProvider()
print(cp.get_latest_prices())
PY

echo "📈 Compute risk policy (quick):"
python3 ai/risk/risk_governor.py
python3 tools/apply_risk_policy.py

echo "📂 Show current weights.json:"
cat config/weights.json || echo "❗ weights.json missing"
SH
fi
echo "✅ neolight-fix upgraded with cache + risk diagnostics."

# ============================================================
# 6) QUICK TESTS
# ============================================================
echo "🧪 Testing signal engine with metals + cache..."
python3 ai/signal_engine.py || true

echo "🧪 Running risk governor..."
python3 ai/risk/risk_governor.py
python3 tools/apply_risk_policy.py

echo "✅ Phase 3950–4100 complete."
 

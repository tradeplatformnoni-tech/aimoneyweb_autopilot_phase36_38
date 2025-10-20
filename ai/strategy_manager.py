import os, random, joblib
STRATEGY=os.getenv("STRATEGY","A").upper()
def score_A(pnl, risk): return (pnl/(risk+1e-6))
def score_B(pnl, risk): return (pnl*2 - risk)
def score_C(pnl, risk): return (pnl*1.5)/(risk+0.5)
def pick(pnl, risk):
    s = os.getenv("STRATEGY","A").upper()
    if s=="B": base=score_B(pnl,risk)
    elif s=="C": base=score_C(pnl,risk)
    else: base=score_A(pnl,risk)
    # If a learned model exists, nudge:
    try:
        m=joblib.load("models/active_model.pkl"); w=m.get('weights',[1])[0]
        base = base * (1 + 0.1*float(w))
    except Exception: pass
    return float(base)

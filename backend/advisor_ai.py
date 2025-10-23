"""
Simple AI Advisor logic — returns natural language explanation from metrics.
"""
import json, pathlib, random, datetime

RISK=pathlib.Path("runtime/risk_metrics.json")
SENT=pathlib.Path("runtime/sentiment_log.jsonl")

def answer(question:str):
    risk=json.load(open(RISK)) if RISK.exists() else {}
    lines=SENT.read_text().splitlines() if SENT.exists() else []
    mood="neutral"
    if lines: mood=json.loads(lines[-1]).get("mood","neutral")
    msg=f"As of {datetime.datetime.utcnow().isoformat()}, market mood is {mood}. "
    if risk:
        msg+=f"Volatility={risk.get('volatility',0):.3f}, Sharpe={risk.get('sharpe',0):.2f}, VaR={risk.get('var_95',0):.3f}. "
        if risk.get('sharpe',0)>1: msg+="Performance is strong — risk-adjusted returns look healthy. "
        elif risk.get('sharpe',0)<0: msg+="Returns are negative risk-adjusted — caution advised. "
    else:
        msg+="No risk metrics yet, still initializing."
    suggestions=[
        "consider rebalancing your momentum allocation",
        "stay defensive until volatility stabilizes",
        "AI will monitor mean reversion opportunities"
    ]
    msg+=random.choice(suggestions)
    return {"answer":msg}

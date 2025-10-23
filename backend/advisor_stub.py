"""
Stub for future AI Advisor. Returns last risk + sentiment summary.
"""
import json, pathlib
RISK=pathlib.Path("runtime/risk_metrics.json")
SENT=pathlib.Path("runtime/sentiment_log.jsonl")
def summarize():
    r=json.load(open(RISK)) if RISK.exists() else {}
    s=[json.loads(l) for l in SENT.open()] if SENT.exists() else []
    last=s[-1] if s else {}
    return {"risk":r,"last_sentiment":last}

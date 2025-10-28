from fastapi import APIRouter
import json, pathlib

router = APIRouter()

RISK = pathlib.Path("runtime/risk_metrics.json")
SENT = pathlib.Path("runtime/sentiment_log.jsonl")

@router.get("/api/risk")
def api_risk():
    return json.load(open(RISK)) if RISK.exists() else {}

@router.get("/api/sentiment/latest")
def api_sent_latest():
    if not SENT.exists(): return {}
    lines = SENT.read_text().strip().splitlines()
    return json.loads(lines[-1]) if lines else {}

@router.get("/api/advisor")
def api_advisor():
    risk = json.load(open(RISK)) if RISK.exists() else {}
    sent = {}
    if SENT.exists():
        lines = SENT.read_text().strip().splitlines()
        if lines: sent = json.loads(lines[-1])
    return {"risk": risk, "last_sentiment": sent}

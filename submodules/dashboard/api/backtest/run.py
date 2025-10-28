# api/backtest/run.py
from fastapi import APIRouter, Query
from tools.backtest_lab import run_backtest

router = APIRouter()

@router.get("/api/backtest/run")
def run(strategy: str = Query(..., description="Strategy name")):
    results = run_backtest(strategy)
    return {"backtest_results": results}

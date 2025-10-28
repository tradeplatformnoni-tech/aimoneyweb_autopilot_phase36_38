# tools/backtest_lab.py
import random

def run_backtest(strategy_name):
    return {
        "strategy": strategy_name,
        "sharpe": round(random.uniform(0.5, 2.5), 2),
        "drawdown": round(random.uniform(0.1, 0.5), 2),
        "pnl": round(random.uniform(1000, 5000), 2)
    }

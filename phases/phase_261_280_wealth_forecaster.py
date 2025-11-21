#!/usr/bin/env python3
import csv
import json
import statistics as stats
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"
STATE.mkdir(exist_ok=True)
CSV = STATE / "performance_metrics.csv"
OUT = STATE / "wealth_trajectory.json"

TARGET = 1_000_000.0


def read_equity():
    if not CSV.exists():
        return []
    out = []
    with CSV.open() as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                out.append((row["timestamp"], float(row["equity"])))
            except:
                pass
    return out


def cagr(equity):
    # crude: use last 30 points as “days”, compute daily returns → annualize
    if len(equity) < 31:
        return None
    w = [e for _, e in equity[-31:]]
    rets = []
    for i in range(1, len(w)):
        if w[i - 1] > 0:
            rets.append((w[i] / w[i - 1]) - 1.0)
    if not rets:
        return None
    avg = stats.mean(rets)
    return ((1 + avg) ** 365) - 1.0


def forecast_to_target(current, cagr_value):
    # simple compounding forecast ignoring cashflows
    if current <= 0 or not cagr_value or cagr_value <= 0:
        return None
    annual = 1 + cagr_value
    # solve years where current * annual^y >= TARGET
    y = 0.0
    v = current
    while v < TARGET and y < 20:
        y += 0.01
        v = current * (annual**y)
    return round(y, 2), round(v, 2)


if __name__ == "__main__":
    while True:
        eq = read_equity()
        current = eq[-1][1] if eq else 0.0
        c = cagr(eq)
        proj = forecast_to_target(current, c)
        data = {
            "time": datetime.utcnow().isoformat(),
            "equity_current": current,
            "cagr_estimate": None if c is None else round(c, 4),
            "forecast_years_to_target": None if proj is None else proj[0],
            "forecast_equity_final": None if proj is None else proj[1],
            "target": TARGET,
        }
        OUT.write_text(json.dumps(data, indent=2))
        time.sleep(3600)

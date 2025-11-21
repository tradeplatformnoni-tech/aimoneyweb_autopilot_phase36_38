#!/usr/bin/env python3
import os
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
STATE.mkdir(parents=True, exist_ok=True)


def tidy(df: pd.DataFrame) -> pd.DataFrame:
    # yfinance often returns Date as index; make it an explicit column
    if "Date" not in df.columns:
        df = df.reset_index()
    # ensure 1-D
    for c in ("Date", "Close"):
        if c in df.columns:
            s = df[c]
            if hasattr(s, "values") and getattr(s.values, "ndim", 1) > 1:
                df[c] = s.values.ravel()
    # standardize name
    df["date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    return df[["date", "Close"]].rename(columns={"Close": "SPY_Close"})


def main():
    spy = yf.download("SPY", period="5y", interval="1d", auto_adjust=False, progress=False)
    if spy is None or spy.empty:
        raise SystemExit("No SPY data")
    out = tidy(spy)
    out.to_csv(STATE / "spy_benchmark.csv", index=False)
    print(f"✅ wrote {STATE / 'spy_benchmark.csv'} rows={len(out)}")


if __name__ == "__main__":
    main()

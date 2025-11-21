#!/usr/bin/env python3
"""
backend/ledger_engine.py
NeoLight — Equity Ledger & Persistence (Phase 301–340)

Functions:
- Record fills/trades to state/pnl_history.csv
- Maintain rolling equity curve -> state/performance_metrics.csv
- Persist portfolio snapshots -> runtime/portfolio.json (via portfolio_manager)
- Daily wealth trajectory -> state/wealth_trajectory.json
- Snapshots to snapshots/ledger_YYYYMMDD.json
- Optional SQLite mirror -> runtime/ledger.db
- Telegram alerts on anomalies (optional)

CLI:
  python backend/ledger_engine.py --health
  python backend/ledger_engine.py --record-fill --symbol BTCUSD --side buy --qty 0.1 --price 64250.0 --fee 1.25
  python backend/ledger_engine.py --snapshot
  python backend/ledger_engine.py --rebuild-equity
"""

import argparse
import csv
import json
import os
import sqlite3
import sys

try:
    from backend import portfolio_manager
except ImportError:
    portfolio_manager = None

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
SNAPSHOTS = ROOT / "snapshots"
LOGS = ROOT / "logs"
BACKEND = ROOT / "backend"

STATE.mkdir(exist_ok=True)
RUNTIME.mkdir(exist_ok=True)
SNAPSHOTS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

PNL_CSV = STATE / "pnl_history.csv"  # append-only fills
PERF_CSV = STATE / "performance_metrics.csv"  # rolling equity curve
WEALTH_JSON = STATE / "wealth_trajectory.json"  # daily wealth trajectory
PORTFOLIO_JSON = RUNTIME / "portfolio.json"  # managed by portfolio_manager
SQLITE_DB = RUNTIME / "ledger.db"  # optional mirror

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
STARTING_EQUITY = float(os.getenv("NEOLIGHT_STARTING_EQUITY", "10000"))


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _send_telegram(text: str):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return
    import urllib.parse
    import urllib.request

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=6)
    except Exception:
        # Silent fail; we don't block ledger
        pass


def ensure_csv_headers():
    if not PNL_CSV.exists():
        with PNL_CSV.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "timestamp", "symbol", "side", "qty", "price", "reason", "pnl"])
    elif PNL_CSV.exists():
        # Check if header needs updating
        with PNL_CSV.open("r") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header and "pnl" not in header:
                # Backup and recreate with new header
                import shutil

                backup = PNL_CSV.with_suffix(".csv.backup")
                shutil.copy(PNL_CSV, backup)
                # Read all data
                f.seek(0)
                rows = list(csv.reader(f))
                # Write with new header
                with PNL_CSV.open("w", newline="") as fw:
                    w = csv.writer(fw)
                    w.writerow(
                        ["date", "timestamp", "symbol", "side", "qty", "price", "reason", "pnl"]
                    )
                    # Write existing rows, adding empty pnl column
                    for row in rows[1:]:  # Skip old header
                        if len(row) < 8:
                            row.extend([""] * (8 - len(row)))
                        w.writerow(row[:8])
    if not PERF_CSV.exists():
        with PERF_CSV.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "date",
                    "timestamp",
                    "equity",
                    "pnl_1d",
                    "drawdown",
                    "sharpe_30d",
                    "sortino_30d",
                    "win_rate_7d",
                    "trades_7d",
                ]
            )


def init_sqlite():
    con = sqlite3.connect(str(SQLITE_DB))
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fills(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, symbol TEXT, side TEXT, qty REAL, price REAL, fee REAL, note TEXT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS equity(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, equity REAL, cash REAL, mdd_pct REAL, day_pnl REAL, rolling_sharpe REAL
    );""")
    con.commit()
    return con


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except:
        return default


def write_json(path: Path, obj: Any):
    path.write_text(json.dumps(obj, indent=2))


def append_fill_row(row: dict[str, Any], pnl: float = 0.0):
    """Append fill row with P&L calculation."""
    ts = row.get("ts", utc_now_iso())
    date = ts[:10] if len(ts) >= 10 else datetime.now(UTC).strftime("%Y-%m-%d")
    with PNL_CSV.open("a", newline="") as f:
        csv.writer(f).writerow(
            [
                date,
                ts,
                row["symbol"],
                row["side"],
                row["qty"],
                row["price"],
                row.get("note", ""),
                f"{pnl:.6f}" if pnl != 0.0 else "",
            ]
        )


def append_equity_row(equity: float, cash: float, mdd_pct: float, day_pnl: float, sharpe: float):
    """Append equity row with proper date format matching performance_metrics.csv structure."""
    ts = utc_now_iso()
    date = ts[:10] if len(ts) >= 10 else datetime.now(UTC).strftime("%Y-%m-%d")
    with PERF_CSV.open("a", newline="") as f:
        w = csv.writer(f)
        # Match the header: date,timestamp,equity,pnl_1d,drawdown,sharpe_30d,sortino_30d,win_rate_7d,trades_7d
        w.writerow(
            [
                date,
                ts,
                f"{equity:.6f}",
                f"{day_pnl:.6f}",
                f"{mdd_pct:.6f}",
                f"{sharpe:.6f}",
                "",
                "",
                "",
            ]
        )


def compute_mdd(equity_series):
    """Calculate Maximum Drawdown with safeguards against invalid values."""
    if not equity_series or len(equity_series) == 0:
        return 0.0

    peak = -1e18
    mdd = 0.0
    for e in equity_series:
        # Ensure equity is valid (non-negative, reasonable)
        if e < 0:
            e = 0.01  # Cap negative equity at small positive value
        if e > 1e15:  # Sanity check for absurdly large values
            continue

        peak = max(peak, e)
        # Only calculate drawdown if we have a valid peak
        if peak > 0.01:  # Minimum threshold to avoid division by tiny numbers
            dd = (peak - e) / peak * 100
            # Cap drawdown at 100% (can't lose more than 100% of peak)
            mdd = max(mdd, min(dd, 100.0))

    # Final sanity check - drawdown can't exceed 100%
    return min(mdd, 100.0)


def compute_sharpe(daily_pnls):
    # Simple rolling Sharpe: mean / std (no risk-free)
    import math

    n = len(daily_pnls)
    if n < 2:
        return 0.0
    mean = sum(daily_pnls) / n
    var = sum((x - mean) ** 2 for x in daily_pnls) / (n - 1)
    std = math.sqrt(max(var, 1e-9))
    return mean / std if std > 0 else 0.0


def get_position_value(portfolio: dict, symbol_prices: dict = None) -> float:
    """
    Calculate total value of open positions
    
    Args:
        portfolio: Portfolio dict with positions
        symbol_prices: Optional dict of current prices {symbol: price}
    
    Returns:
        Total position value in USD
    """
    total_value = 0.0
    positions = portfolio.get("positions", {})
    
    # Handle both dict and list formats
    if isinstance(positions, dict):
        # Dict format: {symbol: {qty: ..., avg_price: ...}}
        for symbol, pos_data in positions.items():
            if not isinstance(pos_data, dict):
                continue
            qty = float(pos_data.get("qty", 0.0))
            if qty == 0:
                continue
            # Try to get current price
            if symbol_prices and symbol in symbol_prices:
                price = float(symbol_prices[symbol])
            else:
                # Fallback to avg_price if no current price available
                price = float(pos_data.get("avg_price", 0.0))
            position_value = abs(qty) * price
            total_value += position_value
    elif isinstance(positions, list):
        # List format: [{symbol: ..., qty: ..., avg_price: ...}, ...]
        for pos_item in positions:
            if not isinstance(pos_item, dict):
                continue
            symbol = pos_item.get("symbol", "")
            qty = float(pos_item.get("qty", 0.0))
            if qty == 0:
                continue
            # Try to get current price
            if symbol_prices and symbol in symbol_prices:
                price = float(symbol_prices[symbol])
            else:
                # Fallback to avg_price
                price = float(pos_item.get("avg_price", 0.0))
            position_value = abs(qty) * price
            total_value += position_value
    
    return total_value


def rebuild_equity_curve():
    # Rebuild from pnl_history.csv + portfolio.json; minimalistic
    ensure_csv_headers()
    portfolio = read_json(
        PORTFOLIO_JSON, {"cash": STARTING_EQUITY, "positions": {}, "equity": STARTING_EQUITY}
    )
    cash = float(portfolio.get("cash", STARTING_EQUITY))
    equity = float(portfolio.get("equity", STARTING_EQUITY))
    # Track positions for accurate valuation
    current_positions = {}  # {symbol: {qty: float, avg_price: float}}
    equity_series = []
    daily_map = {}  # date -> pnl
    if PNL_CSV.exists():
        with PNL_CSV.open() as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    # Handle both old and new CSV formats
                    qty_str = row.get("qty", "0")
                    price_str = row.get("price", "0")
                    fee_str = row.get("fee", "0")

                    # Skip rows with empty essential fields
                    if (
                        not qty_str
                        or not price_str
                        or qty_str.strip() == ""
                        or price_str.strip() == ""
                    ):
                        continue

                    try:
                        qty = float(qty_str)
                        price = float(price_str)
                        fee = float(fee_str) if fee_str and fee_str.strip() else 0.0
                    except ValueError:
                        continue  # Skip malformed rows

                    side = row.get("side", "").lower()
                    symbol = row.get("symbol", "").upper()
                    if not side or side not in ["buy", "sell"]:
                        continue

                    gross = qty * price
                    
                    # Update cash
                    if side == "buy":
                        cash -= gross
                        # Track position
                        if symbol not in current_positions:
                            current_positions[symbol] = {"qty": 0.0, "avg_price": 0.0}
                        
                        # Update position - weighted average price
                        pos = current_positions[symbol]
                        old_qty = pos["qty"]
                        old_avg = pos["avg_price"]
                        
                        new_qty = old_qty + qty
                        if new_qty > 0:
                            # Weighted average
                            pos["avg_price"] = ((old_qty * old_avg) + (qty * price)) / new_qty
                        pos["qty"] = new_qty
                    else:  # sell
                        cash += gross
                        # Reduce position
                        if symbol in current_positions:
                            current_positions[symbol]["qty"] -= qty
                            # Remove if fully closed
                            if current_positions[symbol]["qty"] <= 0:
                                del current_positions[symbol]
                    
                    cash -= fee
                    
                    # ================================================================
                    # CRITICAL FIX: Calculate equity INCLUDING positions
                    # ================================================================
                    
                    # Calculate position value
                    position_value = 0.0
                    for pos_symbol, pos_data in current_positions.items():
                        pos_qty = pos_data["qty"]
                        pos_avg_price = pos_data["avg_price"]
                        
                        # For rebuild, use avg_price (we don't have current prices)
                        # This is conservative - real equity might be higher/lower
                        position_value += abs(pos_qty) * pos_avg_price
                    
                    # ✅ CORRECT: equity = cash + positions
                    equity = cash + position_value
                    
                    equity_series.append(equity)

                    # Get date from timestamp or date column
                    day = row.get("date", "")
                    if not day or day.strip() == "":
                        ts = row.get("timestamp", row.get("ts", ""))
                        day = ts[:10] if len(ts) >= 10 else datetime.utcnow().strftime("%Y-%m-%d")

                    daily_map[day] = (
                        daily_map.get(day, 0.0) + (gross if side == "sell" else -gross) - fee
                    )
                except (ValueError, KeyError):
                    continue  # Skip malformed rows
    # FIX: Validate equity_series before computing MDD to prevent 100% drawdown alerts
    if equity_series:
        # Filter out invalid equity values (negative, zero, or absurdly large)
        valid_equity = [e for e in equity_series if 0.01 < e < 1e10]
        if len(valid_equity) >= 2:  # Need at least 2 points for drawdown
            mdd = compute_mdd(valid_equity)
        else:
            mdd = 0.0  # Not enough valid data
    else:
        mdd = 0.0

    sharpe = compute_sharpe(list(daily_map.values()))
    append_equity_row(
        equity, cash, mdd, daily_map.get(datetime.utcnow().strftime("%Y-%m-%d"), 0.0), sharpe
    )
    return equity, cash, mdd, sharpe


def record_fill(symbol: str, side: str, qty: float, price: float, fee: float, note: str = ""):
    ensure_csv_headers()

    # Calculate P&L for SELL orders
    pnl = 0.0
    if side.lower() == "sell":
        # Get portfolio to find average buy price
        if portfolio_manager:
            try:
                portfolio = portfolio_manager.load_portfolio()
            except Exception:
                portfolio = read_json(PORTFOLIO_JSON, {"positions": {}})
        else:
            portfolio = read_json(PORTFOLIO_JSON, {"positions": {}})
        positions = portfolio.get("positions", {})

        # Handle both dict and list formats for positions
        avg_price = 0.0
        if isinstance(positions, dict):
            # Dict format: {symbol: {avg_price: ..., qty: ...}}
            pos = positions.get(symbol.upper(), {})
            avg_price = pos.get("avg_price", 0.0)
        elif isinstance(positions, list):
            # List format: [{symbol: ..., avg_price: ...}, ...]
            for pos_item in positions:
                if (
                    isinstance(pos_item, dict)
                    and pos_item.get("symbol", "").upper() == symbol.upper()
                ):
                    avg_price = float(pos_item.get("avg_price", 0.0))
                    break
        else:
            positions = {}

        # Persist normalized structure if needed
        if portfolio_manager and isinstance(positions, dict):
            portfolio["positions"] = positions
            portfolio_manager.save_portfolio(portfolio)

        if avg_price > 0:
            # P&L = (sell_price - avg_buy_price) * qty - fees
            pnl = (float(price) - avg_price) * float(qty) - float(fee)
        else:
            # No position found - might be opening short or data issue
            # Use 0 P&L for now
            pnl = -float(fee)  # At least account for fees

    row = {
        "ts": utc_now_iso(),
        "symbol": symbol.upper(),
        "side": side.lower(),
        "qty": float(qty),
        "price": float(price),
        "fee": float(fee),
        "note": note,
    }
    append_fill_row(row, pnl)
    # Optional SQLite
    try:
        con = init_sqlite()
        con.execute(
            "INSERT INTO fills(ts,symbol,side,qty,price,fee,note) VALUES(?,?,?,?,?,?,?)",
            (
                row["ts"],
                row["symbol"],
                row["side"],
                row["qty"],
                row["price"],
                row["fee"],
                row["note"],
            ),
        )
        con.commit()
        con.close()
    except Exception:
        pass
    # Update portfolio
    os.system(
        f"{sys.executable} {BACKEND / 'portfolio_manager.py'} --apply-fill --symbol {row['symbol']} --side {row['side']} --qty {row['qty']} --price {row['price']} --fee {row['fee']} >/dev/null 2>&1"
    )
    # Quick equity update
    equity, cash, mdd, sharpe = rebuild_equity_curve()
    # Snapshot wealth trajectory (daily)
    wealth_raw = read_json(WEALTH_JSON, {})
    if isinstance(wealth_raw, list):
        wealth = {}
        for entry in wealth_raw:
            if not isinstance(entry, dict):
                continue
            day = entry.get("date")
            if not day:
                continue
            wealth_value = entry.get("wealth")
            wealth[day] = {
                "equity": float(wealth_value)
                if wealth_value is not None
                else float(entry.get("equity", 0.0)),
                "cash": float(entry.get("cash", wealth_value if wealth_value is not None else 0.0)),
                "mdd_pct": float(entry.get("mdd_pct", 0.0)),
                "rolling_sharpe": float(entry.get("rolling_sharpe", 0.0)),
            }
    elif isinstance(wealth_raw, dict):
        wealth = wealth_raw
    else:
        wealth = {}
    day = datetime.utcnow().strftime("%Y-%m-%d")
    wealth[day] = {"equity": equity, "cash": cash, "mdd_pct": mdd, "rolling_sharpe": sharpe}
    write_json(WEALTH_JSON, wealth)
    # Risk alert example - only send if drawdown is reasonable (capped at 100%)
    # FIX: Suppress alerts for invalid drawdown calculations (>100% means calculation error)
    if 10.0 <= mdd <= 100.0:
        _send_telegram(f"⚠️ NeoLight Drawdown Alert: {mdd:.1f}%")
    elif mdd > 100.0:
        # If drawdown exceeds 100%, there's a calculation error - log but DON'T send alert
        import logging

        logging.warning(
            f"⚠️ Invalid drawdown calculated: {mdd:.1f}% - suppressing alert (likely data issue)"
        )
        # Don't send Telegram alert for calculation errors - it's confusing


def snapshot():
    # One-off JSON snapshot for audit/backup
    snap = {
        "ts": utc_now_iso(),
        "portfolio": read_json(PORTFOLIO_JSON, {}),
        "wealth": read_json(WEALTH_JSON, {}),
    }
    path = SNAPSHOTS / f"ledger_{datetime.utcnow().strftime('%Y%m%d')}.json"
    write_json(path, snap)
    print(f"Snapshot → {path}")


def health():
    ok = True
    for p in [PNL_CSV, PERF_CSV, WEALTH_JSON, PORTFOLIO_JSON]:
        if p.exists():
            continue
        # these will be created lazily; not fatal
    # minimal confirmation
    print(json.dumps({"ok": True, "ts": utc_now_iso()}))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--health", action="store_true")
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--rebuild-equity", action="store_true")
    ap.add_argument("--record-fill", action="store_true")
    ap.add_argument("--symbol", type=str, default="")
    ap.add_argument("--side", type=str, default="")
    ap.add_argument("--qty", type=float, default=0.0)
    ap.add_argument("--price", type=float, default=0.0)
    ap.add_argument("--fee", type=float, default=0.0)
    ap.add_argument("--note", type=str, default="")
    args = ap.parse_args()

    if args.health:
        sys.exit(health())

    if args.snapshot:
        snapshot()
        return

    if args.rebuild_equity:
        ensure_csv_headers()
        equity, cash, mdd, sharpe = rebuild_equity_curve()
        print(
            json.dumps(
                {"equity": equity, "cash": cash, "mdd_pct": mdd, "rolling_sharpe": sharpe}, indent=2
            )
        )
        return

    if args.record_fill:
        if not (args.symbol and args.side and args.qty and args.price is not None):
            print(
                "Missing fill args. Example: --record-fill --symbol BTCUSD --side buy --qty 0.1 --price 64000 --fee 1.25",
                file=sys.stderr,
            )
            sys.exit(2)
        record_fill(args.symbol, args.side, args.qty, args.price, args.fee, args.note)
        print("OK")
        return

    ap.print_help()


if __name__ == "__main__":
    main()

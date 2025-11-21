#!/usr/bin/env python3
"""
backend/portfolio_manager.py
Simple portfolio state for NeoLight Ledger (Phase 301–340)
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
RUNTIME.mkdir(exist_ok=True)

PORTFOLIO_JSON = RUNTIME / "portfolio.json"
STARTING_EQUITY = float(os.getenv("NEOLIGHT_STARTING_EQUITY", "10000"))


def _normalize_positions(raw_positions):
    """
    Ensure portfolio positions use the canonical dict format:
    { "SYM": {"qty": float, "avg_price": float}, ... }
    """
    normalized = {}
    legacy_allocations = {}

    if isinstance(raw_positions, dict):
        for symbol, payload in raw_positions.items():
            sym = str(symbol).upper()
            if isinstance(payload, dict):
                qty = float(payload.get("qty", 0.0) or 0.0)
                avg_price = float(payload.get("avg_price", 0.0) or 0.0)
            elif isinstance(payload, (int, float)):
                qty = float(payload)
                avg_price = 0.0
            else:
                qty = 0.0
                avg_price = 0.0
            normalized[sym] = {"qty": qty, "avg_price": avg_price}
    elif isinstance(raw_positions, list):
        for item in raw_positions:
            if not isinstance(item, dict):
                continue
            sym = str(item.get("symbol", "")).upper()
            if not sym:
                continue
            legacy_allocations[sym] = float(item.get("weight", 0.0) or 0.0)
            qty = float(item.get("qty", 0.0) or 0.0)
            avg_price = float(item.get("avg_price", 0.0) or 0.0)
            normalized[sym] = {"qty": qty, "avg_price": avg_price}

    return normalized, legacy_allocations


def load_portfolio():
    if not PORTFOLIO_JSON.exists():
        p = {"cash": STARTING_EQUITY, "equity": STARTING_EQUITY, "positions": {}}
        PORTFOLIO_JSON.write_text(json.dumps(p, indent=2))
        return p

    try:
        portfolio = json.loads(PORTFOLIO_JSON.read_text())
    except Exception:
        portfolio = {"cash": STARTING_EQUITY, "equity": STARTING_EQUITY, "positions": {}}
        PORTFOLIO_JSON.write_text(json.dumps(portfolio, indent=2))
        return portfolio

    positions = portfolio.get("positions", {})
    normalized_positions, legacy_allocations = _normalize_positions(positions)
    portfolio["positions"] = normalized_positions

    if legacy_allocations:
        existing_alloc = portfolio.get("allocations", {})
        if not isinstance(existing_alloc, dict):
            existing_alloc = {}
        # Do not overwrite existing allocations, just merge legacy weights
        merged = {**legacy_allocations, **existing_alloc}
        portfolio["allocations"] = merged

    # Ensure cash/equity fields exist and are floats
    portfolio["cash"] = float(portfolio.get("cash", STARTING_EQUITY) or 0.0)
    portfolio["equity"] = float(portfolio.get("equity", portfolio["cash"]) or portfolio["cash"])

    save_portfolio(portfolio)
    return portfolio


def save_portfolio(p):
    normalized_positions, _ = _normalize_positions(p.get("positions", {}))
    p["positions"] = normalized_positions
    PORTFOLIO_JSON.write_text(json.dumps(p, indent=2))


def apply_fill(symbol: str, side: str, qty: float, price: float, fee: float):
    p = load_portfolio()
    symbol = symbol.upper()
    pos = p["positions"].get(symbol, {"qty": 0.0, "avg_price": 0.0})
    cash = float(p.get("cash", STARTING_EQUITY))

    gross = qty * price
    if side.lower() == "buy":
        new_qty = pos["qty"] + qty
        if new_qty <= 0:
            pos = {"qty": 0.0, "avg_price": 0.0}
        else:
            pos["avg_price"] = (pos["qty"] * pos["avg_price"] + gross) / new_qty
            pos["qty"] = new_qty
        cash -= gross + fee
    else:
        # sell
        realized = gross - fee
        pos["qty"] = max(0.0, pos["qty"] - qty)
        if pos["qty"] == 0:
            pos["avg_price"] = 0.0
        cash += realized

    p["positions"][symbol] = pos
    p["cash"] = max(0.0, cash)
    # Without live mark-to-market, equity ≈ cash + sum(open PnL=0 baseline)
    p["equity"] = p["cash"]
    save_portfolio(p)
    return p


def show():
    print(json.dumps(load_portfolio(), indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply-fill", action="store_true")
    ap.add_argument("--symbol", type=str, default="")
    ap.add_argument("--side", type=str, default="")
    ap.add_argument("--qty", type=float, default=0.0)
    ap.add_argument("--price", type=float, default=0.0)
    ap.add_argument("--fee", type=float, default=0.0)
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    if args.show:
        show()
        return

    if args.apply_fill:
        if not (args.symbol and args.side and args.qty and args.price is not None):
            print(
                "Usage: --apply-fill --symbol BTCUSD --side buy --qty 0.1 --price 64000 --fee 1.25",
                file=sys.stderr,
            )
            sys.exit(2)
        p = apply_fill(args.symbol, args.side, args.qty, args.price, args.fee)
        print(json.dumps(p, indent=2))
        return

    ap.print_help()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Retroactive P&L Calculator - Phase 3700-3900
=============================================
Calculates P&L for historical trades by processing them chronologically
and matching SELL orders to BUY orders using average cost basis.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
PNL_CSV = STATE / "pnl_history.csv"
BACKUP_CSV = STATE / f"pnl_history.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def is_valid_trade(row: Any) -> bool:
    """Check if a trade row is valid."""
    try:
        # Handle both dict and pandas Series
        if hasattr(row, "get"):
            symbol = str(row.get("symbol", "")).strip()
            side = str(row.get("side", "")).strip().lower()
            qty_str = str(row.get("qty", "")).strip()
            price_str = str(row.get("price", "")).strip()
        else:
            # Direct access for pandas Series
            symbol = str(row["symbol"] if "symbol" in row else "").strip()
            side = str(row["side"] if "side" in row else "").strip().lower()
            qty_str = str(row["qty"] if "qty" in row else "").strip()
            price_str = str(row["price"] if "price" in row else "").strip()

        # Symbol should be alphanumeric (not a number)
        if not symbol or symbol.replace("-", "").replace("_", "").isnumeric():
            return False

        # Side should be buy or sell
        if side not in ["buy", "sell"]:
            return False

        # Qty and price should be convertible to float
        try:
            qty = float(qty_str)
            price = float(price_str)
            if qty <= 0 or price <= 0:
                return False
        except (ValueError, TypeError):
            return False

        return True
    except Exception:
        return False


def parse_timestamp(row: dict[str, Any]) -> datetime | None:
    """Parse timestamp from row."""
    try:
        # Try different timestamp columns
        for col in ["timestamp", "ts", "date"]:
            if col in row:
                ts_str = str(row[col]).strip()
                if ts_str:
                    # Try ISO format first
                    try:
                        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except:
                        # Try date format
                        try:
                            return datetime.strptime(ts_str[:10], "%Y-%m-%d")
                        except:
                            pass
        return None
    except Exception:
        return None


def calculate_retroactive_pnl() -> dict[str, Any]:
    """
    Calculate P&L for all historical trades.

    Returns:
        Summary dictionary with stats
    """
    if not PNL_CSV.exists():
        print(f"❌ P&L history file not found: {PNL_CSV}")
        return {"error": "File not found"}

    # Create backup
    print(f"📦 Creating backup: {BACKUP_CSV}")
    shutil.copy(PNL_CSV, BACKUP_CSV)

    # Load CSV - handle misaligned format by reading row-by-row
    print(f"📖 Loading {PNL_CSV}...")
    try:
        import csv

        rows = []
        with open(PNL_CSV) as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header

            for row in reader:
                if len(row) < 7:
                    continue  # Skip malformed rows

                # Recent format (7 cols): timestamp,symbol,side,qty,price,fee,reason
                # Old format (8 cols): date,timestamp,symbol,side,qty,price,reason,pnl
                if len(row) == 7:
                    # 7 columns - recent format
                    rows.append(
                        {
                            "timestamp": row[0],
                            "symbol": row[1],
                            "side": row[2],
                            "qty": row[3],
                            "price": row[4],
                            "fee": row[5],
                            "reason": row[6],
                            "pnl": "",
                        }
                    )
                elif len(row) == 8:
                    # 8 columns - check if first is timestamp (has "T" for ISO format)
                    first = str(row[0]).strip()
                    if "T" in first:
                        # First column is timestamp (recent format with pnl column)
                        rows.append(
                            {
                                "timestamp": row[0],
                                "symbol": row[1],
                                "side": row[2],
                                "qty": row[3],
                                "price": row[4],
                                "fee": row[5] if len(row) > 5 else "0",
                                "reason": row[6] if len(row) > 6 else "",
                                "pnl": row[7] if len(row) > 7 else "",
                            }
                        )
                    # Skip old format rows (they're malformed and will be filtered out anyway)

        print(f"   Parsed {len(rows)} valid rows from CSV")
        df = pd.DataFrame(rows)

        # Ensure required columns exist
        if "fee" not in df.columns:
            df["fee"] = 0.0
        if "pnl" not in df.columns:
            df["pnl"] = ""

        print(f"   Created DataFrame with {len(df)} rows, columns: {list(df.columns)}")

        # Debug: show last few rows
        if len(df) > 0:
            print("\n   Sample rows (last 3):")
            for idx in range(max(0, len(df) - 3), len(df)):
                row = df.iloc[idx]
                symbol = str(row.get("symbol", "")).strip()
                side = str(row.get("side", "")).strip()
                qty = row.get("qty", "")
                price = row.get("price", "")
                print(f"     Row {idx}: symbol='{symbol}', side='{side}', qty={qty}, price={price}")

    except Exception as e:
        print(f"❌ Failed to load CSV: {e}")
        import traceback

        traceback.print_exc()
        return {"error": str(e)}

    # Position tracking: {symbol: {"qty": float, "avg_price": float}}
    positions: dict[str, dict[str, float]] = {}

    # Statistics
    stats = {
        "total_rows": len(df),
        "valid_trades": 0,
        "buy_trades": 0,
        "sell_trades": 0,
        "pnl_calculated": 0,
        "pnl_total": 0.0,
        "skipped_rows": 0,
        "errors": 0,
    }

    # Process each row
    pnl_values = []

    print(f"\n   Processing {len(df)} rows...")
    if len(df) > 0:
        print(f"   First row columns: {list(df.columns)}")
        first_row = df.iloc[0]
        print(
            f"   First row sample: symbol={first_row.get('symbol', 'N/A') if hasattr(first_row, 'get') else (first_row['symbol'] if 'symbol' in first_row else 'N/A')}"
        )

    for idx, row in df.iterrows():
        try:
            # Debug: show first few rows being processed
            if idx < 5:
                symbol_test = str(
                    row.get("symbol", "")
                    if hasattr(row, "get")
                    else (row["symbol"] if "symbol" in row else "")
                ).strip()
                side_test = str(
                    row.get("side", "")
                    if hasattr(row, "get")
                    else (row["side"] if "side" in row else "")
                ).strip()
                print(f"  Debug row {idx}: symbol='{symbol_test}', side='{side_test}'")

            # Check if valid trade
            if not is_valid_trade(row):
                pnl_values.append("")  # Keep empty P&L
                stats["skipped_rows"] += 1
                if idx < 5:
                    print(f"    ⚠️  Row {idx} failed validation")
                continue

            # Use direct column access for pandas Series
            symbol = (
                str(row.get("symbol", "") if hasattr(row, "get") else row["symbol"]).strip().upper()
            )
            side = str(row.get("side", "") if hasattr(row, "get") else row["side"]).strip().lower()

            try:
                qty_val = row.get("qty", "") if hasattr(row, "get") else row["qty"]
                price_val = row.get("price", "") if hasattr(row, "get") else row["price"]
                qty_str = str(qty_val).strip()
                price_str = str(price_val).strip()

                if not qty_str or not price_str:
                    pnl_values.append("")
                    stats["skipped_rows"] += 1
                    continue

                qty = float(qty_str)
                price = float(price_str)

                # Fee handling
                fee_val = (
                    row.get("fee", "")
                    if hasattr(row, "get")
                    else row.get("fee", 0.0)
                    if "fee" in row
                    else 0.0
                )
                fee_str = str(fee_val).strip()
                if fee_str and fee_str != "" and fee_str.lower() != "nan":
                    try:
                        fee = float(fee_str)
                    except (ValueError, TypeError):
                        # Estimate fee as 0.02% (2 bps) of trade value
                        fee = qty * price * 0.0002
                else:
                    # Estimate fee as 0.02% (2 bps) of trade value
                    fee = qty * price * 0.0002
            except (ValueError, TypeError):
                pnl_values.append("")
                stats["skipped_rows"] += 1
                continue

            stats["valid_trades"] += 1

            if side == "buy":
                stats["buy_trades"] += 1
                # Add to position inventory
                if symbol not in positions:
                    positions[symbol] = {"qty": 0.0, "avg_price": 0.0}

                pos = positions[symbol]
                # Update average cost basis
                total_cost = (pos["qty"] * pos["avg_price"]) + (qty * price)
                total_qty = pos["qty"] + qty

                if total_qty > 0:
                    pos["avg_price"] = total_cost / total_qty
                    pos["qty"] = total_qty

                # BUY has no P&L (position opened)
                pnl_values.append("")

            elif side == "sell":
                stats["sell_trades"] += 1

                # Check if we have a position
                if symbol not in positions or positions[symbol]["qty"] <= 0:
                    # SELL without matching BUY - use 0 P&L (or negative fee)
                    pnl = -fee
                    pnl_values.append(f"{pnl:.6f}")
                    stats["pnl_calculated"] += 1
                    stats["pnl_total"] += pnl
                    print(f"  ⚠️  SELL {symbol} without matching BUY (qty={qty}, price={price})")
                else:
                    pos = positions[symbol]
                    avg_buy_price = pos["avg_price"]

                    # Calculate P&L: (sell_price - avg_buy_price) * qty - fees
                    pnl = (price - avg_buy_price) * qty - fee

                    pnl_values.append(f"{pnl:.6f}")
                    stats["pnl_calculated"] += 1
                    stats["pnl_total"] += pnl

                    # Reduce position
                    pos["qty"] = max(0.0, pos["qty"] - qty)
                    if pos["qty"] <= 0:
                        pos["avg_price"] = 0.0

                    if idx % 100 == 0:  # Progress update
                        print(f"  ✅ Processed {idx + 1}/{len(df)}: {symbol} SELL P&L={pnl:.2f}")
            else:
                pnl_values.append("")

        except Exception as e:
            print(f"  ⚠️  Error processing row {idx}: {e}")
            pnl_values.append("")
            stats["errors"] += 1

    # Update DataFrame with calculated P&L
    print("\n📊 Updating CSV with calculated P&L...")
    df["pnl"] = pnl_values

    # Write back to CSV
    df.to_csv(PNL_CSV, index=False)
    print(f"✅ Updated {PNL_CSV}")

    # Print summary
    print("\n📋 Summary:")
    print(f"  Total rows: {stats['total_rows']}")
    print(f"  Valid trades: {stats['valid_trades']}")
    print(f"  BUY trades: {stats['buy_trades']}")
    print(f"  SELL trades: {stats['sell_trades']}")
    print(f"  P&L calculated: {stats['pnl_calculated']}")
    print(f"  Total P&L: ${stats['pnl_total']:.2f}")
    print(f"  Skipped rows: {stats['skipped_rows']}")
    print(f"  Errors: {stats['errors']}")

    # Check how many P&L values were populated
    non_empty_pnl = sum(1 for p in pnl_values if p and p.strip() != "")
    print(f"\n✅ P&L values populated: {non_empty_pnl} rows")

    return stats


def main():
    """Main entry point."""
    print("=" * 60)
    print("🔄 Retroactive P&L Calculator")
    print("=" * 60)
    print()

    stats = calculate_retroactive_pnl()

    if "error" in stats:
        print(f"\n❌ Failed: {stats['error']}")
        return 1

    print("\n✅ Retroactive P&L calculation complete!")
    print(f"   Backup saved: {BACKUP_CSV}")
    print(f"   Updated file: {PNL_CSV}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())

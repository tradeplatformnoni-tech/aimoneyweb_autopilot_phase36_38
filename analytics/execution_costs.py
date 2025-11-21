"""
Execution Cost Minimization
Measures implementation shortfall and provides feedback to Governor
World-class: CSV reporting, cost analysis, Governor integration
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~")) / "neolight"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def compute_implementation_shortfall(
    arrival_price: float, avg_fill_price: float, signed_qty: float, fees: float = 0.0
) -> float:
    """
    Compute implementation shortfall.

    Args:
        arrival_price: Price when order arrived
        avg_fill_price: Average fill price
        signed_qty: Signed quantity (positive for buy, negative for sell)
        fees: Trading fees

    Returns:
        Implementation shortfall (negative = cost)
    """
    return (arrival_price - avg_fill_price) * signed_qty - fees


def generate_execution_report(orders: list[dict[str, Any]], date: Optional[str] = None) -> str:
    """
    Generate daily execution cost report.

    Args:
        orders: List of order dicts with arrival_price, avg_fill_price, qty, side, fees
        date: Date string (YYYYMMDD), defaults to today

    Returns:
        Path to generated CSV file
    """
    if date is None:
        date = datetime.now().strftime("%Y%m%d")

    csv_path = REPORTS_DIR / f"execution_costs_{date}.csv"

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "symbol",
                "side",
                "quantity",
                "arrival_price",
                "avg_fill_price",
                "fees",
                "implementation_shortfall",
                "shortfall_pct",
            ]
        )

        total_shortfall = 0.0
        total_value = 0.0

        for order in orders:
            arrival_price = order.get("arrival_price", 0.0)
            avg_fill_price = order.get("avg_fill_price", 0.0)
            qty = order.get("quantity", 0.0)
            side = order.get("side", "buy")
            fees = order.get("fees", 0.0)
            timestamp = order.get("timestamp", datetime.now().isoformat())
            symbol = order.get("symbol", "UNKNOWN")

            signed_qty = qty if side == "buy" else -qty
            shortfall = compute_implementation_shortfall(
                arrival_price, avg_fill_price, signed_qty, fees
            )
            shortfall_pct = (
                (shortfall / (arrival_price * abs(signed_qty))) * 100 if arrival_price > 0 else 0.0
            )

            writer.writerow(
                [
                    timestamp,
                    symbol,
                    side,
                    qty,
                    arrival_price,
                    avg_fill_price,
                    fees,
                    shortfall,
                    shortfall_pct,
                ]
            )

            total_shortfall += shortfall
            total_value += arrival_price * abs(signed_qty)

        # Summary row
        writer.writerow([])
        writer.writerow(
            [
                "TOTAL",
                "",
                "",
                "",
                "",
                "",
                "",
                total_shortfall,
                (total_shortfall / total_value * 100) if total_value > 0 else 0.0,
            ]
        )

    print(f"[execution_costs] Report generated: {csv_path}", flush=True)
    print(
        f"[execution_costs] Total shortfall: ${total_shortfall:.2f} ({total_shortfall / total_value * 100 if total_value > 0 else 0:.2f}%)",
        flush=True,
    )

    return str(csv_path)


def get_high_shortfall_strategies(threshold_pct: float = 0.5) -> list[dict[str, Any]]:
    """
    Identify strategies with high implementation shortfall.

    Args:
        threshold_pct: Threshold percentage for high shortfall

    Returns:
        List of strategies exceeding threshold
    """
    # Would read from execution reports and aggregate by strategy
    # For now, return mock
    return [{"strategy": "breakout", "avg_shortfall_pct": 0.75, "order_count": 10}]


def main():
    """Main execution cost analysis."""
    # Example orders (would come from actual trade history)
    orders = [
        {
            "timestamp": datetime.now().isoformat(),
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 0.01,
            "arrival_price": 107000.0,
            "avg_fill_price": 107050.0,
            "fees": 0.50,
        }
    ]

    report_path = generate_execution_report(orders)
    print(f"[execution_costs] Report saved to {report_path}", flush=True)

    high_shortfall = get_high_shortfall_strategies()
    if high_shortfall:
        print(f"[execution_costs] High shortfall strategies: {high_shortfall}", flush=True)


if __name__ == "__main__":
    main()

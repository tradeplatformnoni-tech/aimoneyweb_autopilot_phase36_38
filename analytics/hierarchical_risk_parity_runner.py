#!/usr/bin/env python3
"""
Hierarchical Risk Parity Runner - World-Class Implementation
-------------------------------------------------------------
Standalone runner for HRP optimizer with world-class stability.
Paper-mode compatible - only runs in PAPER_TRADING_MODE.
"""

import json
import logging
import os
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
sys.path.insert(0, str(ROOT))

# World-class utilities
try:
    from utils.agent_wrapper import world_class_agent
    from utils.health_check import HealthCheck
    from utils.retry import retry_with_backoff

    HAS_UTILS = True
except ImportError:
    HAS_UTILS = False

# Setup logging
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS / "hierarchical_risk_parity.log"

logger = logging.getLogger("hrp_runner")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(console_handler)

STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
DATA = ROOT / "data"

# Import HRP
try:
    from analytics.hierarchical_risk_parity import HierarchicalRiskParity

    HAS_HRP = True
except ImportError as e:
    HAS_HRP = False
    logger.error(f"❌ Failed to import HierarchicalRiskParity: {e}")


@retry_with_backoff(max_retries=3, base_delay=2.0)
def load_returns_data() -> Any | None:
    """Load returns data for HRP optimization."""
    try:
        import yfinance as yf

        # Get symbols from allocations
        alloc_file = RUNTIME / "allocations_override.json"
        if not alloc_file.exists():
            alloc_file = RUNTIME / "allocations.json"

        symbols = ["BTC-USD", "ETH-USD", "SPY", "QQQ"]  # Default
        if alloc_file.exists():
            try:
                data = json.loads(alloc_file.read_text())
                symbols = list(data.get("allocations", {}).keys())[:10]  # Limit to 10
            except:
                pass

        # Download data
        logger.info(f"📊 Loading returns data for {len(symbols)} symbols...")
        data = yf.download(symbols, period="1y", interval="1d", progress=False)

        if data.empty:
            logger.warning("⚠️ No data downloaded")
            return None

        # Use Close prices
        if len(symbols) == 1:
            closes = data["Close"].to_frame()
            closes.columns = symbols
        else:
            closes = data["Close"]

        return closes.dropna()

    except Exception as e:
        logger.error(f"❌ Failed to load returns data: {e}")
        raise


@world_class_agent("hierarchical_risk_parity", paper_mode_only=True)
def main():
    """Main HRP runner loop - world-class stability."""
    if not HAS_HRP:
        logger.error("❌ HierarchicalRiskParity not available")
        return

    logger.info("🚀 Hierarchical Risk Parity Runner starting...")
    logger.info("📊 Paper-mode compatible - will not run in LIVE_MODE")

    update_interval = 3600.0  # 1 hour

    while True:
        try:
            # Load returns data
            returns_df = load_returns_data()
            if returns_df is None or returns_df.empty:
                logger.warning("⚠️ No returns data available, waiting...")
                time.sleep(update_interval)
                continue

            # Initialize HRP
            try:
                hrp = HierarchicalRiskParity(returns_df)
            except Exception as e:
                logger.error(f"❌ Failed to initialize HRP: {e}")
                time.sleep(update_interval)
                continue

            # Optimize
            try:
                weights = hrp.optimize()
                logger.info(f"✅ HRP optimization complete: {len(weights)} assets")

                # Save weights
                output_file = RUNTIME / "hrp_allocations.json"
                output_data = {
                    "allocations": weights,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "method": "hierarchical_risk_parity",
                }
                output_file.write_text(json.dumps(output_data, indent=2))
                logger.info(f"💾 Saved HRP allocations to {output_file}")

            except Exception as e:
                logger.error(f"❌ HRP optimization failed: {e}")
                traceback.print_exc()

            # Wait before next update
            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 HRP Runner stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in HRP runner loop: {e}")
            traceback.print_exc()
            time.sleep(60)  # Wait 1 minute before retrying


if __name__ == "__main__":
    main()

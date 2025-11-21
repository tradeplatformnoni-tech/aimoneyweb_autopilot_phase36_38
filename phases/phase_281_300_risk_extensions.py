#!/usr/bin/env python3
"""
Phase 281-300: Risk Extensions - WORLD CLASS
==========================================
Einstein-level risk extensions:
- Position limits
- Exposure limits
- Concentration risk
- Leverage limits
- Sector limits
- Paper-mode compatible
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
for p in [STATE, RUNTIME, LOGS]:
    p.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "risk_extensions.log"
logger = logging.getLogger("risk_extensions")
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

# =============== WORLD-CLASS UTILITIES ==================
try:
    from utils.agent_wrapper import world_class_agent
    from utils.circuit_breaker import CircuitBreaker
    from utils.health_check import HealthCheck
    from utils.retry import retry_with_backoff
    from utils.state_manager import StateManager

    HAS_WORLD_CLASS_UTILS = True
except ImportError:
    HAS_WORLD_CLASS_UTILS = False
    logger.warning("⚠️ World-class utilities not available")

RISK_LIMITS_FILE = RUNTIME / "risk_limits.json"
PORTFOLIO_FILE = RUNTIME / "portfolio.json"


class RiskExtensions:
    """World-class risk extensions engine."""

    def __init__(self):
        """Initialize risk extensions."""
        self.limits = self.load_limits()
        self.state_manager = None
        if HAS_WORLD_CLASS_UTILS:
            try:
                self.state_manager = StateManager(
                    RUNTIME / "risk_extensions_state.json",
                    default_state={"limits": self.limits, "violations": []},
                    backup_count=24,
                    backup_interval=3600.0,
                )
            except Exception as e:
                logger.warning(f"⚠️ StateManager init failed: {e}")
        logger.info("✅ RiskExtensions initialized")

    def load_limits(self) -> dict[str, Any]:
        """Load risk limits."""
        default_limits = {
            "max_position_size_pct": 0.20,  # 20% max per position
            "max_sector_exposure_pct": 0.40,  # 40% max per sector
            "max_leverage": 1.0,  # No leverage in paper mode
            "max_concentration_pct": 0.30,  # 30% max concentration
            "max_daily_loss_pct": 0.05,  # 5% max daily loss
            "min_diversification": 5,  # Minimum 5 positions
        }

        if RISK_LIMITS_FILE.exists():
            try:
                file_limits = json.loads(RISK_LIMITS_FILE.read_text())
                default_limits.update(file_limits.get("limits", {}))
            except Exception as e:
                logger.warning(f"⚠️ Error loading limits: {e}")

        return default_limits

    def check_position_limit(
        self, symbol: str, quantity: float, price: float, total_equity: float
    ) -> dict[str, Any]:
        """Check if position exceeds size limit."""
        position_value = abs(quantity * price)
        position_pct = position_value / total_equity if total_equity > 0 else 0.0

        max_pct = self.limits["max_position_size_pct"]
        violation = position_pct > max_pct

        return {
            "symbol": symbol,
            "position_value": position_value,
            "position_pct": position_pct,
            "limit_pct": max_pct,
            "violation": violation,
            "allowed_quantity": (total_equity * max_pct) / price if price > 0 else 0.0,
        }

    def check_concentration_risk(
        self, positions: dict[str, dict[str, float]], total_equity: float
    ) -> dict[str, Any]:
        """Check concentration risk."""
        if not positions:
            return {"concentration_pct": 0.0, "violation": False}

        # Calculate top 3 positions
        position_values = []
        for symbol, pos in positions.items():
            qty = pos.get("quantity", 0.0)
            price = pos.get("price", 0.0)
            value = abs(qty * price)
            position_values.append((symbol, value))

        position_values.sort(key=lambda x: x[1], reverse=True)
        top3_value = sum([v for _, v in position_values[:3]])
        concentration_pct = top3_value / total_equity if total_equity > 0 else 0.0

        max_concentration = self.limits["max_concentration_pct"]
        violation = concentration_pct > max_concentration

        return {
            "concentration_pct": concentration_pct,
            "max_concentration_pct": max_concentration,
            "violation": violation,
            "top_positions": position_values[:3],
        }

    def check_sector_exposure(
        self, positions: dict[str, dict[str, Any]], sectors: dict[str, str]
    ) -> dict[str, Any]:
        """Check sector exposure limits."""
        sector_exposure = {}
        total_value = 0.0

        for symbol, pos in positions.items():
            sector = sectors.get(symbol, "UNKNOWN")
            qty = pos.get("quantity", 0.0)
            price = pos.get("price", 0.0)
            value = abs(qty * price)

            if sector not in sector_exposure:
                sector_exposure[sector] = 0.0
            sector_exposure[sector] += value
            total_value += value

        violations = {}
        max_sector_pct = self.limits["max_sector_exposure_pct"]

        for sector, value in sector_exposure.items():
            sector_pct = value / total_value if total_value > 0 else 0.0
            if sector_pct > max_sector_pct:
                violations[sector] = {
                    "exposure_pct": sector_pct,
                    "limit_pct": max_sector_pct,
                    "exposure_value": value,
                }

        return {
            "sector_exposure": {
                k: v / total_value if total_value > 0 else 0.0 for k, v in sector_exposure.items()
            },
            "violations": violations,
        }

    def check_diversification(self, positions: dict[str, Any]) -> dict[str, Any]:
        """Check diversification requirements."""
        active_positions = len(
            [p for p in positions.values() if abs(p.get("quantity", 0.0)) > 1e-6]
        )
        min_diversification = self.limits["min_diversification"]

        violation = active_positions < min_diversification

        return {
            "active_positions": active_positions,
            "min_required": min_diversification,
            "violation": violation,
        }


@world_class_agent(
    "risk_extensions", state_file=RUNTIME / "risk_extensions_state.json", paper_mode_only=True
)
def main():
    """Main risk extensions loop."""
    logger.info("🚀 Risk Extensions starting...")

    risk_ext = RiskExtensions()

    # Monitor loop
    while True:
        try:
            time.sleep(60)  # Check every minute

            # Load current portfolio
            if PORTFOLIO_FILE.exists():
                try:
                    portfolio = json.loads(PORTFOLIO_FILE.read_text())
                    positions = portfolio.get("positions", {})
                    equity = portfolio.get("equity", 100000.0)

                    # Check all risk limits
                    for symbol, pos in positions.items():
                        check = risk_ext.check_position_limit(
                            symbol, pos.get("quantity", 0.0), pos.get("price", 0.0), equity
                        )
                        if check["violation"]:
                            logger.warning(
                                f"⚠️ Position limit violation: {symbol} at {check['position_pct']:.1%} (limit: {check['limit_pct']:.1%})"
                            )

                    # Check concentration
                    concentration = risk_ext.check_concentration_risk(positions, equity)
                    if concentration["violation"]:
                        logger.warning(
                            f"⚠️ Concentration risk: {concentration['concentration_pct']:.1%} (limit: {concentration['max_concentration_pct']:.1%})"
                        )

                    # Check diversification
                    diversification = risk_ext.check_diversification(positions)
                    if diversification["violation"]:
                        logger.warning(
                            f"⚠️ Diversification: {diversification['active_positions']} positions (min: {diversification['min_required']})"
                        )

                except Exception as e:
                    logger.error(f"❌ Error checking risk limits: {e}")

        except KeyboardInterrupt:
            logger.info("🛑 Risk Extensions stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in risk extensions loop: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()

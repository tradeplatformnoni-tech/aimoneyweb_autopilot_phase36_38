#!/usr/bin/env python3
"""
Regime Detector - Phase 2000-2300 Enhanced
Detect market regimes (Bull, Bear, Sideways, High Volatility) for adaptive strategy switching
"""

import json
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd
except ImportError:
    np = None
    pd = None

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
DATA = ROOT / "data"
LOGS = ROOT / "logs"

REGIME_FILE = RUNTIME / "market_regime.json"

REGIMES = {
    "BULL": {"description": "Bull market - trending up", "risk_multiplier": 1.2},
    "BEAR": {"description": "Bear market - trending down", "risk_multiplier": 0.5},
    "SIDEWAYS": {"description": "Sideways market - range bound", "risk_multiplier": 0.8},
    "HIGH_VOL": {"description": "High volatility - uncertain", "risk_multiplier": 0.6},
}


def detect_regime(df: Any | None = None) -> dict[str, Any]:
    """Detect current market regime from historical data."""
    if df is None or pd is None:
        # Fallback: read from brain file
        brain_file = RUNTIME / "atlas_brain.json"
        if brain_file.exists():
            try:
                brain = json.loads(brain_file.read_text())
                confidence = brain.get("confidence", 0.5)
                risk_scaler = brain.get("risk_scaler", 1.0)

                if confidence < 0.3:
                    regime = "HIGH_VOL"
                elif risk_scaler < 0.7:
                    regime = "BEAR"
                elif risk_scaler > 1.1:
                    regime = "BULL"
                else:
                    regime = "SIDEWAYS"

                return {
                    "regime": regime,
                    "confidence": confidence,
                    "risk_scaler": risk_scaler,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            except:
                pass

        return {"regime": "UNKNOWN", "timestamp": datetime.now(UTC).isoformat()}

    # Analyze price trends
    if "equity" in df.columns and len(df) > 20:
        returns = df["equity"].pct_change().dropna()

        # Calculate metrics
        recent_returns = returns.tail(20)
        volatility = recent_returns.std()
        mean_return = recent_returns.mean()

        # Trend detection
        if len(df) >= 50:
            ma_short = df["equity"].tail(20).mean()
            ma_long = df["equity"].tail(50).mean()
            trend = ma_short - ma_long
        else:
            trend = 0

        # Classify regime
        if volatility > 0.05:  # High volatility threshold
            regime = "HIGH_VOL"
        elif trend > 0 and mean_return > 0:
            regime = "BULL"
        elif trend < 0 and mean_return < 0:
            regime = "BEAR"
        else:
            regime = "SIDEWAYS"

        return {
            "regime": regime,
            "volatility": float(volatility) if np else 0.0,
            "mean_return": float(mean_return) if np else 0.0,
            "trend": float(trend) if np else 0.0,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return {"regime": "UNKNOWN", "timestamp": datetime.now(UTC).isoformat()}


def get_regime_strategy(regime: str) -> dict[str, Any]:
    """Get recommended strategy adjustments for detected regime."""
    regime_info = REGIMES.get(regime, REGIMES["SIDEWAYS"])

    strategies = {
        "BULL": {"position_sizing": "increase", "risk_tolerance": "high", "hold_period": "longer"},
        "BEAR": {"position_sizing": "decrease", "risk_tolerance": "low", "hold_period": "shorter"},
        "SIDEWAYS": {
            "position_sizing": "neutral",
            "risk_tolerance": "medium",
            "hold_period": "medium",
        },
        "HIGH_VOL": {
            "position_sizing": "decrease",
            "risk_tolerance": "low",
            "hold_period": "shorter",
        },
    }

    return {
        "regime": regime,
        "risk_multiplier": regime_info["risk_multiplier"],
        "strategy": strategies.get(regime, strategies["SIDEWAYS"]),
        "description": regime_info["description"],
    }


def main():
    """Main regime detection loop."""
    print(
        f"[regime_detector] Starting regime detection @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    while True:
        try:
            # Load historical data
            perf_file = STATE / "performance_metrics.csv"
            df = None
            if perf_file.exists() and pd:
                try:
                    df = pd.read_csv(perf_file)
                except:
                    pass

            # Detect regime
            regime_data = detect_regime(df)
            regime = regime_data.get("regime", "UNKNOWN")

            # Get strategy recommendations
            strategy = get_regime_strategy(regime)

            # Combine and save
            result = {**regime_data, **strategy}

            REGIME_FILE.write_text(json.dumps(result, indent=2))

            # Emit regime change event (Phase 3900-4100: Event-Driven Architecture)
            try:
                from phases.phase_3900_4100_events import get_recent_events, process_event

                # Check if regime changed
                recent_events = get_recent_events("REGIME_CHANGE", limit=1)
                if not recent_events or recent_events[-1].get("data", {}).get("regime") != regime:
                    process_event(
                        "REGIME_CHANGE",
                        {
                            "regime": regime,
                            "risk_multiplier": strategy["risk_multiplier"],
                            "strategy_adjustments": strategy["strategy"],
                            "description": regime_data.get("description", ""),
                        },
                        source="regime_detector",
                    )
            except ImportError:
                pass  # Event system not available
            except Exception as e:
                print(f"[regime_detector] Event emission failed: {e}", flush=True)

            print(
                f"[regime_detector] Detected regime: {regime} (risk_multiplier: {strategy['risk_multiplier']})",
                flush=True,
            )

            time.sleep(300)  # Check every 5 minutes

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[regime_detector] Error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    main()

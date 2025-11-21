"""
Slippage Predictor (Meta-Model)
Predicts expected slippage to set smarter limits and route choices
World-class: ML model with graceful degradation
"""

import os
import pickle
from pathlib import Path
from typing import Any

MODEL_DIR = Path(os.path.expanduser("~")) / "neolight" / "models" / "slippage"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODEL_DIR / "slippage_model.pkl"


class MockSlippageModel:
    """Mock slippage model for when ML library is not available."""

    def predict(self, features: dict[str, Any]) -> float:
        """
        Predict slippage in basis points.

        Args:
            features: Dict with spread, depth, vol, time, route, size

        Returns:
            Predicted slippage in bps
        """
        spread_bps = features.get("spread_bps", 5.0)
        depth = features.get("depth", 50000.0)
        vol = features.get("volatility", 0.02)
        size = features.get("size", 0.01)
        route = features.get("route", "VWAP")

        # Heuristic model
        base_slippage = spread_bps * 0.5

        # Size impact (larger orders = more slippage)
        size_impact = (size / 0.1) * 2.0  # 2 bps per 0.1 BTC

        # Volatility impact
        vol_impact = vol * 100 * 0.5  # Convert to bps

        # Depth impact (less depth = more slippage)
        depth_factor = max(0.5, 10000.0 / depth)

        # Route impact
        route_factor = 1.2 if route == "TWAP" else 1.0

        predicted_slippage = (
            (base_slippage + size_impact + vol_impact) * depth_factor * route_factor
        )

        return max(0.1, min(predicted_slippage, 50.0))  # Clamp between 0.1 and 50 bps


# Load or create model
_model = None


def load_model():
    """Load persisted model or create mock."""
    global _model

    if MODEL_PATH.exists():
        try:
            with open(MODEL_PATH, "rb") as f:
                _model = pickle.load(f)
            print(f"[slippage_model] Loaded model from {MODEL_PATH}", flush=True)
        except Exception as e:
            print(f"[slippage_model] Failed to load model: {e}, using mock", flush=True)
            _model = MockSlippageModel()
    else:
        _model = MockSlippageModel()
        print("[slippage_model] No model found, using mock", flush=True)


def predict_slippage_bps(
    symbol: str,
    size: float,
    route: str,
    spread_bps: float | None = None,
    depth: float | None = None,
    volatility: float | None = None,
) -> float:
    """
    Predict slippage for a given order.

    Args:
        symbol: Trading symbol
        size: Order size
        route: Execution route (VWAP, TWAP)
        spread_bps: Optional spread (if not provided, will use defaults)
        depth: Optional depth (if not provided, will use defaults)
        volatility: Optional volatility (if not provided, will use defaults)

    Returns:
        Predicted slippage in basis points
    """
    if _model is None:
        load_model()

    features = {
        "spread_bps": spread_bps or 5.0,
        "depth": depth or 50000.0,
        "volatility": volatility or 0.02,
        "size": size,
        "route": route,
    }

    return _model.predict(features)


if __name__ == "__main__":
    # Test prediction
    slippage = predict_slippage_bps("BTC-USD", 0.01, "VWAP", spread_bps=5.0, depth=50000.0)
    print(f"Predicted slippage: {slippage:.2f} bps")

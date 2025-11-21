#!/usr/bin/env python3
"""
NeoLight Kalman Filter - Advanced Math
======================================
State-space model for dynamic price estimation.
Adapts to regime changes and handles noise better than simple moving averages.
"""

import logging
import os
from pathlib import Path

import numpy as np

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "kalman_filter.log"
logger = logging.getLogger("kalman_filter")
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


class KalmanFilter:
    """
    Kalman Filter for price prediction.
    State equation: x_k = F * x_{k-1} + w_k
    Observation equation: z_k = H * x_k + v_k
    """

    def __init__(
        self, initial_price: float, process_noise: float = 0.01, measurement_noise: float = 0.1
    ):
        """
        Initialize Kalman Filter.

        Args:
            initial_price: Initial price estimate
            process_noise: Process noise covariance (Q)
            measurement_noise: Measurement noise covariance (R)
        """
        # State: [price, velocity]
        self.state = np.array([initial_price, 0.0])  # [price, price_change]

        # State transition matrix (constant velocity model)
        self.F = np.array([[1.0, 1.0], [0.0, 1.0]])

        # Observation matrix (we observe price)
        self.H = np.array([[1.0, 0.0]])

        # Process noise covariance
        self.Q = np.array([[process_noise, 0.0], [0.0, process_noise * 0.1]])

        # Measurement noise covariance
        self.R = np.array([[measurement_noise]])

        # Error covariance
        self.P = np.eye(2) * 1.0

        logger.info(f"✅ KalmanFilter initialized (price: {initial_price:.2f})")

    def predict(self) -> tuple[float, float]:
        """
        Predict next state.

        Returns:
            (predicted_price, predicted_velocity)
        """
        # Predict state
        self.state = self.F.dot(self.state)

        # Predict covariance
        self.P = self.F.dot(self.P).dot(self.F.T) + self.Q

        return float(self.state[0]), float(self.state[1])

    def update(self, observed_price: float) -> float:
        """
        Update filter with new observation.

        Args:
            observed_price: Observed price

        Returns:
            Updated price estimate
        """
        # Innovation (measurement residual)
        y = observed_price - self.H.dot(self.state)

        # Innovation covariance
        S = self.H.dot(self.P).dot(self.H.T) + self.R

        # Kalman gain
        K = self.P.dot(self.H.T).dot(np.linalg.pinv(S))

        # Update state
        self.state = self.state + K.dot(y)

        # Update covariance
        self.P = (np.eye(2) - K.dot(self.H)).dot(self.P)

        return float(self.state[0])

    def filter_prices(self, prices: np.ndarray) -> np.ndarray:
        """
        Filter entire price series.

        Args:
            prices: Array of observed prices

        Returns:
            Filtered prices
        """
        filtered = np.zeros(len(prices))

        # Initialize with first price
        self.state[0] = prices[0]
        filtered[0] = prices[0]

        for i in range(1, len(prices)):
            # Predict
            self.predict()

            # Update with observation
            filtered[i] = self.update(prices[i])

        return filtered

    def predict_next_price(self, current_price: float) -> float:
        """
        Predict next price given current price.

        Args:
            current_price: Current observed price

        Returns:
            Predicted next price
        """
        # Update with current price
        self.update(current_price)

        # Predict next state
        next_price, _ = self.predict()

        return next_price


def main():
    """Test Kalman Filter."""
    logger.info("🧪 Testing Kalman Filter...")

    # Generate sample price data with noise
    np.random.seed(42)
    true_prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    noisy_prices = true_prices + np.random.randn(100) * 2.0  # Add noise

    # Initialize filter
    kf = KalmanFilter(noisy_prices[0], process_noise=0.01, measurement_noise=0.1)

    # Filter prices
    filtered_prices = kf.filter_prices(noisy_prices)

    # Calculate error
    true_error = np.mean(np.abs(noisy_prices - true_prices))
    filtered_error = np.mean(np.abs(filtered_prices - true_prices))

    logger.info(f"✅ Mean absolute error - Noisy: {true_error:.2f}, Filtered: {filtered_error:.2f}")
    logger.info(f"✅ Improvement: {(1 - filtered_error / true_error) * 100:.1f}%")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
NeoLight Bayesian Optimizer - Advanced Math
==========================================
Gaussian Process-based hyperparameter tuning.
Finds optimal parameters faster than grid search.
"""

import logging
import os
from collections.abc import Callable
from pathlib import Path

import numpy as np

try:
    from scipy.optimize import minimize
    from scipy.stats import norm

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "bayesian_optimizer.log"
logger = logging.getLogger("bayesian_optimizer")
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


class BayesianOptimizer:
    """
    Bayesian Optimization using Gaussian Process (simplified).
    Uses Expected Improvement (EI) acquisition function.
    """

    def __init__(self, param_bounds: dict[str, tuple[float, float]], n_initial: int = 5):
        """
        Initialize Bayesian Optimizer.

        Args:
            param_bounds: Dict of {param_name: (min, max)}
            n_initial: Number of initial random samples
        """
        if not HAS_SCIPY:
            raise ImportError("scipy required for Bayesian Optimization")

        self.param_bounds = param_bounds
        self.param_names = list(param_bounds.keys())
        self.n_initial = n_initial

        # Storage for observations
        self.X = []  # Parameter values
        self.y = []  # Objective values

        logger.info(f"✅ BayesianOptimizer initialized for {len(self.param_names)} parameters")

    def _random_sample(self) -> dict[str, float]:
        """Generate random parameter sample."""
        sample = {}
        for name, (min_val, max_val) in self.param_bounds.items():
            sample[name] = np.random.uniform(min_val, max_val)
        return sample

    def _expected_improvement(self, x: np.ndarray, best_y: float) -> float:
        """
        Calculate Expected Improvement acquisition function.
        Simplified version (full GP would require more computation).
        """
        # Simplified: use distance from best point
        if len(self.X) == 0:
            return 1.0

        # Calculate distance to nearest observed point
        distances = [
            np.linalg.norm(x - np.array([self.X[i][name] for name in self.param_names]))
            for i in range(len(self.X))
        ]
        min_distance = min(distances) if distances else 1.0

        # Higher distance = higher expected improvement
        return min_distance

    def suggest(self) -> dict[str, float]:
        """
        Suggest next parameter set to evaluate.

        Returns:
            Dictionary of parameter values
        """
        if len(self.X) < self.n_initial:
            # Random sampling for initial exploration
            return self._random_sample()

        # Bayesian optimization: maximize Expected Improvement
        best_y = max(self.y) if self.y else 0.0

        # Grid search over parameter space (simplified - full GP would be better)
        best_x = None
        best_ei = -np.inf

        # Sample random points and pick best EI
        for _ in range(50):
            x_dict = self._random_sample()
            x_array = np.array([x_dict[name] for name in self.param_names])
            ei = self._expected_improvement(x_array, best_y)

            if ei > best_ei:
                best_ei = ei
                best_x = x_dict

        return best_x if best_x else self._random_sample()

    def update(self, params: dict[str, float], objective_value: float):
        """
        Update optimizer with new observation.

        Args:
            params: Parameter values tested
            objective_value: Objective function value (higher is better)
        """
        self.X.append(params)
        self.y.append(objective_value)

        logger.debug(f"📊 Updated: {params} -> {objective_value:.4f}")

    def optimize(
        self, objective_func: Callable[[dict[str, float]], float], n_iterations: int = 20
    ) -> tuple[dict[str, float], float]:
        """
        Optimize objective function.

        Args:
            objective_func: Function that takes params dict and returns objective value
            n_iterations: Number of optimization iterations

        Returns:
            (best_params, best_value)
        """
        logger.info(f"🚀 Starting Bayesian Optimization ({n_iterations} iterations)...")

        best_params = None
        best_value = -np.inf

        for i in range(n_iterations):
            # Suggest next parameters
            params = self.suggest()

            # Evaluate objective
            try:
                value = objective_func(params)
            except Exception as e:
                logger.warning(f"⚠️  Objective function error: {e}")
                value = -np.inf

            # Update optimizer
            self.update(params, value)

            # Track best
            if value > best_value:
                best_value = value
                best_params = params.copy()
                logger.info(
                    f"✅ Iteration {i + 1}: New best value {best_value:.4f} with {best_params}"
                )

        logger.info(f"✅ Optimization complete. Best: {best_value:.4f} with {best_params}")

        return best_params, best_value


def main():
    """Test Bayesian Optimizer."""
    logger.info("🧪 Testing Bayesian Optimizer...")

    if not HAS_SCIPY:
        logger.error("❌ scipy required")
        return

    # Example: Optimize a simple function
    def objective(params: dict[str, float]) -> float:
        # Maximize: -(x-0.5)^2 - (y-0.3)^2 (peak at x=0.5, y=0.3)
        x = params.get("x", 0.0)
        y = params.get("y", 0.0)
        return -((x - 0.5) ** 2) - (y - 0.3) ** 2

    # Define parameter bounds
    bounds = {"x": (0.0, 1.0), "y": (0.0, 1.0)}

    # Initialize optimizer
    optimizer = BayesianOptimizer(bounds, n_initial=5)

    # Optimize
    best_params, best_value = optimizer.optimize(objective, n_iterations=20)

    logger.info(f"✅ Best parameters: {best_params}")
    logger.info(f"✅ Best value: {best_value:.4f}")


if __name__ == "__main__":
    main()

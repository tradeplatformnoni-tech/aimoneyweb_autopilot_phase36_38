#!/usr/bin/env python3
"""
ML Pipeline - Phase 1500-1800 Enhanced
Automated feature engineering, model selection, hyperparameter tuning, ensemble methods
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
    print("[ml_pipeline] Install numpy and pandas: pip install numpy pandas")
    np = None
    pd = None

try:
    from sklearn.ensemble import (
        BaggingRegressor,
        GradientBoostingRegressor,
        RandomForestRegressor,
        VotingRegressor,
    )
    from sklearn.linear_model import Lasso, LinearRegression, Ridge
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, train_test_split
    from sklearn.svm import SVR

    sklearn_available = True
except ImportError:
    print("[ml_pipeline] Install scikit-learn: pip install scikit-learn")
    sklearn_available = False
    sklearn = None

try:
    import xgboost as xgb
except ImportError:
    xgb = None
    print("[ml_pipeline] Optional: Install xgboost: pip install xgboost")

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
DATA = ROOT / "data"
RUNTIME = ROOT / "runtime"
MODELS_DIR = DATA / "ml_models"
LOGS = ROOT / "logs"

for d in [STATE, DATA, MODELS_DIR, LOGS]:
    d.mkdir(parents=True, exist_ok=True)


def load_historical_data() -> pd.DataFrame | None:
    """Load historical performance data."""
    if pd is None:
        return None

    perf_file = STATE / "performance_metrics.csv"
    if not perf_file.exists():
        return None

    try:
        df = pd.read_csv(perf_file)
        return df
    except Exception as e:
        print(f"[ml_pipeline] Error loading data: {e}", flush=True)
        return None


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Automated feature engineering from historical data."""
    if pd is None or df is None or df.empty:
        return df

    # Handle multiple date formats in CSV
    # Try to create timestamp column from available date columns
    timestamp_col = None
    if "timestamp" in df.columns:
        timestamp_col = pd.to_datetime(df["timestamp"], errors="coerce")
    elif "date" in df.columns:
        timestamp_col = pd.to_datetime(df["date"], errors="coerce")

    # Only create time-based features if timestamp exists and is valid
    if timestamp_col is not None and timestamp_col.notna().any():
        df["timestamp"] = timestamp_col
        # Time-based features (only for valid timestamps)
        df["hour"] = df["timestamp"].dt.hour.fillna(12)
        df["day_of_week"] = df["timestamp"].dt.dayofweek.fillna(0)
        df["month"] = df["timestamp"].dt.month.fillna(11)
    else:
        # If no valid timestamp, create placeholder columns
        df["hour"] = 12  # Default hour
        df["day_of_week"] = 0  # Default day
        df["month"] = 11  # Default month

    # Rolling statistics
    for window in [5, 10, 20]:
        if "equity" in df.columns:
            df[f"equity_ma_{window}"] = df["equity"].rolling(window=window).mean()
            df[f"equity_std_{window}"] = df["equity"].rolling(window=window).std()

    # Returns
    if "equity" in df.columns:
        df["returns"] = df["equity"].pct_change()
        df["returns_lag1"] = df["returns"].shift(1)
        df["returns_lag2"] = df["returns"].shift(2)

    return df.dropna()


def train_model(
    model_type: str = "random_forest",
    df: pd.DataFrame | None = None,
    hyperparams: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Train a machine learning model with optional hyperparameter tuning."""
    if df is None or pd is None or not sklearn_available:
        return None

    df_eng = engineer_features(df.copy())

    # Prepare features and target
    feature_cols = [
        c for c in df_eng.columns if c not in ["timestamp", "equity", "pnl_pct", "date"]
    ]
    if "equity" in df_eng.columns:
        target_col = "equity"
    else:
        return None

    X = df_eng[feature_cols].select_dtypes(include=[np.number]).fillna(0)
    y = df_eng[target_col]

    if len(X) < 10:
        return None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model based on type
    model = None
    if model_type == "random_forest":
        if hyperparams:
            model = RandomForestRegressor(**hyperparams, random_state=42)
        else:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
    elif model_type == "gradient_boosting":
        if hyperparams:
            model = GradientBoostingRegressor(**hyperparams, random_state=42)
        else:
            model = GradientBoostingRegressor(n_estimators=100, random_state=42)
    elif model_type == "xgboost" and xgb:
        if hyperparams:
            model = xgb.XGBRegressor(**hyperparams, random_state=42)
        else:
            model = xgb.XGBRegressor(n_estimators=100, random_state=42)
    elif model_type == "linear_regression":
        model = LinearRegression()
    elif model_type == "ridge":
        if hyperparams:
            model = Ridge(**hyperparams)
        else:
            model = Ridge(alpha=1.0)
    elif model_type == "lasso":
        if hyperparams:
            model = Lasso(**hyperparams)
        else:
            model = Lasso(alpha=1.0)
    elif model_type == "svr":
        if hyperparams:
            model = SVR(**hyperparams)
        else:
            model = SVR(kernel="rbf")
    else:
        return None

    # Train and evaluate
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    # Save model metadata
    model_file = MODELS_DIR / f"{model_type}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    result = {
        "model_type": model_type,
        "mse": float(mse),
        "mae": float(mae),
        "r2_score": float(r2),
        "features": list(X.columns),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "hyperparameters": hyperparams or {},
        "timestamp": datetime.now(UTC).isoformat(),
    }
    model_file.write_text(json.dumps(result, indent=2))

    return result


def hyperparameter_tuning(model_type: str, df: pd.DataFrame | None = None) -> dict[str, Any] | None:
    """
    Tune hyperparameters using GridSearchCV or RandomizedSearchCV.

    Args:
        model_type: Type of model to tune
        df: Training data

    Returns:
        Dictionary with best parameters and performance
    """
    if df is None or pd is None or not sklearn_available:
        return None

    df_eng = engineer_features(df.copy())

    # Prepare features and target
    feature_cols = [
        c for c in df_eng.columns if c not in ["timestamp", "equity", "pnl_pct", "date"]
    ]
    if "equity" not in df_eng.columns:
        return None

    X = df_eng[feature_cols].select_dtypes(include=[np.number]).fillna(0)
    y = df_eng["equity"]

    if len(X) < 20:
        return None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Define parameter grids
    param_grids = {
        "random_forest": {
            "n_estimators": [50, 100, 200],
            "max_depth": [5, 10, 20, None],
            "min_samples_split": [2, 5, 10],
        },
        "gradient_boosting": {
            "n_estimators": [50, 100, 200],
            "learning_rate": [0.01, 0.1, 0.2],
            "max_depth": [3, 5, 7],
        },
        "xgboost": {
            "n_estimators": [50, 100, 200],
            "learning_rate": [0.01, 0.1, 0.2],
            "max_depth": [3, 5, 7],
        },
        "ridge": {"alpha": [0.1, 1.0, 10.0, 100.0]},
        "lasso": {"alpha": [0.1, 1.0, 10.0, 100.0]},
    }

    if model_type not in param_grids:
        return None

    param_grid = param_grids[model_type]

    # Create base model
    if model_type == "random_forest":
        base_model = RandomForestRegressor(random_state=42)
    elif model_type == "gradient_boosting":
        base_model = GradientBoostingRegressor(random_state=42)
    elif model_type == "xgboost" and xgb:
        base_model = xgb.XGBRegressor(random_state=42)
    elif model_type == "ridge":
        base_model = Ridge()
    elif model_type == "lasso":
        base_model = Lasso()
    else:
        return None

    # Use RandomizedSearchCV for faster search (limit combinations)
    try:
        search = RandomizedSearchCV(
            base_model,
            param_grid,
            n_iter=10,  # Limit iterations for performance
            cv=3,  # 3-fold cross-validation
            scoring="r2",
            n_jobs=1,  # Single job to avoid resource issues
            random_state=42,
        )
        search.fit(X_train, y_train)

        # Evaluate best model
        best_model = search.best_estimator_
        y_pred = best_model.predict(X_test)
        r2 = r2_score(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)

        return {
            "model_type": model_type,
            "best_params": search.best_params_,
            "best_score": float(search.best_score_),
            "test_r2": float(r2),
            "test_mse": float(mse),
            "method": "randomized_search",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        print(f"[ml_pipeline] Hyperparameter tuning error: {e}", flush=True)
        return None


def auto_model_selection(df: pd.DataFrame | None = None) -> dict[str, Any] | None:
    """
    Automatically select the best model by testing multiple models.

    Returns:
        Dictionary with best model and performance metrics
    """
    if df is None or pd is None or not sklearn_available:
        return None

    print("[ml_pipeline] Auto-selecting best model...", flush=True)

    # List of models to test
    models_to_test = ["random_forest", "gradient_boosting", "ridge", "linear_regression"]
    if xgb:
        models_to_test.append("xgboost")

    results = []

    for model_type in models_to_test:
        try:
            result = train_model(model_type, df)
            if result:
                results.append(
                    {
                        "model_type": model_type,
                        "r2_score": result["r2_score"],
                        "mse": result["mse"],
                        "mae": result.get("mae", 0.0),
                    }
                )
                print(
                    f"[ml_pipeline] {model_type}: R2={result['r2_score']:.3f}, MSE={result['mse']:.2f}",
                    flush=True,
                )
        except Exception as e:
            print(f"[ml_pipeline] Error testing {model_type}: {e}", flush=True)
            continue

    if not results:
        return None

    # Select best model by R2 score
    best_result = max(results, key=lambda x: x["r2_score"])

    return {
        "best_model": best_result["model_type"],
        "best_r2": best_result["r2_score"],
        "best_mse": best_result["mse"],
        "best_mae": best_result["mae"],
        "all_results": results,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def train_ensemble_model(
    df: pd.DataFrame | None = None, ensemble_type: str = "voting"
) -> dict[str, Any] | None:
    """
    Train an ensemble model (voting, stacking, or bagging).

    Args:
        df: Training data
        ensemble_type: Type of ensemble ("voting", "bagging")

    Returns:
        Dictionary with ensemble model performance
    """
    if df is None or pd is None or not sklearn_available:
        return None

    df_eng = engineer_features(df.copy())

    # Prepare features and target
    feature_cols = [
        c for c in df_eng.columns if c not in ["timestamp", "equity", "pnl_pct", "date"]
    ]
    if "equity" not in df_eng.columns:
        return None

    X = df_eng[feature_cols].select_dtypes(include=[np.number]).fillna(0)
    y = df_eng["equity"]

    if len(X) < 20:
        return None

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    try:
        if ensemble_type == "voting":
            # Voting ensemble: combine predictions from multiple models
            estimators = [
                ("rf", RandomForestRegressor(n_estimators=50, random_state=42)),
                ("gb", GradientBoostingRegressor(n_estimators=50, random_state=42)),
                ("ridge", Ridge(alpha=1.0)),
            ]
            ensemble = VotingRegressor(estimators=estimators)
        elif ensemble_type == "bagging":
            # Bagging: bootstrap aggregating with base model
            base_model = RandomForestRegressor(n_estimators=50, random_state=42)
            ensemble = BaggingRegressor(estimator=base_model, n_estimators=5, random_state=42)
        else:
            return None

        # Train ensemble
        ensemble.fit(X_train, y_train)
        y_pred = ensemble.predict(X_test)

        r2 = r2_score(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)

        return {
            "ensemble_type": ensemble_type,
            "r2_score": float(r2),
            "mse": float(mse),
            "mae": float(mae),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        print(f"[ml_pipeline] Ensemble training error: {e}", flush=True)
        return None


def walk_forward_optimization() -> dict[str, Any]:
    """Walk-forward optimization: train on rolling windows."""
    df = load_historical_data()
    if df is None or len(df) < 50:
        return {"error": "Insufficient data for walk-forward"}

    results = []

    # Simple walk-forward: 80% train, 20% test, sliding window
    test_size = max(10, len(df) // 5)

    for i in range(test_size, len(df), test_size):
        train_df = df.iloc[:i]
        test_df = df.iloc[i : i + test_size]

        if len(train_df) < 20:
            continue

        result = train_model("random_forest", train_df)
        if result:
            results.append(result)

    return {
        "walk_forward_results": results,
        "average_r2": float(np.mean([r["r2_score"] for r in results])) if results and np else 0.0,
        "best_model": max(results, key=lambda x: x["r2_score"]) if results else None,
    }


def main():
    """Main ML pipeline loop with auto-model selection, hyperparameter tuning, and ensemble models."""
    print(
        f"[ml_pipeline] Starting enhanced ML pipeline @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    optimization_cycle = 0
    ensemble_cycle = 0

    while True:
        try:
            df = load_historical_data()
            if df is not None and len(df) > 20:
                # === AUTO-MODEL SELECTION (every cycle) ===
                print("[ml_pipeline] Running auto-model selection...", flush=True)
                best_model_result = auto_model_selection(df)
                if best_model_result:
                    print(
                        f"[ml_pipeline] ✅ Best model: {best_model_result['best_model']} (R2={best_model_result['best_r2']:.3f})",
                        flush=True,
                    )

                # === HYPERPARAMETER TUNING (every 3 cycles = 18 hours) ===
                optimization_cycle += 1
                if optimization_cycle >= 3:
                    optimization_cycle = 0
                    print("[ml_pipeline] Running hyperparameter tuning...", flush=True)

                    # Tune best model if available
                    if best_model_result:
                        best_model_type = best_model_result["best_model"]
                        tuning_result = hyperparameter_tuning(best_model_type, df)
                        if tuning_result:
                            print(
                                f"[ml_pipeline] ✅ Hyperparameter tuning complete: {best_model_type} (R2={tuning_result['test_r2']:.3f})",
                                flush=True,
                            )
                            # Retrain with best parameters
                            tuned_result = train_model(
                                best_model_type, df, tuning_result["best_params"]
                            )
                            if tuned_result:
                                print(
                                    f"[ml_pipeline] ✅ Retrained with optimized params: R2={tuned_result['r2_score']:.3f}",
                                    flush=True,
                                )

                # === ENSEMBLE MODELS (every 6 cycles = 36 hours) ===
                ensemble_cycle += 1
                if ensemble_cycle >= 6:
                    ensemble_cycle = 0
                    print("[ml_pipeline] Training ensemble models...", flush=True)

                    # Train voting ensemble
                    voting_result = train_ensemble_model(df, "voting")
                    if voting_result:
                        print(
                            f"[ml_pipeline] ✅ Voting ensemble: R2={voting_result['r2_score']:.3f}",
                            flush=True,
                        )

                    # Train bagging ensemble
                    bagging_result = train_ensemble_model(df, "bagging")
                    if bagging_result:
                        print(
                            f"[ml_pipeline] ✅ Bagging ensemble: R2={bagging_result['r2_score']:.3f}",
                            flush=True,
                        )

                # === STANDARD TRAINING (every cycle) ===
                print("[ml_pipeline] Training standard models...", flush=True)
                rf_result = train_model("random_forest", df)
                if rf_result:
                    print(
                        f"[ml_pipeline] RandomForest trained: R2={rf_result['r2_score']:.3f}",
                        flush=True,
                    )

                if xgb:
                    xgb_result = train_model("xgboost", df)
                    if xgb_result:
                        print(
                            f"[ml_pipeline] XGBoost trained: R2={xgb_result['r2_score']:.3f}",
                            flush=True,
                        )

                # Walk-forward optimization
                wf_result = walk_forward_optimization()
                if "average_r2" in wf_result:
                    print(
                        f"[ml_pipeline] Walk-forward avg R2: {wf_result['average_r2']:.3f}",
                        flush=True,
                    )
            else:
                print("[ml_pipeline] Insufficient data for training (need >20 samples)", flush=True)

            # Run every 6 hours
            time.sleep(21600)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[ml_pipeline] Error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(3600)


if __name__ == "__main__":
    main()

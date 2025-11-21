#!/usr/bin/env python3
"""
Replay Engine - Phase 1100-1300
Historical replay loader for backtesting and AI learning
Uses TensorFlow/PyTorch to simulate past scenarios
Auto-adjusts Guardian risk policy based on backtest confidence
"""

import json
import os
import time
import traceback
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import csv

try:
    import numpy as np
except ImportError:
    np = None
    print("[replay_engine] numpy not available; install: pip install numpy")

try:
    import tensorflow as tf
except ImportError:
    tf = None
    print("[replay_engine] TensorFlow not available; install: pip install tensorflow")

try:
    import torch
except ImportError:
    torch = None
    print("[replay_engine] PyTorch not available; install: pip install torch")

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
DATA = ROOT / "data"
LOGS = ROOT / "logs"
BACKTEST_DIR = DATA / "backtests"
BACKTEST_SUMMARY_FILE = STATE / "backtest_summary.json"
BACKTEST_LOG_FILE = LOGS / "backtest_summary.log"


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


WF_TRAIN_WINDOW = max(10, _int_env("BACKTEST_WF_TRAIN_WINDOW", 60))
WF_TEST_WINDOW = max(5, _int_env("BACKTEST_WF_TEST_WINDOW", 20))
WF_STEP_SIZE = max(1, _int_env("BACKTEST_WF_STEP_SIZE", 10))
MC_SIMULATIONS = max(100, _int_env("BACKTEST_MC_SIMULATIONS", 1000))
MC_BOOTSTRAP = os.getenv("BACKTEST_MC_BOOTSTRAP", "false").lower() == "true"
MC_BLOCK_SIZE = max(5, _int_env("BACKTEST_MC_BLOCK_SIZE", 10))
TRANSACTION_COMMISSION = _float_env("BACKTEST_COMMISSION_BPS", 0.0002)
TRANSACTION_SLIPPAGE = _float_env("BACKTEST_SLIPPAGE_BPS", 0.0001)
MIN_RETURN_THRESHOLD = _float_env("BACKTEST_MIN_ABS_RETURN", 0.0001)

for d in [STATE, RUNTIME, DATA, BACKTEST_DIR, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

PNL_CSV = STATE / "pnl_history.csv"
PERF_CSV = STATE / "performance_metrics.csv"


def load_historical_data(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Load historical performance data from CSV files."""
    data = []
    
    try:
        if PNL_CSV.exists():
            with open(PNL_CSV, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Filter by date range if provided
                    if start_date and row.get("timestamp", "") < start_date:
                        continue
                    if end_date and row.get("timestamp", "") > end_date:
                        continue
                    data.append(row)
    except Exception as e:
        print(f"[replay_engine] Error loading PnL: {e}", flush=True)
    
    try:
        if PERF_CSV.exists():
            with open(PERF_CSV, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if start_date and row.get("timestamp", "") < start_date:
                        continue
                    if end_date and row.get("timestamp", "") > end_date:
                        continue
                    data.append(row)
    except Exception as e:
        print(f"[replay_engine] Error loading perf: {e}", flush=True)
    
    return data


def simulate_scenario(data: List[Dict[str, Any]], risk_policy: Dict[str, float]) -> Dict[str, Any]:
    """Simulate a trading scenario with given risk policy."""
    if not data:
        return {"error": "No historical data available"}
    
    # Simple simulation: apply risk_scaler to returns
    returns = []
    for point in data:
        try:
            equity = float(point.get("equity", 0))
            pnl_pct = float(point.get("pnl_pct", 0))
            risk_scaler = risk_policy.get("risk_scaler", 1.0)
            adjusted_return = pnl_pct * risk_scaler
            returns.append(adjusted_return)
        except (ValueError, TypeError):
            continue
    
    if not returns:
        return {"error": "No valid returns calculated"}
    
    total_return = sum(returns)
    sharpe = np.std(returns) if np and len(returns) > 1 else 0.0
    if sharpe > 0:
        sharpe = np.mean(returns) / sharpe
    
    return {
        "total_return": total_return,
        "sharpe": float(sharpe) if np else 0.0,
        "max_drawdown": min(returns) if returns else 0.0,
        "win_rate": len([r for r in returns if r > 0]) / len(returns) if returns else 0.0,
        "data_points": len(returns),
    }


def tensorflow_backtest(
    data: List[Dict[str, Any]], model_type: str = "simple"
) -> Optional[Dict[str, Any]]:
    """Backtest using TensorFlow (if available)."""
    if tf is None:
        return None
    
    try:
        # Placeholder: build simple model
        # In production, would train on historical patterns
        if model_type == "simple":
            returns = [float(p.get("pnl_pct", 0)) for p in data if p.get("pnl_pct")]
            if returns:
                mean_return = np.mean(returns) if np else sum(returns) / len(returns)
                return {"predicted_return": float(mean_return), "method": "tensorflow_simple"}
    except Exception as e:
        print(f"[replay_engine] TensorFlow backtest error: {e}", flush=True)
    
    return None


def pytorch_backtest(
    data: List[Dict[str, Any]], model_type: str = "simple"
) -> Optional[Dict[str, Any]]:
    """Backtest using PyTorch (if available)."""
    if torch is None:
        return None
    
    try:
        returns = [float(p.get("pnl_pct", 0)) for p in data if p.get("pnl_pct")]
        if returns:
            mean_return = np.mean(returns) if np else sum(returns) / len(returns)
            return {"predicted_return": float(mean_return), "method": "pytorch_simple"}
    except Exception as e:
        print(f"[replay_engine] PyTorch backtest error: {e}", flush=True)
    
    return None


def auto_adjust_guardian_policy(backtest_results: Dict[str, Any]) -> Dict[str, float]:
    """Auto-adjust Guardian risk policy based on backtest confidence."""
    confidence = backtest_results.get("confidence", 0.5)
    sharpe = backtest_results.get("sharpe", 0.0)
    win_rate = backtest_results.get("win_rate", 0.5)
    
    # Adjust risk_scaler based on performance
    base_risk = 1.0
    if sharpe > 1.5:
        risk_adjustment = 1.2  # Increase risk if Sharpe is high
    elif sharpe < 0.5:
        risk_adjustment = 0.6  # Decrease risk if Sharpe is low
    else:
        risk_adjustment = 1.0
    
    # Factor in win rate
    win_rate_adjustment = win_rate * 0.3 + 0.7  # 0.7 to 1.0 multiplier
    
    new_risk_scaler = base_risk * risk_adjustment * win_rate_adjustment
    new_risk_scaler = max(0.4, min(1.2, new_risk_scaler))  # Clamp to valid range
    
    new_confidence = min(0.9, max(0.05, confidence * (1 + (sharpe - 1.0) * 0.1)))
    
    adjusted_policy = {
        "risk_scaler": round(new_risk_scaler, 3),
        "confidence": round(new_confidence, 3),
        "updated": datetime.now(timezone.utc).isoformat() + "Z",
        "source": "replay_engine_backtest",
    }
    
    return adjusted_policy


def walk_forward_optimization(
    data: List[Dict[str, Any]], train_window: int = 60, test_window: int = 20, step_size: int = 10
) -> Dict[str, Any]:
    """
    Walk-forward optimization: train on rolling windows, test on out-of-sample data.
    
    Args:
        data: Historical data
        train_window: Number of data points for training (default: 60 days)
        test_window: Number of data points for testing (default: 20 days)
        step_size: Number of points to shift forward each iteration (default: 10)
    
    Returns:
        Dictionary with walk-forward optimization results
    """
    if not data or len(data) < train_window + test_window:
        return {"error": "Insufficient data for walk-forward optimization"}
    
    if not np:
        return {"error": "numpy required for walk-forward optimization"}
    
    results = []
    total_iterations = max(1, (len(data) - train_window - test_window) // step_size)
    
    print(
        f"[replay_engine] Walk-forward optimization: {total_iterations} iterations (train={train_window}, test={test_window})",
        flush=True,
    )
    
    for i in range(0, len(data) - train_window - test_window, step_size):
        train_data = data[i : i + train_window]
        test_data = data[i + train_window : i + train_window + test_window]
        
        if len(train_data) < train_window or len(test_data) < test_window:
            continue
        
        # Train on training window
        train_returns = []
        for point in train_data:
            try:
                pnl_pct = float(point.get("pnl_pct", 0))
                train_returns.append(pnl_pct)
            except (ValueError, TypeError):
                continue
        
        if not train_returns:
            continue
        
        # Calculate training statistics
        train_mean = np.mean(train_returns)
        train_std = np.std(train_returns) if len(train_returns) > 1 else 0.0
        train_sharpe = train_mean / train_std if train_std > 0 else 0.0
        
        # Test on test window
        test_returns = []
        for point in test_data:
            try:
                pnl_pct = float(point.get("pnl_pct", 0))
                test_returns.append(pnl_pct)
            except (ValueError, TypeError):
                continue
        
        if not test_returns:
            continue
        
        test_mean = np.mean(test_returns)
        test_std = np.std(test_returns) if len(test_returns) > 1 else 0.0
        test_sharpe = test_mean / test_std if test_std > 0 else 0.0
        test_total_return = sum(test_returns)
        
        results.append(
            {
            "iteration": len(results) + 1,
            "train_start": i,
            "train_end": i + train_window,
            "test_start": i + train_window,
            "test_end": i + train_window + test_window,
            "train_sharpe": float(train_sharpe),
            "test_sharpe": float(test_sharpe),
            "test_total_return": float(test_total_return),
                "test_std": float(test_std),
            }
        )
    
    if not results:
        return {"error": "No valid walk-forward iterations completed"}
    
    # Aggregate results
    avg_test_sharpe = np.mean([r["test_sharpe"] for r in results])
    avg_test_return = np.mean([r["test_total_return"] for r in results])
    best_iteration = max(results, key=lambda x: x["test_sharpe"])
    
    return {
        "total_iterations": len(results),
        "average_test_sharpe": float(avg_test_sharpe),
        "average_test_return": float(avg_test_return),
        "best_iteration": best_iteration,
        "all_results": results,
    }


def monte_carlo_simulation(
    data: List[Dict[str, Any]],
    num_simulations: int = MC_SIMULATIONS,
    risk_policy: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Monte Carlo simulation: generate random scenarios based on historical returns distribution.
    
    Args:
        data: Historical data
        num_simulations: Number of Monte Carlo simulations (default: 1000)
        risk_policy: Risk policy to apply
    
    Returns:
        Dictionary with Monte Carlo simulation results
    """
    if not data:
        return {"error": "No historical data available for Monte Carlo simulation"}
    
    if not np:
        return {"error": "numpy required for Monte Carlo simulation"}
    
    # Extract returns from historical data
    returns = []
    for point in data:
        try:
            pnl_pct = float(point.get("pnl_pct", 0))
            returns.append(pnl_pct)
        except (ValueError, TypeError):
            continue
    
    if not returns or len(returns) < 10:
        return {"error": "Insufficient returns data for Monte Carlo simulation"}
    
    # Calculate distribution parameters
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    risk_scaler = risk_policy.get("risk_scaler", 1.0) if risk_policy else 1.0
    
    # Run Monte Carlo simulations
    simulation_results = []
    for _ in range(num_simulations):
        # Generate random returns based on configuration
        if MC_BOOTSTRAP:
            simulated_returns = []
            while len(simulated_returns) < len(returns):
                start_idx = random.randint(0, max(0, len(returns) - MC_BLOCK_SIZE))
                block = returns[start_idx : start_idx + MC_BLOCK_SIZE]
                simulated_returns.extend(block)
            simulated_returns = np.array(simulated_returns[: len(returns)], dtype=float)
        else:
        simulated_returns = np.random.normal(mean_return, std_return, len(returns))
        simulated_returns = simulated_returns * risk_scaler
        simulated_returns = apply_transaction_costs(
            list(simulated_returns),
            commission_per_trade=TRANSACTION_COMMISSION,
            slippage_per_trade=TRANSACTION_SLIPPAGE,
            min_abs_return=MIN_RETURN_THRESHOLD,
        )
        simulated_returns = np.array(simulated_returns, dtype=float)
        
        # Calculate metrics
        total_return = float(np.sum(simulated_returns))
        std_sim = float(np.std(simulated_returns)) if len(simulated_returns) > 1 else 0.0
        sharpe = float(np.mean(simulated_returns) / std_sim) if std_sim > 0 else 0.0
        max_drawdown = float(np.min(simulated_returns))
        win_rate = float(len([r for r in simulated_returns if r > 0]) / len(simulated_returns))
        
        simulation_results.append(
            {
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
                "win_rate": win_rate,
            }
        )
    
    # Calculate statistics
    total_returns = [r["total_return"] for r in simulation_results]
    sharpe_ratios = [r["sharpe"] for r in simulation_results]
    
    # Percentiles
    def percentile(values: List[float], p: float) -> float:
        sorted_vals = sorted(values)
        idx = int(len(sorted_vals) * p)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]
    
    return {
        "num_simulations": num_simulations,
        "mean_total_return": float(np.mean(total_returns)),
        "std_total_return": float(np.std(total_returns)),
        "mean_sharpe": float(np.mean(sharpe_ratios)),
        "percentile_5": float(percentile(total_returns, 0.05)),
        "percentile_25": float(percentile(total_returns, 0.25)),
        "percentile_50": float(percentile(total_returns, 0.50)),
        "percentile_75": float(percentile(total_returns, 0.75)),
        "percentile_95": float(percentile(total_returns, 0.95)),
        "probability_positive": float(
            len([r for r in total_returns if r > 0]) / len(total_returns)
        ),
    }


def apply_transaction_costs(
    returns: List[float],
    commission_per_trade: float = 0.0002,  # 2 bps (0.02%) per trade
    slippage_per_trade: float = 0.0001,  # 1 bp (0.01%) slippage
    frequency: int = 1,  # Trades per period (1 = every period)
    min_abs_return: float = MIN_RETURN_THRESHOLD,
) -> List[float]:
    """
    Apply transaction costs (commissions + slippage) to returns.
    
    Args:
        returns: List of returns
        commission_per_trade: Commission cost per trade (default: 2 bps)
        slippage_per_trade: Slippage cost per trade (default: 1 bp)
        frequency: Number of trades per period (default: 1)
    
    Returns:
        List of returns with transaction costs applied
    """
    if not returns:
        return returns
    
    total_cost_per_trade = commission_per_trade + slippage_per_trade
    adjusted_returns = []
    
    for i, ret in enumerate(returns):
        # Apply transaction costs only on active trading periods
        if i % frequency == 0 and abs(ret) > min_abs_return:  # Only apply if there's actual trading
            adjusted_ret = ret - total_cost_per_trade
        else:
            adjusted_ret = ret
        adjusted_returns.append(adjusted_ret)
    
    return adjusted_returns


def simulate_scenario_with_costs(
    data: List[Dict[str, Any]],
    risk_policy: Dict[str, float],
    commission: float = 0.0002,
    slippage: float = 0.0001,
) -> Dict[str, Any]:
    """
    Simulate trading scenario with transaction costs applied.
    
    Args:
        data: Historical data
        risk_policy: Risk policy
        commission: Commission per trade (default: 2 bps)
        slippage: Slippage per trade (default: 1 bp)
    
    Returns:
        Simulation results with transaction costs
    """
    if not data:
        return {"error": "No historical data available"}
    
    # Extract returns
    returns = []
    for point in data:
        try:
            pnl_pct = float(point.get("pnl_pct", 0))
            risk_scaler = risk_policy.get("risk_scaler", 1.0)
            adjusted_return = pnl_pct * risk_scaler
            returns.append(adjusted_return)
        except (ValueError, TypeError):
            continue
    
    if not returns:
        return {"error": "No valid returns calculated"}
    
    # Apply transaction costs
    returns_with_costs = apply_transaction_costs(
        returns,
        commission_per_trade=commission,
        slippage_per_trade=slippage,
        min_abs_return=MIN_RETURN_THRESHOLD,
    )
    
    # Calculate metrics
    if np:
        total_return = float(np.sum(returns_with_costs))
        std_returns = float(np.std(returns_with_costs)) if len(returns_with_costs) > 1 else 0.0
        mean_return = float(np.mean(returns_with_costs))
        sharpe = mean_return / std_returns if std_returns > 0 else 0.0
        max_drawdown = float(np.min(returns_with_costs))
        win_rate = float(len([r for r in returns_with_costs if r > 0]) / len(returns_with_costs))
    else:
        total_return = sum(returns_with_costs)
        sharpe = 0.0
        max_drawdown = min(returns_with_costs)
        win_rate = len([r for r in returns_with_costs if r > 0]) / len(returns_with_costs)
    
    # Calculate cost impact
    total_return_no_costs = sum(returns)
    cost_impact = total_return_no_costs - total_return
    
    return {
        "total_return": total_return,
        "total_return_no_costs": total_return_no_costs,
        "cost_impact": cost_impact,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "data_points": len(returns),
        "commission_per_trade": commission,
        "slippage_per_trade": slippage,
    }


def summarize_backtest(result: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a compact summary for dashboards and logs."""
    simulation_with_costs = result.get("simulation_with_costs") or {}
    walk_forward = result.get("walk_forward") or {}
    monte_carlo = result.get("monte_carlo") or {}
    best_iteration = walk_forward.get("best_iteration") or {}

    summary = {
        "timestamp": result.get("timestamp"),
        "data_points": result.get("data_points", 0),
        "total_return_with_costs": simulation_with_costs.get("total_return"),
        "sharpe_with_costs": simulation_with_costs.get("sharpe"),
        "win_rate_with_costs": simulation_with_costs.get("win_rate"),
        "cost_impact": simulation_with_costs.get("cost_impact"),
        "average_walk_forward_sharpe": walk_forward.get("average_test_sharpe"),
        "best_walk_forward_sharpe": best_iteration.get("test_sharpe"),
        "monte_carlo_prob_positive": monte_carlo.get("probability_positive"),
        "monte_carlo_percentile_5": monte_carlo.get("percentile_5"),
        "monte_carlo_percentile_95": monte_carlo.get("percentile_95"),
        "current_risk_scaler": (result.get("current_policy") or {}).get("risk_scaler"),
        "current_confidence": (result.get("current_policy") or {}).get("confidence"),
    }

    sharpe_value = summary.get("sharpe_with_costs")
    prob_positive = summary.get("monte_carlo_prob_positive")
    walk_forward_avg = summary.get("average_walk_forward_sharpe")
    if (
        isinstance(sharpe_value, (int, float))
        and isinstance(prob_positive, (int, float))
        and isinstance(walk_forward_avg, (int, float))
    ):
        summary["headline"] = (
            f"Sharpe {sharpe_value:.2f} • MC Prob+ {prob_positive:.1%} • WF {walk_forward_avg:.2f}"
        )
    else:
        summary["headline"] = "Backtest summary unavailable"

    return summary


def persist_backtest_result(result: Dict[str, Any], summary: Dict[str, Any]) -> None:
    """Persist backtest results to disk for dashboards and auditing."""
    payload = {
        "result": result,
        "summary": summary,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        BACKTEST_SUMMARY_FILE.write_text(json.dumps(payload, indent=2))
    except Exception as exc:
        print(f"[replay_engine] Failed to write backtest summary file: {exc}", flush=True)

    try:
        BACKTEST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with BACKTEST_LOG_FILE.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{summary.get('timestamp')} | {summary.get('headline')}\n")
    except Exception as exc:
        print(f"[replay_engine] Failed to append backtest log: {exc}", flush=True)


def run_backtest(
    start_date: Optional[str] = None, end_date: Optional[str] = None
) -> Dict[str, Any]:
    """Run complete backtest pipeline with walk-forward, Monte Carlo, and transaction costs."""
    print(
        f"[replay_engine] Starting enhanced backtest (start={start_date}, end={end_date})",
        flush=True,
    )
    
    data = load_historical_data(start_date, end_date)
    if not data:
        return {"error": "No historical data available for backtest"}
    
    # Current risk policy (from brain file)
    brain_file = RUNTIME / "atlas_brain.json"
    current_policy = {"risk_scaler": 1.0, "confidence": 0.5}
    if brain_file.exists():
        try:
            brain_data = json.loads(brain_file.read_text())
            current_policy["risk_scaler"] = brain_data.get("risk_scaler", 1.0)
            current_policy["confidence"] = brain_data.get("confidence", 0.5)
        except:
            pass
    
    # Run basic simulation
    sim_result = simulate_scenario(data, current_policy)
    
    # Run simulation with transaction costs
    sim_result_with_costs = simulate_scenario_with_costs(data, current_policy)
    
    # Walk-forward optimization
    wf_result = None
    if len(data) >= WF_TRAIN_WINDOW + WF_TEST_WINDOW:
        wf_result = walk_forward_optimization(
            data, train_window=WF_TRAIN_WINDOW, test_window=WF_TEST_WINDOW, step_size=WF_STEP_SIZE
        )
    
    # Monte Carlo simulation
    mc_result = (
        monte_carlo_simulation(data, num_simulations=MC_SIMULATIONS, risk_policy=current_policy)
        if np
        else None
    )
    
    # Try TensorFlow/PyTorch if available
    tf_result = tensorflow_backtest(data) if tf else None
    pt_result = pytorch_backtest(data) if torch else None
    
    # Combine results
    backtest_result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_points": len(data),
        "simulation": sim_result,
        "simulation_with_costs": sim_result_with_costs,
        "walk_forward": wf_result,
        "monte_carlo": mc_result,
        "tensorflow": tf_result,
        "pytorch": pt_result,
        "current_policy": current_policy,
    }
    
    summary = summarize_backtest(backtest_result)
    backtest_result["summary"] = summary
    
    # Auto-adjust policy if simulation succeeded
    if "error" not in sim_result_with_costs:
        adjusted_policy = auto_adjust_guardian_policy(
            {
            "confidence": current_policy["confidence"],
            "sharpe": sim_result_with_costs.get("sharpe", 0.0),
                "win_rate": sim_result_with_costs.get("win_rate", 0.5),
            }
        )
        backtest_result["adjusted_policy"] = adjusted_policy
        
        # Optionally write adjusted policy to brain file (if enabled)
        if os.getenv("REPLAY_AUTO_APPLY", "false").lower() == "true":
            (RUNTIME / "atlas_brain_backtest.json").write_text(
                json.dumps(adjusted_policy, indent=2)
            )
            print(
                f"[replay_engine] Adjusted policy saved: risk_scaler={adjusted_policy['risk_scaler']}, confidence={adjusted_policy['confidence']}",
                flush=True,
            )
    
    # Save backtest result
    result_file = (
        BACKTEST_DIR / f"backtest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    )
    result_file.write_text(json.dumps(backtest_result, indent=2))

    # Persist summary for dashboards
    persist_backtest_result(backtest_result, summary)
    
    print(f"[replay_engine] Backtest complete: {result_file}", flush=True)
    
    return backtest_result


def main():
    """CLI entry point for backtesting."""
    import sys
    
    # Check if running in continuous mode
    if "--loop" in sys.argv:
        # Continuous mode: run backtests periodically
        interval = int(os.getenv("BACKTEST_INTERVAL", "86400"))  # Default: 24 hours
        print(
            f"[replay_engine] Starting continuous backtesting (interval: {interval}s)", flush=True
        )
        
        while True:
            try:
                result = run_backtest()
                if "error" not in result:
                    print(
                        f"[replay_engine] Backtest complete: {result.get('timestamp', 'unknown')}",
                        flush=True,
                    )
                else:
                    print(
                        f"[replay_engine] Backtest error: {result.get('error', 'unknown')}",
                        flush=True,
                    )
            except Exception as e:
                print(f"[replay_engine] Error in continuous mode: {e}", flush=True)
                traceback.print_exc()
            
            time.sleep(interval)
    else:
        # One-time mode: run single backtest
    start_date = sys.argv[1] if len(sys.argv) > 1 else None
    end_date = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = run_backtest(start_date, end_date)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

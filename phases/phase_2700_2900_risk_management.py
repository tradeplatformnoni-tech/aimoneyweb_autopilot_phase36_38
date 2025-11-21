#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2700-2900: Advanced Risk Management - World-Class Implementation
----------------------------------------------------------------------
Comprehensive risk metrics with integration to risk attribution:
- Value at Risk (VaR) - 1-day, 5-day, 95%, 99%
- Conditional VaR (CVaR) - Expected Shortfall
- Stress Testing (market crash, flash crash, volatility spike)
- Liquidity Risk Monitoring
- Drawdown Prediction Models
- Integration with risk_attribution.py and portfolio analytics
"""
import os
import json
import time
import logging
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

try:
    import numpy as np  # pyright: ignore[reportMissingImports]
    import pandas as pd  # pyright: ignore[reportMissingImports]
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

ROOT = Path(os.path.expanduser("~/neolight"))
RUNTIME = ROOT / "runtime"
STATE = ROOT / "state"
DATA = ROOT / "data"
LOGS = ROOT / "logs"

for d in [RUNTIME, STATE, DATA, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "risk_management.log"
logger = logging.getLogger("risk_management")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

RISK_METRICS_FILE = STATE / "risk_metrics.json"
BRAIN_FILE = RUNTIME / "atlas_brain.json"
PORTFOLIO_FILE = RUNTIME / "portfolio.json"
PERF_METRICS_FILE = STATE / "performance_metrics.csv"
RISK_ATTRIBUTION_FILE = STATE / "risk_attribution.json"

class AdvancedRiskManager:
    """Advanced risk management with comprehensive metrics."""
    
    def __init__(self):
        """Initialize risk manager."""
        logger.info("✅ AdvancedRiskManager initialized")
    
    def load_portfolio_positions(self) -> Dict[str, float]:
        """Load current portfolio positions from portfolio.json."""
        try:
            if PORTFOLIO_FILE.exists():
                data = json.loads(PORTFOLIO_FILE.read_text())
                positions = data.get("positions", {})
                return {k: float(v.get("qty", 0)) for k, v in positions.items()}
        except Exception as e:
            logger.debug(f"Could not load positions: {e}")
        return {}

    def load_current_equity(self) -> float:
        """Load current portfolio equity from multiple sources."""
        # Try portfolio.json first
        try:
            if PORTFOLIO_FILE.exists():
                data = json.loads(PORTFOLIO_FILE.read_text())
                equity = data.get("equity")
                if equity:
                    return float(equity)
        except Exception:
            pass
        
        # Try brain file
        try:
            if BRAIN_FILE.exists():
                data = json.loads(BRAIN_FILE.read_text())
                equity = data.get("current_equity")
                if equity:
                    return float(equity)
        except Exception:
            pass
        
        # Try performance metrics
        try:
            if PERF_METRICS_FILE.exists() and HAS_NUMPY:
                df = pd.read_csv(PERF_METRICS_FILE)
                if not df.empty and "equity" in df.columns:
                    return float(df["equity"].iloc[-1])
        except Exception:
            pass
        
        return 100000.0  # Default

    def calculate_var(self, returns: np.ndarray, confidence: float = 0.95, days: int = 1) -> float:
        """
        Calculate Value at Risk using historical simulation.
        
        Args:
            returns: Array of historical returns
            confidence: Confidence level (0.95 = 95%)
            days: Time horizon in days
        
        Returns:
            VaR as a decimal (e.g., 0.05 = 5%)
        """
        if len(returns) == 0 or not HAS_NUMPY:
            return 0.0
        
        try:
            # Historical simulation method
            sorted_returns = np.sort(returns)
            percentile = (1 - confidence) * 100
            index = int(len(sorted_returns) * (1 - confidence))
            
            if index >= len(sorted_returns):
                index = len(sorted_returns) - 1
            elif index < 0:
                index = 0
            
            var = -sorted_returns[index]  # Negative because VaR is loss
            
            # Scale for time horizon (square root of time rule)
            var *= np.sqrt(days)
            
            # Ensure non-negative
            return max(0.0, float(var))
        except Exception as e:
            logger.error(f"❌ Error calculating VaR: {e}")
            return 0.0

    def calculate_cvar(self, returns: np.ndarray, confidence: float = 0.95, days: int = 1) -> float:
        """
        Calculate Conditional VaR (Expected Shortfall).
        Average loss given that loss exceeds VaR.
        
        Args:
            returns: Array of historical returns
            confidence: Confidence level
            days: Time horizon in days
        
        Returns:
            CVaR as a decimal (positive value representing expected loss)
        """
        if len(returns) == 0 or not HAS_NUMPY:
            return 0.0
        
        try:
            var = self.calculate_var(returns, confidence, days)
            
            # CVaR is mean of losses beyond VaR
            # Returns are typically negative for losses, so we look for returns <= VaR threshold
            threshold = var  # VaR is already a positive loss value
            losses_beyond = returns[returns <= -threshold]  # Negative returns worse than -VaR
            
            if len(losses_beyond) > 0:
                # CVaR is the average of losses beyond VaR (make positive)
                cvar = abs(np.mean(losses_beyond)) * np.sqrt(days)
            else:
                # If no losses beyond VaR, use VaR itself as conservative estimate
                cvar = var
            
            # Ensure CVaR is positive and reasonable (cap at 50% for safety)
            cvar = min(max(0.0, float(cvar)), 0.50)
            return cvar
        except Exception as e:
            logger.error(f"❌ Error calculating CVaR: {e}")
            return 0.0

    def stress_test(self, price_df: pd.DataFrame, returns_df: pd.DataFrame, scenarios: List[str]) -> Dict[str, float]:
        """
        Run stress tests for different market scenarios.
        
        Args:
            price_df: DataFrame with price history
            returns_df: DataFrame with returns
            scenarios: List of scenario names
        
        Returns:
            Dictionary of {scenario: expected_loss}
        """
        if price_df is None or price_df.empty or not HAS_NUMPY:
            return {}
        
        results = {}
        
        try:
            portfolio_returns = returns_df.mean(axis=1).values if not returns_df.empty else np.array([])
            current_vol = np.std(portfolio_returns) if len(portfolio_returns) > 0 else 0.15
            current_corr = returns_df.corr().mean().mean() if not returns_df.empty else 0.5
            
            for scenario in scenarios:
                if scenario == "market_crash":
                    # Simulate -20% market crash (2008-style)
                    results[scenario] = -0.20
                elif scenario == "flash_crash":
                    # Simulate -10% flash crash (2010-style)
                    results[scenario] = -0.10
                elif scenario == "volatility_spike":
                    # Simulate 3x volatility (VIX spike)
                    spike_vol = current_vol * 3
                    # Rough estimate: loss = -2 * volatility (2-sigma event)
                    results[scenario] = -spike_vol * 2
                elif scenario == "correlation_breakdown":
                    # All assets move together (diversification fails)
                    worst_day = returns_df.min().min() if not returns_df.empty else -0.05
                    results[scenario] = float(worst_day)
                elif scenario == "liquidity_crisis":
                    # Liquidity dries up, forced selling at -15%
                    results[scenario] = -0.15
                elif scenario == "inflation_shock":
                    # Inflation spike, real returns negative
                    results[scenario] = -0.08
            
            logger.info(f"📊 Stress tests completed: {len(results)} scenarios")
        except Exception as e:
            logger.error(f"❌ Error in stress testing: {e}")
            traceback.print_exc()
        
        return results

    def calculate_drawdown(self, equity_series: List[float]) -> Dict[str, Any]:
        """
        Calculate comprehensive drawdown metrics.
        
        Args:
            equity_series: List of equity values over time
        
        Returns:
            Dictionary with drawdown metrics
        """
        if not equity_series or len(equity_series) < 2:
            return {
                "current_drawdown": 0.0,
                "max_drawdown": 0.0,
                "avg_drawdown": 0.0,
                "drawdown_duration": 0,
                "recovery_time": 0
            }
        
        try:
            if HAS_NUMPY:
                equity_array = np.array(equity_series)
                peaks = np.maximum.accumulate(equity_array)
                drawdowns = (peaks - equity_array) / peaks
                
                current_drawdown = float(drawdowns[-1]) if len(drawdowns) > 0 else 0.0
                max_drawdown = float(np.max(drawdowns))
                avg_drawdown = float(np.mean(drawdowns[drawdowns > 0])) if np.any(drawdowns > 0) else 0.0
                
                # Calculate drawdown duration (simplified)
                in_drawdown = drawdowns > 0.01  # > 1% drawdown
                drawdown_duration = int(np.sum(in_drawdown)) if len(in_drawdown) > 0 else 0
                
                return {
                    "current_drawdown": current_drawdown,
                    "max_drawdown": max_drawdown,
                    "avg_drawdown": avg_drawdown,
                    "drawdown_duration": drawdown_duration,
                    "recovery_time": 0  # Would need timestamps for accurate calculation
                }
            else:
                # Manual calculation
                peaks = []
                drawdowns = []
                peak = equity_series[0]
                
                for value in equity_series:
                    if value > peak:
                        peak = value
                    peaks.append(peak)
                    drawdown = (peak - value) / peak if peak > 0 else 0
                    drawdowns.append(drawdown)
                
                max_drawdown = max(drawdowns) if drawdowns else 0.0
                current_drawdown = drawdowns[-1] if drawdowns else 0.0
                avg_drawdown = sum([d for d in drawdowns if d > 0]) / max(1, len([d for d in drawdowns if d > 0]))
                
                return {
                    "current_drawdown": float(current_drawdown),
                    "max_drawdown": float(max_drawdown),
                    "avg_drawdown": float(avg_drawdown),
                    "drawdown_duration": 0,
                    "recovery_time": 0
                }
        except Exception as e:
            logger.error(f"❌ Error calculating drawdown: {e}")
            return {
                "current_drawdown": 0.0,
                "max_drawdown": 0.0,
                "avg_drawdown": 0.0,
                "drawdown_duration": 0,
                "recovery_time": 0
            }

    def load_price_history(self, symbols: List[str], days: int = 252) -> Optional[pd.DataFrame]:
        """Load price history for risk calculations."""
        if not HAS_NUMPY:
            return None
        
        try:
            import yfinance as yf  # pyright: ignore[reportMissingImports]
            data = {}
            for sym in symbols:
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period=f"{days}d")
                    if not hist.empty and "Close" in hist.columns:
                        data[sym] = hist["Close"]
                except Exception as e:
                    logger.debug(f"Error loading {sym}: {e}")
            
            if data:
                df = pd.DataFrame(data)
                df = df.dropna()
                return df
        except ImportError:
            logger.warning("⚠️  yfinance not available")
        except Exception as e:
            logger.error(f"❌ Error loading price history: {e}")
        
        return None

    def calculate_liquidity_risk(self, positions: Dict[str, float], price_df: Optional[pd.DataFrame]) -> Dict[str, float]:
        """
        Calculate liquidity risk metrics.
        
        Args:
            positions: Dictionary of {symbol: quantity}
            price_df: DataFrame with price history
        
        Returns:
            Liquidity risk metrics
        """
        if not positions or price_df is None or price_df.empty:
            return {
                "liquidity_score": 1.0,
                "avg_daily_volume": 0.0,
                "position_size_vs_volume": 0.0
            }
        
        try:
            # Simplified liquidity risk: assume larger positions = higher risk
            total_position_value = sum(abs(qty) * price_df[sym].iloc[-1] if sym in price_df.columns else 0 
                                      for sym, qty in positions.items())
            
            # Normalize by portfolio equity
            equity = self.load_current_equity()
            liquidity_score = min(1.0, equity / max(total_position_value, 1.0))
            
            return {
                "liquidity_score": float(liquidity_score),
                "total_position_value": float(total_position_value),
                "equity": float(equity)
            }
        except Exception as e:
            logger.error(f"❌ Error calculating liquidity risk: {e}")
            return {"liquidity_score": 1.0}
    
    def predict_drawdown(self, returns: np.ndarray, current_drawdown: float) -> Dict[str, float]:
        """
        Predict potential future drawdown using historical patterns.
        
        Args:
            returns: Historical returns
            current_drawdown: Current drawdown level
        
        Returns:
            Drawdown prediction metrics
        """
        if len(returns) == 0 or not HAS_NUMPY:
            return {
                "predicted_max_drawdown": current_drawdown,
                "drawdown_probability": 0.5,
                "confidence": 0.0
            }
        
        try:
            # Simple prediction: use historical worst drawdown as proxy
            # In production, would use more sophisticated models
            worst_return = np.min(returns)
            predicted_dd = abs(worst_return) * 2  # Conservative estimate
            
            # Probability of further drawdown based on current level
            if current_drawdown > 0.10:  # Already in significant drawdown
                prob_further = 0.6
            elif current_drawdown > 0.05:
                prob_further = 0.4
            else:
                prob_further = 0.2
            
            return {
                "predicted_max_drawdown": float(predicted_dd),
                "drawdown_probability": float(prob_further),
                "confidence": 0.7  # Medium confidence
            }
        except Exception as e:
            logger.error(f"❌ Error predicting drawdown: {e}")
            return {
                "predicted_max_drawdown": current_drawdown,
                "drawdown_probability": 0.5,
                "confidence": 0.0
            }
    
    def generate_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk report."""
        try:
            # Load current equity
            current_equity = self.load_current_equity()
            
            # Load allocations to get symbols
            allocations_file = RUNTIME / "allocations_override.json"
            symbols = []
            if allocations_file.exists():
                try:
                    data = json.loads(allocations_file.read_text())
                    symbols = list(data.get("allocations", {}).keys())
                except Exception:
                    pass
            
            if not symbols:
                symbols = ["BTC-USD", "ETH-USD", "SPY", "QQQ", "GLD"]
            
            logger.info(f"📊 Calculating risk metrics for {len(symbols)} assets")
            
            # Load price history
            price_df = self.load_price_history(symbols, days=252)
            returns_df = None
            portfolio_returns = np.array([])
            
            if price_df is not None and not price_df.empty:
                returns_df = price_df.pct_change().dropna()
                if not returns_df.empty:
                    portfolio_returns = returns_df.mean(axis=1).values
            
            # Initialize risk metrics
            risk_metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "current_equity": current_equity,
                "var": {},
                "cvar": {},
                "stress_tests": {},
                "drawdown": {},
                "liquidity_risk": {},
                "drawdown_prediction": {}
            }
            
            # Calculate VaR and CVaR
            if len(portfolio_returns) > 0:
                for days in [1, 5]:
                    for confidence in [0.95, 0.99]:
                        key = f"var_{days}d_{int(confidence*100)}"
                        risk_metrics["var"][key] = self.calculate_var(portfolio_returns, confidence, days)
                        risk_metrics["cvar"][key] = self.calculate_cvar(portfolio_returns, confidence, days)
                
                logger.info(f"✅ VaR calculated: 1d 95% = {risk_metrics['var'].get('var_1d_95', 0):.2%}")
            
            # Stress tests
            if price_df is not None and returns_df is not None:
                scenarios = ["market_crash", "flash_crash", "volatility_spike", "correlation_breakdown", "liquidity_crisis"]
                risk_metrics["stress_tests"] = self.stress_test(price_df, returns_df, scenarios)
            
            # Calculate drawdown from equity history
            equity_history = []
            try:
                if PERF_METRICS_FILE.exists() and HAS_NUMPY:
                    df = pd.read_csv(PERF_METRICS_FILE)
                    if not df.empty and "equity" in df.columns:
                        equity_history = df["equity"].tolist()
            except Exception:
                pass
            
            if not equity_history:
                equity_history = [current_equity]
            
            risk_metrics["drawdown"] = self.calculate_drawdown(equity_history)
            
            # Drawdown prediction
            if len(portfolio_returns) > 0:
                current_dd = risk_metrics["drawdown"].get("current_drawdown", 0.0)
                risk_metrics["drawdown_prediction"] = self.predict_drawdown(portfolio_returns, current_dd)
            
            # Liquidity risk
            positions = self.load_portfolio_positions()
            risk_metrics["liquidity_risk"] = self.calculate_liquidity_risk(positions, price_df)
            
            # Integrate with risk attribution if available
            try:
                if RISK_ATTRIBUTION_FILE.exists():
                    risk_attribution = json.loads(RISK_ATTRIBUTION_FILE.read_text())
                    risk_metrics["risk_attribution"] = {
                        "diversification_score": risk_attribution.get("diversification_score", 0.0),
                        "concentrated_exposures": len(risk_attribution.get("concentrated_exposures", []))
                    }
            except Exception:
                pass
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"❌ Error generating risk report: {e}")
            traceback.print_exc()
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }
    
    def update_risk_scaler(self, risk_metrics: Dict[str, Any]) -> bool:
        """Update risk scaler in brain based on risk metrics."""
        try:
            if not BRAIN_FILE.exists():
                return False
            
            brain = json.loads(BRAIN_FILE.read_text())
            max_dd = risk_metrics.get("drawdown", {}).get("max_drawdown", 0.0)
            current_dd = risk_metrics.get("drawdown", {}).get("current_drawdown", 0.0)
            var_1d_95 = risk_metrics.get("var", {}).get("var_1d_95", 0.05)
            
            # Adaptive risk scaling based on multiple factors
            risk_multiplier = 1.0
            
            # Reduce risk if drawdown is high
            if max_dd > 0.20:  # 20% max drawdown
                risk_multiplier *= 0.5
            elif max_dd > 0.15:
                risk_multiplier *= 0.7
            elif max_dd > 0.10:
                risk_multiplier *= 0.85
            
            # Reduce risk if current drawdown is significant
            if current_dd > 0.15:
                risk_multiplier *= 0.6
            elif current_dd > 0.10:
                risk_multiplier *= 0.8
            
            # Reduce risk if VaR is very high
            if var_1d_95 > 0.10:  # > 10% daily VaR
                risk_multiplier *= 0.7
            elif var_1d_95 > 0.05:
                risk_multiplier *= 0.9
            
            # Ensure reasonable bounds
            risk_multiplier = max(0.2, min(1.0, risk_multiplier))
            
            brain["risk_scaler"] = float(risk_multiplier)
            brain["risk_scaler_timestamp"] = datetime.now(timezone.utc).isoformat()
            brain["risk_metrics"] = {
                "max_drawdown": max_dd,
                "current_drawdown": current_dd,
                "var_1d_95": var_1d_95
            }
            
            BRAIN_FILE.write_text(json.dumps(brain, indent=2))
            logger.info(f"✅ Risk scaler updated: {risk_multiplier:.2f} (max_dd: {max_dd:.2%}, current_dd: {current_dd:.2%})")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating risk scaler: {e}")
            return False

def main():
    """Main risk management loop."""
    logger.info("🚀 Advanced Risk Management (Phase 2700-2900) starting...")
    
    risk_manager = AdvancedRiskManager()
    update_interval = int(os.getenv("NEOLIGHT_RISK_MANAGEMENT_INTERVAL", "3600"))  # Default 1 hour
    
    while True:
        try:
            # Generate comprehensive risk report
            risk_metrics = risk_manager.generate_risk_report()
            
            if "error" not in risk_metrics:
                # Save risk metrics
                RISK_METRICS_FILE.write_text(json.dumps(risk_metrics, indent=2))
                
                # Update risk scaler
                risk_manager.update_risk_scaler(risk_metrics)
                
                # Log summary
                logger.info("📊 Risk Metrics Summary:")
                logger.info(f"  VaR (1d, 95%): {risk_metrics.get('var', {}).get('var_1d_95', 0):.2%}")
                logger.info(f"  CVaR (1d, 95%): {risk_metrics.get('cvar', {}).get('cvar_1d_95', 0):.2%}")
                logger.info(f"  Current Drawdown: {risk_metrics.get('drawdown', {}).get('current_drawdown', 0):.2%}")
                logger.info(f"  Max Drawdown: {risk_metrics.get('drawdown', {}).get('max_drawdown', 0):.2%}")
                
                stress_tests = risk_metrics.get("stress_tests", {})
                if stress_tests:
                    logger.info(f"  Stress Tests: {len(stress_tests)} scenarios analyzed")
            else:
                logger.warning(f"⚠️  Risk report generation failed: {risk_metrics.get('error')}")
            
            logger.info(f"✅ Risk management complete. Next run in {update_interval/3600:.1f} hours")
            time.sleep(update_interval)
            
        except KeyboardInterrupt:
            logger.info("🛑 Advanced Risk Management stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in risk management loop: {e}")
            traceback.print_exc()
            time.sleep(600)  # Wait 10 minutes before retrying

# =============== WORLD-CLASS UTILITIES ==================
try:
    from utils.agent_wrapper import world_class_agent
    HAS_WORLD_CLASS_UTILS = True
except ImportError:
    HAS_WORLD_CLASS_UTILS = False

if HAS_WORLD_CLASS_UTILS:
    main = world_class_agent("risk_management", paper_mode_only=True)(main)

if __name__ == "__main__":
    main()

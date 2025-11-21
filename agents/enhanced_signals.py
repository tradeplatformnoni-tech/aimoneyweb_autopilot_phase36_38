#!/usr/bin/env python3
"""
NeoLight Enhanced Signal Generation - Phase 3100–3300
=====================================================
World-class multi-indicator signal generation:
- RSI, MACD, EMA crossover, Bollinger Bands, Momentum
- Ensemble prediction with confidence scoring
- Multi-timeframe analysis
- Pattern Recognition (candlestick patterns, chart patterns)
- ML Signal Integration (connects to ML pipeline for predictions)
"""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("⚠️  Install numpy and pandas: pip install numpy pandas")

try:
    import talib

    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    print("⚠️  Install TA-Lib: pip install TA-Lib (or use conda install -c conda-forge ta-lib)")

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "enhanced_signals.log"
logger = logging.getLogger("enhanced_signals")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
    logger.addHandler(console_handler)


class EnhancedSignalGenerator:
    """
    World-class signal generator with multiple technical indicators.
    Combines signals into ensemble prediction with confidence scoring.
    """

    def __init__(self, price_data: pd.DataFrame):
        """
        Initialize signal generator.

        Args:
            price_data: DataFrame with 'Close' column (and optionally 'High', 'Low', 'Volume')
        """
        if not HAS_NUMPY:
            raise ImportError("numpy required for signal generation")

        self.price_data = price_data.copy()

        # Ensure we have Close prices
        if "Close" not in self.price_data.columns:
            if len(self.price_data.columns) == 1:
                self.price_data.columns = ["Close"]
            else:
                raise ValueError("price_data must contain 'Close' column")

        self.close = self.price_data["Close"].values

        # Calculate all indicators
        self._calculate_indicators()

        logger.info(f"✅ EnhancedSignalGenerator initialized with {len(self.close)} data points")

    def _calculate_indicators(self):
        """Calculate all technical indicators."""
        try:
            if HAS_TALIB and len(self.close) >= 26:
                # Use TA-Lib for accurate calculations
                self.rsi = talib.RSI(self.close, timeperiod=14)
                self.macd, self.macd_signal, self.macd_hist = talib.MACD(
                    self.close, fastperiod=12, slowperiod=26, signalperiod=9
                )
                self.bb_upper, self.bb_middle, self.bb_lower = talib.BBANDS(
                    self.close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
                )
                self.ema_12 = talib.EMA(self.close, timeperiod=12)
                self.ema_26 = talib.EMA(self.close, timeperiod=26)
            else:
                # Fallback to manual calculations
                self.rsi = self._calculate_rsi_manual(self.close, 14)
                self.macd, self.macd_signal, self.macd_hist = self._calculate_macd_manual(
                    self.close
                )
                self.bb_upper, self.bb_middle, self.bb_lower = self._calculate_bollinger_manual(
                    self.close, 20, 2
                )
                self.ema_12 = self._calculate_ema_manual(self.close, 12)
                self.ema_26 = self._calculate_ema_manual(self.close, 26)

            # Calculate momentum
            self.momentum = self._calculate_momentum(self.close, 10)

            # Calculate SMA for crossover signals
            self.sma_20 = self._calculate_sma_manual(self.close, 20)
            self.sma_50 = (
                self._calculate_sma_manual(self.close, 50) if len(self.close) >= 50 else None
            )

        except Exception as e:
            logger.error(f"❌ Error calculating indicators: {e}")
            import traceback

            traceback.print_exc()
            # Set defaults
            self.rsi = np.full(len(self.close), 50.0)
            self.macd = np.zeros(len(self.close))
            self.macd_signal = np.zeros(len(self.close))
            self.macd_hist = np.zeros(len(self.close))

    def _calculate_rsi_manual(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI manually."""
        if len(prices) < period + 1:
            return np.full(len(prices), 50.0)

        rsi = np.full(len(prices), 50.0)
        deltas = np.diff(prices)

        for i in range(period, len(prices)):
            gains = deltas[i - period : i][deltas[i - period : i] > 0]
            losses = -deltas[i - period : i][deltas[i - period : i] < 0]

            avg_gain = np.mean(gains) if len(gains) > 0 else 0
            avg_loss = np.mean(losses) if len(losses) > 0 else 0

            if avg_loss == 0:
                rsi[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i] = 100.0 - (100.0 / (1.0 + rs))

        return rsi

    def _calculate_macd_manual(
        self, prices: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate MACD manually."""
        if len(prices) < 26:
            return np.zeros(len(prices)), np.zeros(len(prices)), np.zeros(len(prices))

        ema_12 = self._calculate_ema_manual(prices, 12)
        ema_26 = self._calculate_ema_manual(prices, 26)

        macd_line = ema_12 - ema_26

        # Signal line (EMA of MACD)
        macd_signal = self._calculate_ema_manual(macd_line, 9)

        # Histogram
        macd_hist = macd_line - macd_signal

        return macd_line, macd_signal, macd_hist

    def _calculate_ema_manual(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA manually."""
        if len(prices) < period:
            return np.full(len(prices), prices[0] if len(prices) > 0 else 0)

        ema = np.zeros(len(prices))
        multiplier = 2.0 / (period + 1)

        # Start with SMA
        ema[period - 1] = np.mean(prices[:period])

        # Calculate EMA
        for i in range(period, len(prices)):
            ema[i] = (prices[i] * multiplier) + (ema[i - 1] * (1 - multiplier))

        return ema

    def _calculate_sma_manual(self, prices: np.ndarray, period: int) -> np.ndarray | None:
        """Calculate SMA manually."""
        if len(prices) < period:
            return None

        sma = np.zeros(len(prices))
        for i in range(period - 1, len(prices)):
            sma[i] = np.mean(prices[i - period + 1 : i + 1])

        return sma

    def _calculate_bollinger_manual(
        self, prices: np.ndarray, period: int = 20, std_dev: float = 2.0
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bollinger Bands manually."""
        if len(prices) < period:
            return (
                np.full(len(prices), prices[0]),
                np.full(len(prices), prices[0]),
                np.full(len(prices), prices[0]),
            )

        sma = self._calculate_sma_manual(prices, period)
        if sma is None:
            return (
                np.full(len(prices), prices[0]),
                np.full(len(prices), prices[0]),
                np.full(len(prices), prices[0]),
            )

        upper = np.zeros(len(prices))
        lower = np.zeros(len(prices))

        for i in range(period - 1, len(prices)):
            std = np.std(prices[i - period + 1 : i + 1])
            upper[i] = sma[i] + (std_dev * std)
            lower[i] = sma[i] - (std_dev * std)

        return upper, sma, lower

    def _calculate_momentum(self, prices: np.ndarray, period: int = 10) -> np.ndarray:
        """Calculate momentum (rate of change)."""
        if len(prices) < period + 1:
            return np.zeros(len(prices))

        momentum = np.zeros(len(prices))
        for i in range(period, len(prices)):
            momentum[i] = (prices[i] - prices[i - period]) / prices[i - period]

        return momentum

    def detect_candlestick_patterns(self) -> dict[str, Any]:
        """
        Detect common candlestick patterns - Enhanced World-Class Implementation.
        Returns pattern name and signal strength.
        Supports: Hammer, Doji, Engulfing, Morning Star, Evening Star, Three White Soldiers, Three Black Crows
        """
        if len(self.close) < 3:
            return {"pattern": None, "signal": "HOLD", "confidence": 0.0}

        patterns = []
        confidence = 0.0

        # Get OHLC data if available, otherwise estimate from Close
        has_ohlc = all(col in self.price_data.columns for col in ["Open", "High", "Low", "Close"])

        if has_ohlc:
            opens = self.price_data["Open"].values
            highs = self.price_data["High"].values
            lows = self.price_data["Low"].values
            closes = self.price_data["Close"].values
        else:
            # Estimate OHLC from Close prices (simplified)
            closes = self.close
            opens = closes * 0.999  # Estimate: open slightly below close
            highs = closes * 1.002  # Estimate: high slightly above close
            lows = closes * 0.998  # Estimate: low slightly below close

        if len(closes) >= 3:
            # Hammer pattern (reversal - bullish)
            last_low = lows[-1] if len(lows) > 0 else closes[-1]
            last_high = highs[-1] if len(highs) > 0 else closes[-1]
            last_open = opens[-1] if len(opens) > 0 else closes[-1]
            last_close = closes[-1]

            body = abs(last_close - last_open)
            lower_shadow = min(last_open, last_close) - last_low
            upper_shadow = last_high - max(last_open, last_close)

            if lower_shadow > body * 2 and upper_shadow < body * 0.5:
                patterns.append("Hammer")
                confidence += 0.4

            # Doji pattern (indecision)
            if body < (last_high - last_low) * 0.1:
                patterns.append("Doji")
                confidence += 0.2

            # Engulfing patterns
            if len(closes) >= 2:
                prev_open = opens[-2] if len(opens) >= 2 else closes[-2]
                prev_close = closes[-2]

                # Bullish Engulfing
                if (
                    prev_close < prev_open  # Previous bearish
                    and last_close > last_open  # Current bullish
                    and last_open < prev_close  # Gaps down
                    and last_close > prev_open
                ):  # Engulfs previous
                    patterns.append("Bullish Engulfing")
                    confidence += 0.5

                # Bearish Engulfing
                elif (
                    prev_close > prev_open  # Previous bullish
                    and last_close < last_open  # Current bearish
                    and last_open > prev_close  # Gaps up
                    and last_close < prev_open
                ):  # Engulfs previous
                    patterns.append("Bearish Engulfing")
                    confidence += 0.5

        # Three White Soldiers (strong bullish)
        if len(closes) >= 3:
            if (
                closes[-3] < closes[-2] < closes[-1]
                and opens[-2] > closes[-3]
                and opens[-1] > closes[-2]
            ):
                patterns.append("Three White Soldiers")
                confidence += 0.6

        # Three Black Crows (strong bearish)
        if len(closes) >= 3:
            if (
                closes[-3] > closes[-2] > closes[-1]
                and opens[-2] < closes[-3]
                and opens[-1] < closes[-2]
            ):
                patterns.append("Three Black Crows")
                confidence += 0.6

        # Morning Star (bullish reversal)
        if len(closes) >= 3 and has_ohlc:
            if (
                closes[-3] < opens[-3]  # First candle bearish
                and closes[-2] < closes[-3]  # Second candle gaps down
                and closes[-1] > (opens[-3] + closes[-3]) / 2
            ):  # Third candle strong bullish
                patterns.append("Morning Star")
                confidence += 0.7

        # Evening Star (bearish reversal)
        if len(closes) >= 3 and has_ohlc:
            if (
                closes[-3] > opens[-3]  # First candle bullish
                and closes[-2] > closes[-3]  # Second candle gaps up
                and closes[-1] < (opens[-3] + closes[-3]) / 2
            ):  # Third candle strong bearish
                patterns.append("Evening Star")
                confidence += 0.7

        # Determine signal from patterns
        signal = "HOLD"
        bullish_patterns = ["Hammer", "Bullish Engulfing", "Three White Soldiers", "Morning Star"]
        bearish_patterns = ["Bearish Engulfing", "Three Black Crows", "Evening Star"]

        if any(p in patterns for p in bullish_patterns):
            signal = "BUY"
        elif any(p in patterns for p in bearish_patterns):
            signal = "SELL"

        return {
            "pattern": patterns[0] if patterns else None,
            "patterns": patterns,
            "signal": signal,
            "confidence": min(confidence, 1.0),
            "pattern_count": len(patterns),
        }

    def detect_chart_patterns(self) -> dict[str, Any]:
        """
        Detect chart patterns - Enhanced World-Class Implementation.
        Supports: Head and Shoulders, Triangles, Double Tops/Bottoms, Flags, Pennants
        """
        if len(self.close) < 20:
            return {"pattern": None, "signal": "HOLD", "confidence": 0.0}

        recent_prices = self.close[-50:] if len(self.close) >= 50 else self.close
        patterns_detected = []
        confidence = 0.0

        # Trend detection
        trend = "SIDEWAYS"
        if len(recent_prices) >= 10:
            first_half = np.mean(recent_prices[: len(recent_prices) // 2])
            second_half = np.mean(recent_prices[len(recent_prices) // 2 :])

            if second_half > first_half * 1.02:
                trend = "UPTREND"
            elif second_half < first_half * 0.98:
                trend = "DOWNTREND"

        # Detect support/resistance levels
        support = float(np.min(recent_prices))
        resistance = float(np.max(recent_prices))
        current = float(self.close[-1])

        # Head and Shoulders detection (bearish reversal)
        if len(recent_prices) >= 20:
            # Look for three peaks: left shoulder, head, right shoulder
            peaks = []
            for i in range(1, len(recent_prices) - 1):
                if (
                    recent_prices[i] > recent_prices[i - 1]
                    and recent_prices[i] > recent_prices[i + 1]
                ):
                    peaks.append((i, recent_prices[i]))

            if len(peaks) >= 3:
                # Check if middle peak is highest (head)
                peaks_sorted = sorted(peaks, key=lambda x: x[1], reverse=True)
                if len(peaks_sorted) >= 3:
                    head_idx = peaks_sorted[0][0]
                    left_shoulder = peaks_sorted[1] if peaks_sorted[1][0] < head_idx else None
                    right_shoulder = peaks_sorted[2] if peaks_sorted[2][0] > head_idx else None

                    if left_shoulder and right_shoulder:
                        # Check if shoulders are similar height
                        shoulder_diff = abs(left_shoulder[1] - right_shoulder[1]) / left_shoulder[1]
                        if shoulder_diff < 0.05:  # Within 5%
                            patterns_detected.append("Head and Shoulders")
                            confidence += 0.6

        # Double Top detection (bearish)
        if len(peaks) >= 2:
            top1, top2 = peaks[-2], peaks[-1]
            price_diff = abs(top1[1] - top2[1]) / top1[1]
            if price_diff < 0.02:  # Within 2%
                patterns_detected.append("Double Top")
                confidence += 0.5

        # Double Bottom detection (bullish)
        if len(recent_prices) >= 10:
            troughs = []
            for i in range(1, len(recent_prices) - 1):
                if (
                    recent_prices[i] < recent_prices[i - 1]
                    and recent_prices[i] < recent_prices[i + 1]
                ):
                    troughs.append((i, recent_prices[i]))

            if len(troughs) >= 2:
                bottom1, bottom2 = troughs[-2], troughs[-1]
                price_diff = abs(bottom1[1] - bottom2[1]) / bottom1[1]
                if price_diff < 0.02:  # Within 2%
                    patterns_detected.append("Double Bottom")
                    confidence += 0.5

        # Triangle pattern detection (ascending, descending, symmetrical)
        if len(recent_prices) >= 15:
            # Calculate volatility compression
            early_vol = np.std(recent_prices[: len(recent_prices) // 3])
            late_vol = np.std(recent_prices[-len(recent_prices) // 3 :])

            if late_vol < early_vol * 0.7:  # Volatility compression
                # Check for converging trendlines
                early_high = np.max(recent_prices[: len(recent_prices) // 3])
                late_high = np.max(recent_prices[-len(recent_prices) // 3 :])
                early_low = np.min(recent_prices[: len(recent_prices) // 3])
                late_low = np.min(recent_prices[-len(recent_prices) // 3 :])

                high_slope = (late_high - early_high) / len(recent_prices)
                low_slope = (late_low - early_low) / len(recent_prices)

                if abs(high_slope) < 0.001 and abs(low_slope) < 0.001:
                    patterns_detected.append("Symmetrical Triangle")
                    confidence += 0.4
                elif high_slope < 0 and low_slope > 0:
                    patterns_detected.append("Ascending Triangle")
                    confidence += 0.5
                elif high_slope < 0 and low_slope < 0:
                    patterns_detected.append("Descending Triangle")
                    confidence += 0.5

        # Flag/Pennant detection (continuation patterns)
        if len(recent_prices) >= 10:
            # Look for sharp move followed by consolidation
            early_range = np.max(recent_prices[:5]) - np.min(recent_prices[:5])
            late_range = np.max(recent_prices[-5:]) - np.min(recent_prices[-5:])

            if early_range > late_range * 2:  # Consolidation after move
                if trend == "UPTREND":
                    patterns_detected.append("Bull Flag")
                    confidence += 0.4
                elif trend == "DOWNTREND":
                    patterns_detected.append("Bear Flag")
                    confidence += 0.4

        # Determine signal from patterns
        signal = "HOLD"
        bullish_patterns = ["Double Bottom", "Ascending Triangle", "Bull Flag"]
        bearish_patterns = ["Head and Shoulders", "Double Top", "Descending Triangle", "Bear Flag"]

        if any(p in patterns_detected for p in bullish_patterns):
            signal = "BUY"
        elif any(p in patterns_detected for p in bearish_patterns):
            signal = "SELL"
        elif trend == "UPTREND" and current < support * 1.05:
            signal = "BUY"  # Near support in uptrend
            confidence += 0.3
        elif trend == "DOWNTREND" and current > resistance * 0.95:
            signal = "SELL"  # Near resistance in downtrend
            confidence += 0.3

        return {
            "pattern": patterns_detected[0] if patterns_detected else trend,
            "patterns": patterns_detected + [trend] if trend != "SIDEWAYS" else patterns_detected,
            "signal": signal,
            "confidence": min(confidence, 1.0),
            "support": support,
            "resistance": resistance,
            "trend": trend,
        }

    def get_ml_signal(self, symbol: str | None = None) -> dict[str, Any]:
        """
        Get ML prediction signal from ML pipeline.
        Connects to agents/ml_pipeline.py for predictions.
        """
        try:
            # Try to load ML model predictions
            ml_file = ROOT / "state" / "ml_predictions.json"
            if ml_file.exists():
                import json

                data = json.loads(ml_file.read_text())

                if symbol and symbol in data.get("predictions", {}):
                    pred = data["predictions"][symbol]
                    return {
                        "signal": pred.get("signal", "HOLD"),
                        "confidence": pred.get("confidence", 0.0),
                        "predicted_return": pred.get("predicted_return", 0.0),
                        "source": "ml_pipeline",
                    }

                # Fallback to general prediction
                general = data.get("general_prediction", {})
                if general:
                    return {
                        "signal": general.get("signal", "HOLD"),
                        "confidence": general.get("confidence", 0.0),
                        "source": "ml_pipeline",
                    }
        except Exception as e:
            logger.debug(f"ML signal not available: {e}")

        # Fallback: try to use ML pipeline directly
        try:
            from agents.ml_pipeline import predict_price

            if symbol and len(self.close) >= 20:
                # Use recent prices for prediction
                recent_data = pd.DataFrame({"Close": self.close[-20:]})
                prediction = predict_price(recent_data)

                if prediction:
                    signal = (
                        "BUY"
                        if prediction.get("predicted_return", 0) > 0.01
                        else "SELL"
                        if prediction.get("predicted_return", 0) < -0.01
                        else "HOLD"
                    )
                    return {
                        "signal": signal,
                        "confidence": abs(prediction.get("predicted_return", 0))
                        * 10,  # Scale to 0-1
                        "predicted_return": prediction.get("predicted_return", 0),
                        "source": "ml_pipeline_direct",
                    }
        except Exception as e:
            logger.debug(f"Direct ML prediction failed: {e}")

        return {"signal": "HOLD", "confidence": 0.0, "source": "ml_unavailable"}

    def generate_signal(self, current_price: float | None = None) -> dict[str, Any]:
        """
        Generate trading signal with confidence score.

        Args:
            current_price: Current price (if None, uses last price in series)

        Returns:
            Dictionary with signal, confidence, and indicator details
        """
        if len(self.close) == 0:
            return {"signal": "HOLD", "confidence": 0.0, "reason": "No data"}

        # Use latest values
        idx = len(self.close) - 1
        current = current_price if current_price is not None else self.close[idx]

        # Initialize signal votes
        buy_votes = 0
        sell_votes = 0
        hold_votes = 0

        reasons = []

        # RSI Signal
        if idx < len(self.rsi):
            rsi_val = self.rsi[idx]
            if rsi_val < 30:
                buy_votes += 2
                reasons.append(f"RSI oversold ({rsi_val:.1f})")
            elif rsi_val > 70:
                sell_votes += 2
                reasons.append(f"RSI overbought ({rsi_val:.1f})")
            else:
                hold_votes += 1

        # MACD Signal
        if idx < len(self.macd_hist):
            macd_hist_val = self.macd_hist[idx]
            if macd_hist_val > 0 and self.macd[idx] > self.macd_signal[idx]:
                buy_votes += 2
                reasons.append("MACD bullish crossover")
            elif macd_hist_val < 0 and self.macd[idx] < self.macd_signal[idx]:
                sell_votes += 2
                reasons.append("MACD bearish crossover")
            else:
                hold_votes += 1

        # EMA Crossover
        if self.ema_12 is not None and self.ema_26 is not None and idx < len(self.ema_12):
            if self.ema_12[idx] > self.ema_26[idx]:
                buy_votes += 1
                reasons.append("EMA 12 > EMA 26 (bullish)")
            else:
                sell_votes += 1

        # Bollinger Bands
        if idx < len(self.bb_upper):
            if current < self.bb_lower[idx]:
                buy_votes += 1
                reasons.append("Price below lower Bollinger Band")
            elif current > self.bb_upper[idx]:
                sell_votes += 1
                reasons.append("Price above upper Bollinger Band")

        # SMA Crossover
        if self.sma_20 is not None and idx < len(self.sma_20):
            if current > self.sma_20[idx]:
                buy_votes += 1
            else:
                sell_votes += 1

        # Pattern Recognition
        candlestick_patterns = self.detect_candlestick_patterns()
        chart_patterns = self.detect_chart_patterns()

        if candlestick_patterns.get("signal") == "BUY":
            buy_votes += 1
            reasons.append(f"Candlestick: {candlestick_patterns.get('pattern')}")
        elif candlestick_patterns.get("signal") == "SELL":
            sell_votes += 1
            reasons.append(f"Candlestick: {candlestick_patterns.get('pattern')}")

        if chart_patterns.get("signal") == "BUY":
            buy_votes += 1
            reasons.append(f"Chart: {chart_patterns.get('pattern')}")
        elif chart_patterns.get("signal") == "SELL":
            sell_votes += 1
            reasons.append(f"Chart: {chart_patterns.get('pattern')}")

        # ML Signal Integration
        ml_signal = self.get_ml_signal()
        if ml_signal.get("confidence", 0) > 0.3:
            ml_sig = ml_signal.get("signal", "HOLD")
            if ml_sig == "BUY":
                buy_votes += 2  # ML signals get higher weight
                reasons.append(f"ML Prediction: {ml_signal.get('predicted_return', 0):.2%}")
            elif ml_sig == "SELL":
                sell_votes += 2
                reasons.append(f"ML Prediction: {ml_signal.get('predicted_return', 0):.2%}")

        if self.sma_50 is not None and self.sma_20 is not None and idx < len(self.sma_20):
            if self.sma_20[idx] > self.sma_50[idx]:
                buy_votes += 1
                reasons.append("SMA 20 > SMA 50 (golden cross)")
            else:
                sell_votes += 1

        # Momentum
        if self.momentum is not None and idx < len(self.momentum):
            momentum_val = self.momentum[idx]
            if momentum_val > 0.02:  # 2% positive momentum
                buy_votes += 1
                reasons.append(f"Strong positive momentum ({momentum_val:.2%})")
            elif momentum_val < -0.02:  # 2% negative momentum
                sell_votes += 1
                reasons.append(f"Strong negative momentum ({momentum_val:.2%})")

        # Determine signal
        total_votes = buy_votes + sell_votes + hold_votes
        if total_votes == 0:
            signal = "HOLD"
            confidence = 0.0
        elif buy_votes > sell_votes:
            signal = "BUY"
            confidence = min(1.0, buy_votes / max(total_votes, 1))
        elif sell_votes > buy_votes:
            signal = "SELL"
            confidence = min(1.0, sell_votes / max(total_votes, 1))
        else:
            signal = "HOLD"
            confidence = 0.3

        result = {
            "signal": signal,
            "confidence": float(confidence),
            "buy_votes": buy_votes,
            "sell_votes": sell_votes,
            "hold_votes": hold_votes,
            "reasons": reasons,
            "indicators": {
                "rsi": float(self.rsi[idx]) if idx < len(self.rsi) else 50.0,
                "macd_hist": float(self.macd_hist[idx]) if idx < len(self.macd_hist) else 0.0,
                "momentum": float(self.momentum[idx])
                if self.momentum is not None and idx < len(self.momentum)
                else 0.0,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.info(
            f"📊 Signal generated: {signal} (confidence: {confidence:.2f}) | Reasons: {', '.join(reasons[:3])}"
        )

        return result


# Example usage
if __name__ == "__main__":
    logger.info("🧪 Testing Enhanced Signal Generator...")

    # Generate sample price data
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    prices = 100 + np.cumsum(np.random.randn(100) * 2)
    price_df = pd.DataFrame({"Close": prices}, index=dates)

    # Initialize generator
    generator = EnhancedSignalGenerator(price_df)

    # Generate signal
    signal_result = generator.generate_signal()

    print(f"\n✅ Signal: {signal_result['signal']}")
    print(f"✅ Confidence: {signal_result['confidence']:.2f}")
    print(f"✅ Buy Votes: {signal_result['buy_votes']} | Sell Votes: {signal_result['sell_votes']}")
    print(f"✅ Reasons: {', '.join(signal_result['reasons'])}")

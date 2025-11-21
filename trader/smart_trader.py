#!/usr/bin/env python3
"""
NeoLight SmartTrader — Paper Trading Implementation
---------------------------------------------------
Autonomous paper trading with signal generation, risk management,
and Telegram notifications.
"""

import datetime as dt
import json
import logging
import math
import os
import signal
import sys
import time
import traceback
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Optional

# Add backend to path for ledger integration
ROOT = Path(os.path.expanduser("~/neolight"))
sys.path.insert(0, str(ROOT))

# =============== WORLD-CLASS UTILITIES ==================
# Import world-class stability utilities
try:
    from utils.circuit_breaker import CircuitBreaker
    from utils.health_check import HealthCheck
    from utils.state_manager import StateManager, load_state_safe, save_state_safe
    from utils.structured_logging import log_with_context, setup_structured_logging

    HAS_WORLD_CLASS_UTILS = True
except ImportError as e:
    HAS_WORLD_CLASS_UTILS = False
    print(f"⚠️ World-class utilities not available: {e}", flush=True)

# =============== LOGGING SETUP ==================
# Configure logging with file and console handlers
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "smart_trader.log"

# Create logger
logger = logging.getLogger("smart_trader")
logger.setLevel(logging.DEBUG)

# Prevent duplicate handlers
if not logger.handlers:
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler (INFO level for less noise)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

# Try requests for Alpaca API (optional)
try:
    import requests  # type: ignore

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Phase 2900-3100: Live Execution Engine
try:
    from trader.live_execution import LiveExecutionEngine

    HAS_LIVE_EXECUTION = True
except ImportError:
    HAS_LIVE_EXECUTION = False
    logger.warning("⚠️ live_execution not available - LIVE_MODE disabled")

# Phase 3300-3500: Kelly Sizing
try:
    from analytics.kelly_sizing import apply_fractional_kelly, calculate_position_size

    HAS_KELLY_SIZING = True
except ImportError:
    HAS_KELLY_SIZING = False
    logger.warning("⚠️ kelly_sizing not available - using default position sizing")

# Phase 3500-3700: Multi-Strategy Framework
try:
    from agents.strategy_manager import StrategyManager
    from trader.strategy_executor import StrategyExecutor

    HAS_STRATEGY_MANAGER = True
except ImportError:
    HAS_STRATEGY_MANAGER = False
    logger.warning("⚠️ strategy_manager not available - using default strategy loading")

# Import world-class QuoteService
try:
    # Try relative import first (same directory)
    from quote_service import ValidatedQuote, atomic_trade_context, get_quote_service

    HAS_QUOTE_SERVICE = True
except ImportError:
    try:
        # Try absolute import
        from trader.quote_service import ValidatedQuote, atomic_trade_context, get_quote_service

        HAS_QUOTE_SERVICE = True
    except ImportError:
        HAS_QUOTE_SERVICE = False
        logger.warning("⚠️ quote_service not available - using legacy quote fetching")

try:
    from backend.ledger_engine import rebuild_equity_curve, record_fill
except ImportError:
    print("⚠️  ledger_engine not available - P&L tracking disabled")

    def record_fill(*args, **kwargs):
        pass

    def rebuild_equity_curve():
        return 100000.0, 100000.0, 0.0, 0.0


# Try yfinance for market data
try:
    import yfinance as yf  # type: ignore

    HAS_YFINANCE = True
except ImportError:
    print("⚠️  Install yfinance: pip install yfinance")
    HAS_YFINANCE = False

try:
    import numpy as np  # type: ignore

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("⚠️  Install numpy: pip install numpy")

# Track recent bid/ask spreads (percent) for liquidity risk
RECENT_SPREADS: deque[float] = deque(maxlen=128)
QUOTE_BACKOFF: dict[str, float] = {}
QUOTE_FAILURE_COUNTS: dict[str, int] = defaultdict(int)

# =============== SAFETY HANDLERS ==================
stop_flag = {"stop": False}
restart_count = 0
MAX_RESTARTS = 100  # Prevent infinite loops


def handle_stop(sig, frame):
    """Handle stop signals more gracefully - only stop on explicit user interrupt."""
    # Only stop if SIGINT (Ctrl+C) from user
    # Ignore SIGTERM (which Guardian might send during restart)
    if sig == signal.SIGINT:
        stop_flag["stop"] = True
        print("🛑 Stop signal received — preparing graceful shutdown...", flush=True)
    # For SIGTERM, log but don't stop (Guardian will restart if needed)
    elif sig == signal.SIGTERM:
        print("⚠️  SIGTERM received (may be Guardian restart) - continuing...", flush=True)
        # Don't set stop_flag - let Guardian manage lifecycle


# Only catch SIGINT for user control
signal.signal(signal.SIGINT, handle_stop)
# Don't catch SIGTERM - let Guardian handle it


# =============== TELEGRAM ==================
def send_telegram(
    text: str, include_mode: bool = False, mode: Optional[str] = None, state: Optional[dict] = None
):
    """
    Send Telegram notification with optional mode display.

    Args:
        text: Message text
        include_mode: If True, prepend mode indicator
        mode: Trading mode (if None, extracted from state)
        state: State dictionary for mode extraction
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return

    # Format message with mode if requested
    if include_mode:
        if mode is None and state:
            mode = state.get("trading_mode", "TEST_MODE")

        if mode:
            # Mode emoji mapping
            mode_emoji = {"TEST_MODE": "🟣", "PAPER_TRADING_MODE": "🟢", "LIVE_MODE": "🔴"}
            emoji = mode_emoji.get(mode, "⚪")
            mode_display = f"{emoji} Mode: {mode}"
            text = f"{mode_display}\n{text}"

    try:
        import urllib.parse
        import urllib.request

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        urllib.request.urlopen(url, data=data, timeout=6)
        logger.debug(f"✅ Telegram message sent: {text[:50]}...")
    except Exception as e:
        logger.warning(f"⚠️ Telegram send failed: {e}")  # Log errors instead of silent fail


# =============== UTILS ==================
def calculate_spread(bid: float, ask: float) -> float:
    """Compute bid-ask spread in basis points."""
    mid = (bid + ask) / 2.0
    return (ask - bid) / max(1e-9, mid) * 10000.0


def sma(series: list[float], n: int) -> Optional[float]:
    if len(series) < n:
        return None
    return sum(series[-n:]) / float(n)


def rsi(prices: list[float], n: int = 14) -> Optional[float]:
    if len(prices) < n + 1:
        return None
    gains = losses = 0.0
    for i in range(-n, 0):
        d = prices[i] - prices[i - 1]
        if d > 0:
            gains += d
        else:
            losses -= d
    if losses <= 0:
        return 100.0
    rs = gains / max(1e-9, losses)
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Optional[dict[str, float]]:
    """Calculate MACD indicator."""
    if len(prices) < slow + signal:
        return None
    # Simplified: use SMA for EMA approximation
    fast_ema = sma(prices, fast)
    slow_ema = sma(prices, slow)
    if not (fast_ema and slow_ema):
        return None
    macd_line = fast_ema - slow_ema
    # Signal line approximation
    macd_hist = [macd_line]  # Simplified
    signal_line = macd_line * 0.9  # Approximation
    return {"macd": macd_line, "signal": signal_line, "histogram": macd_line - signal_line}


def bollinger_bands(
    prices: list[float], n: int = 20, std_dev: float = 2.0
) -> Optional[dict[str, float]]:
    """Calculate Bollinger Bands."""
    if len(prices) < n:
        return None
    sma_val = sma(prices, n)
    if not sma_val:
        return None
    # Calculate standard deviation
    variance = sum((p - sma_val) ** 2 for p in prices[-n:]) / n
    std = variance**0.5
    upper = sma_val + (std_dev * std)
    lower = sma_val - (std_dev * std)
    return {"upper": upper, "middle": sma_val, "lower": lower}


def atr(prices: list[float], n: int = 14) -> Optional[float]:
    """Average True Range for volatility."""
    if len(prices) < n + 1:
        return None
    true_ranges = []
    for i in range(-n, 0):
        high_low = abs(prices[i] - prices[i - 1])
        true_ranges.append(high_low)
    return sum(true_ranges) / len(true_ranges) if true_ranges else None


def calculate_momentum(prices: list[float], window: int = 5) -> Optional[float]:
    """Calculate momentum as % change over last N price points."""
    if len(prices) < window + 1:
        return None
    momentum = (prices[-1] - prices[-(window + 1)]) / prices[-(window + 1)]
    return round(momentum * 100, 3)  # return % change


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def schedule_quote_backoff(symbol: str, base_delay: int = 30, max_delay: int = 900) -> None:
    """Exponential-style backoff for symbols that keep failing quote fetches."""
    QUOTE_FAILURE_COUNTS[symbol] += 1
    delay = min(max_delay, base_delay * QUOTE_FAILURE_COUNTS[symbol])
    QUOTE_BACKOFF[symbol] = time.time() + delay


def reset_quote_backoff(symbol: str) -> None:
    """Reset backoff when quote fetch succeeds."""
    QUOTE_FAILURE_COUNTS[symbol] = 0
    if symbol in QUOTE_BACKOFF:
        QUOTE_BACKOFF.pop(symbol, None)


# =============== WORLD-CLASS SAFE PRICE CONVERSION ==================
def safe_float_convert(
    value: Any,
    symbol: str = "UNKNOWN",
    context: str = "price",
    logger_instance: Optional[logging.Logger] = None,
    state: Optional[dict] = None,
) -> Optional[float]:
    """
    World-class safe float conversion with comprehensive validation.
    Returns None if conversion fails, never raises ValueError.
    """
    log = logger_instance or logger

    # --- Step 1: Check for None, empty string, or invalid values ---
    if value is None:
        log.debug(f"⚠️ {symbol}: {context} is None")
        return None

    if value == "" or str(value).strip() == "":
        log.warning(f"⚠️ {symbol}: {context} is empty string")
        if state:
            send_telegram(
                f"🟣 Mode: {state.get('trading_mode', 'TEST_MODE')}\n"
                f"⚠️ Invalid {context} detected: {symbol}\n"
                f"Reason: Empty value received from data source.",
                include_mode=True,
                state=state,
            )
        return None

    # --- Step 2: Check for string representations of NaN/None ---
    value_str = str(value).strip().lower()
    if value_str in ("nan", "none", "null", "inf", "-inf", "infinity", "-infinity"):
        log.warning(f"⚠️ {symbol}: {context} is invalid string: {value_str!r}")
        return None

    # --- Step 3: Attempt safe conversion ---
    try:
        converted = float(value)

        # --- Step 4: Validate reasonable range ---
        if converted <= 0:
            log.warning(f"⚠️ {symbol}: {context} is non-positive: {converted}")
            return None

        if converted > 1e10:  # Unrealistic price (e.g., > $10 billion)
            log.warning(f"⚠️ {symbol}: {context} is unrealistic: {converted}")
            return None

        return converted

    except (ValueError, TypeError, OverflowError) as e:
        log.error(
            f"❌ {symbol}: Failed to convert {context} to float: {value!r} ({type(value).__name__}) - {e}"
        )
        if state:
            send_telegram(
                f"🟣 Mode: {state.get('trading_mode', 'TEST_MODE')}\n"
                f"⚠️ {context} conversion failed: {symbol}\n"
                f"Reason: {type(value).__name__} value '{value!r}' cannot be converted.",
                include_mode=True,
                state=state,
            )
        return None


# =============== BROKER (PAPER TRADING) ==================
class PaperBroker:
    def __init__(self, starting_cash: float = 100000.0):
        self._cash = starting_cash
        self._positions: dict[
            str, dict[str, float]
        ] = {}  # {symbol: {"qty": float, "avg_price": float}}
        self._equity = starting_cash
        self.fee_rate = 0.0002  # 2 bps per trade

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def equity(self) -> float:
        return self._equity

    def fetch_quote(self, sym: str) -> Optional[dict[str, float]]:
        """
        Fetch current quote with world-class multi-source fallback.
        Priority: Alpaca (if configured) -> Yahoo Finance -> Historical data.
        """
        # --- Method 1: Try Alpaca API (if configured) - Highest quality data ---
        alpaca_key = os.getenv("ALPACA_API_KEY")
        alpaca_secret = os.getenv("ALPACA_API_SECRET")
        use_alpaca = os.getenv("NEOLIGHT_USE_ALPACA_QUOTES", "false").lower() == "true"

        if use_alpaca and alpaca_key and alpaca_secret:
            if HAS_REQUESTS:
                try:
                    # Convert symbol format (BTC-USD -> BTCUSD for Alpaca)
                    alpaca_symbol = sym.replace("-", "") if "-" in sym else sym

                    # Try Alpaca quotes endpoint
                    headers = {"APCA-API-KEY-ID": alpaca_key, "APCA-API-SECRET-KEY": alpaca_secret}

                    # Try crypto first (BTCUSD, ETHUSD)
                    if "USD" in alpaca_symbol and len(alpaca_symbol) <= 8:
                        url = "https://data.alpaca.markets/v1beta3/crypto/latest/quotes"
                        params = {"symbols": alpaca_symbol}
                    else:
                        # Stocks
                        url = f"https://data.alpaca.markets/v2/stocks/{alpaca_symbol}/quotes/latest"
                        params = None

                    response = requests.get(url, headers=headers, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()

                        # Parse Alpaca response
                        if "quotes" in data:
                            # Crypto format
                            quotes = data.get("quotes", {})
                            if alpaca_symbol in quotes:
                                quote_data = quotes[alpaca_symbol]
                                price = (
                                    quote_data.get("ap")
                                    or quote_data.get("bp")
                                    or quote_data.get("lp")
                                )
                            else:
                                price = None
                        elif "quote" in data:
                            # Stock format
                            quote_data = data["quote"]
                            price = (
                                quote_data.get("ap") or quote_data.get("bp") or quote_data.get("lp")
                            )
                        else:
                            price = None

                        if price is not None:
                            # --- World-Class Safe Conversion ---
                            safe_price = safe_float_convert(
                                price, symbol=sym, context="Alpaca quote price"
                            )
                            if safe_price is not None and 1.0 <= safe_price <= 1e10:
                                logger.debug(f"📊 {sym} Quote (Alpaca): {safe_price:.2f}")
                                spread_pct = 0.0005
                                return {
                                    "bid": safe_price * (1 - spread_pct / 2),
                                    "ask": safe_price * (1 + spread_pct / 2),
                                    "mid": safe_price,
                                    "last": safe_price,
                                    "regularMarketPrice": safe_price,
                                    "currentPrice": safe_price,
                                    "source": "alpaca",
                                }
                except Exception as e:
                    logger.debug(f"⚠️ {sym}: Alpaca quote fetch failed: {e}")

        # --- Method 2: Yahoo Finance (fast_info) - Fast fallback ---
        if not HAS_YFINANCE:
            logger.warning(f"⚠️ yfinance not available, cannot fetch quote for {sym}")
            return None

        try:
            ticker = yf.Ticker(sym)

            # Method 1: Try fast_info first (faster, more reliable)
            try:
                fast_info = ticker.fast_info
                price = None

                # Try different fast_info attributes in order of preference
                for attr_name in ["lastPrice", "regularMarketPrice", "currentPrice"]:
                    if hasattr(fast_info, attr_name):
                        attr_value = getattr(fast_info, attr_name)
                        if attr_value is not None:
                            # --- World-Class Safe Conversion ---
                            safe_price = safe_float_convert(
                                attr_value, symbol=sym, context=f"fast_info.{attr_name}"
                            )
                            if safe_price is not None and 1.0 <= safe_price <= 1e10:
                                logger.debug(
                                    f"📊 {sym} Quote (fast_info.{attr_name}): {safe_price:.2f}"
                                )
                                spread_pct = 0.0005
                                return {
                                    "bid": safe_price * (1 - spread_pct / 2),
                                    "ask": safe_price * (1 + spread_pct / 2),
                                    "mid": safe_price,
                                    "last": safe_price,
                                    "regularMarketPrice": safe_price,
                                    "currentPrice": safe_price,
                                    "source": "yfinance_fast_info",
                                }
            except Exception as e:
                logger.debug(f"⚠️ {sym}: fast_info failed: {e}")

            # Method 2: Try historical data
            data = None
            periods_intervals = [("1d", "1h"), ("2d", "1d"), ("5d", "1d"), ("1mo", "1d")]

            for period, interval in periods_intervals:
                try:
                    data = ticker.history(period=period, interval=interval)
                    if data is not None and not data.empty and "Close" in data.columns:
                        break
                except Exception as e:
                    logger.debug(f"⚠️ {sym}: Failed to fetch {period}/{interval}: {e}")
                    continue

            if data is not None and not data.empty:
                try:
                    latest = data.iloc[-1]
                    # Try multiple price columns in order of preference
                    close_price = None
                    for price_col in ["Close", "Last", "regularMarketPrice", "currentPrice"]:
                        if price_col in data.columns:
                            close_price = latest.get(price_col)
                            if (
                                close_price is not None
                                and str(close_price).strip() != ""
                                and str(close_price).strip().lower() != "nan"
                            ):
                                break

                    # --- World-Class Safe Conversion ---
                    safe_price = safe_float_convert(
                        close_price, symbol=sym, context="historical Close price"
                    )
                    if safe_price is not None and 1.0 <= safe_price <= 1e10:
                        logger.debug(f"📊 {sym} Quote (historical): {safe_price:.2f}")
                        spread_pct = 0.0005
                        bid = safe_price * (1 - spread_pct / 2)
                        ask = safe_price * (1 + spread_pct / 2)
                        return {
                            "bid": bid,
                            "ask": ask,
                            "mid": safe_price,
                            "last": safe_price,
                            "regularMarketPrice": safe_price,
                            "currentPrice": safe_price,
                            "source": "yfinance_historical",
                        }
                    else:
                        logger.debug(f"⚠️ {sym}: No valid price found in historical data")
                except Exception as e:
                    logger.warning(f"⚠️ {sym}: Failed to parse historical data: {e}")

            # All methods failed - try to use cached price from price_history if available
            try:
                state_file = ROOT / "state" / "smart_trader_state.json"
                if state_file.exists():
                    cached_state = json.loads(state_file.read_text())
                    if sym in cached_state.get("price_history", {}):
                        price_list = cached_state["price_history"][sym]
                        if isinstance(price_list, list) and len(price_list) > 0:
                            cached_price = price_list[-1]
                            safe_price = safe_float_convert(
                                cached_price, symbol=sym, context="cached price_history"
                            )
                            if safe_price is not None and 1.0 <= safe_price <= 1e10:
                                logger.debug(f"📊 {sym} Quote (cached): {safe_price:.2f}")
                                spread_pct = 0.0005
                                return {
                                    "bid": safe_price * (1 - spread_pct / 2),
                                    "ask": safe_price * (1 + spread_pct / 2),
                                    "mid": safe_price,
                                    "last": safe_price,
                                    "regularMarketPrice": safe_price,
                                    "currentPrice": safe_price,
                                    "source": "cached",
                                }
            except Exception as cache_err:
                logger.debug(f"⚠️ Could not load cached price for {sym}: {cache_err}")

            # All methods failed
            logger.warning(f"⚠️ Could not fetch quote for {sym}: all methods failed")
            return None

        except Exception as e:
            logger.error(f"❌ Quote fetch error for {sym}: {e}", exc_info=True)
            # Try cached price as last resort
            try:
                state_file = ROOT / "state" / "smart_trader_state.json"
                if state_file.exists():
                    cached_state = json.loads(state_file.read_text())
                    if sym in cached_state.get("price_history", {}):
                        price_list = cached_state["price_history"][sym]
                        if isinstance(price_list, list) and len(price_list) > 0:
                            cached_price = price_list[-1]
                            safe_price = safe_float_convert(
                                cached_price, symbol=sym, context="cached fallback"
                            )
                            if safe_price is not None and 1.0 <= safe_price <= 1e10:
                                logger.debug(f"📊 {sym} Quote (cached fallback): {safe_price:.2f}")
                                spread_pct = 0.0005
                                return {
                                    "bid": safe_price * (1 - spread_pct / 2),
                                    "ask": safe_price * (1 + spread_pct / 2),
                                    "mid": safe_price,
                                    "last": safe_price,
                                    "regularMarketPrice": safe_price,
                                    "currentPrice": safe_price,
                                    "source": "cached_fallback",
                                }
            except Exception:
                pass
            return None

    def get_position(self, sym: str) -> dict[str, float]:
        return self._positions.get(sym, {"qty": 0.0, "avg_price": 0.0})

    def fetch_portfolio_value(self) -> float:
        """Calculate total portfolio value."""
        total = self._cash
        for sym, pos in self._positions.items():
            quote = self.fetch_quote(sym)
            if quote:
                price = quote.get("mid") or quote.get("last")
                safe_price = safe_float_convert(price, symbol=sym, context="portfolio valuation")
                if safe_price is not None:
                    total += pos["qty"] * safe_price
        self._equity = total
        return total

    def submit_order(self, sym: str, side: str, qty: float, price: float) -> dict[str, Any]:
        """Submit paper trade order with world-class price validation."""
        # --- World-Class Safe Conversion (GUARANTEED to never raise ValueError for empty string) ---
        # Use safe_float_convert for ALL conversions - this is the critical fix
        safe_price = safe_float_convert(price, symbol=sym, context="submit_order price")
        if safe_price is None:
            error_msg = f"Invalid price parameter: {price} ({type(price).__name__})"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        safe_qty = safe_float_convert(qty, symbol=sym, context="submit_order quantity")
        if safe_qty is None:
            error_msg = f"Invalid quantity parameter: {qty} ({type(qty).__name__})"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # Use safe converted values
        price = safe_price
        qty = safe_qty

        # Additional validation
        if qty <= 0:
            error_msg = f"Invalid quantity: {qty} (must be > 0)"
            logger.error(f"❌ {error_msg}")
            raise ValueError(error_msg)

        side = side.lower()

        # CRITICAL: Validate all internal state values before using them
        if not isinstance(self._cash, (int, float)):
            safe_cash = safe_float_convert(self._cash, symbol=sym, context="broker cash")
            if safe_cash is None:
                raise ValueError(f"Invalid broker cash: {self._cash!r}")
            self._cash = safe_cash

        fee = abs(qty * price * self.fee_rate)

        if side == "buy":
            cost = qty * price + fee
            if cost > self._cash:
                raise RuntimeError(f"Insufficient cash: need ${cost:.2f}, have ${self._cash:.2f}")
            self._cash -= cost
            pos = self.get_position(sym)

            # CRITICAL: Validate position values
            if not isinstance(pos.get("qty"), (int, float)):
                safe_qty_val = safe_float_convert(
                    pos.get("qty"), symbol=sym, context="position qty"
                )
                pos["qty"] = safe_qty_val if safe_qty_val is not None else 0.0
            if not isinstance(pos.get("avg_price"), (int, float)):
                safe_avg = safe_float_convert(
                    pos.get("avg_price"), symbol=sym, context="position avg_price"
                )
                pos["avg_price"] = safe_avg if safe_avg is not None else price

            if pos["qty"] > 0:
                # Average in
                total_cost = (pos["qty"] * pos["avg_price"]) + (qty * price)
                pos["qty"] += qty
                pos["avg_price"] = total_cost / pos["qty"]
            else:
                pos["qty"] = qty
                pos["avg_price"] = price
            self._positions[sym] = pos

        elif side == "sell":
            pos = self.get_position(sym)

            # CRITICAL: Validate position values
            if not isinstance(pos.get("qty"), (int, float)):
                safe_qty_val = safe_float_convert(
                    pos.get("qty"), symbol=sym, context="position qty"
                )
                pos["qty"] = safe_qty_val if safe_qty_val is not None else 0.0
            if not isinstance(pos.get("avg_price"), (int, float)):
                safe_avg = safe_float_convert(
                    pos.get("avg_price"), symbol=sym, context="position avg_price"
                )
                pos["avg_price"] = safe_avg if safe_avg is not None else price

            if qty > pos["qty"] + 1e-6:
                raise RuntimeError(
                    f"Insufficient position: trying to sell {qty}, have {pos['qty']}"
                )

            # CRITICAL: Ensure avg_price is valid before calculation
            avg_price = pos["avg_price"]
            if not isinstance(avg_price, (int, float)) or avg_price <= 0:
                logger.error(f"❌ Invalid avg_price for {sym}: {avg_price!r} ({type(avg_price)})")
                avg_price = price  # Fallback to current price

            pnl = (price - avg_price) * qty
            proceeds = qty * price - fee
            self._cash += proceeds
            pos["qty"] -= qty
            if pos["qty"] <= 1e-6:
                self._positions.pop(sym, None)
                # Realize P&L
                self._equity += pnl
            else:
                self._positions[sym] = pos
        else:
            raise RuntimeError(f"Invalid side: {side}")

        # Record trade (with safe conversion to prevent errors in record_fill)
        try:
            # CRITICAL: Ensure all values are valid floats before passing to record_fill
            # record_fill does float(qty), float(price), float(fee) which can fail on empty strings
            safe_fee = (
                fee
                if isinstance(fee, (int, float))
                else (safe_float_convert(fee, symbol=sym, context="fee") or 0.0)
            )
            record_fill(sym, side, float(qty), float(price), float(safe_fee), note="paper_trade")
        except (ValueError, TypeError) as e:
            # Don't fail the trade if record_fill fails
            logger.warning(f"⚠️ Failed to record fill for {sym}: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Unexpected error in record_fill for {sym}: {e}")

        # Emit trading event (Phase 3900-4100: Event-Driven Architecture)
        try:
            from phases.phase_3900_4100_events import process_event

            process_event(
                side.upper(),
                {
                    "symbol": sym,
                    "quantity": float(qty),
                    "price": float(price),
                    "fee": float(safe_fee),
                    "pnl": float(pnl) if side == "sell" else 0.0,
                    "equity": float(self._equity),
                    "cash": float(self._cash),
                },
                source="smart_trader",
            )
        except ImportError:
            pass  # Event system not available
        except Exception as e:
            logger.debug(f"Event emission failed: {e}")

        return {
            "filled_qty": qty,
            "filled_price": price,
            "fee": fee,
            "pnl": pnl if side == "sell" else 0.0,
        }


# =============== SIGNAL GENERATION ==================
def load_market_intelligence(sym: str) -> Optional[dict[str, Any]]:
    """Load market intelligence for symbol."""
    intel_file = ROOT / "state" / "market_intelligence.json"
    if intel_file.exists():
        try:
            data = json.loads(intel_file.read_text())
            return data.get("signals", {}).get(sym)
        except:
            pass
    return None


def load_active_strategies() -> list[str]:
    """Load top-performing strategies from strategy_research agent."""
    strategies_file = ROOT / "state" / "strategy_performance.json"
    if strategies_file.exists():
        try:
            data = json.loads(strategies_file.read_text())
            active = data.get("active_strategies", [])
            # Extract strategy names - handle both string and dict formats
            strategies = []
            for s in active:
                if isinstance(s, str):
                    strategies.append(s)
                elif isinstance(s, dict):
                    strategy_name = s.get("strategy")
                    if strategy_name:
                        strategies.append(strategy_name)
            if strategies:
                return strategies
            # Fallback to ranked strategies (top 5)
            ranked = data.get("ranked_strategies", [])
            ranked_strategies = []
            for s in ranked[:5]:
                if isinstance(s, str):
                    ranked_strategies.append(s)
                elif isinstance(s, dict):
                    strategy_name = s.get("strategy")
                    if strategy_name:
                        ranked_strategies.append(strategy_name)
            if ranked_strategies:
                return ranked_strategies
        except Exception as e:
            print(f"⚠️  Error loading strategies: {e}", flush=True)
    # Default fallback
    return [
        "turtle_trading",
        "mean_reversion_rsi",
        "momentum_sma_crossover",
        "pairs_trading",
        "vix_strategy",
    ]


def generate_signal(
    broker: PaperBroker, sym: str, prices: deque, risk_scaler: float, confidence: float
) -> tuple[Optional[str], dict[str, Any]]:
    """Generate buy/sell signal using multi-source intelligence and return metadata for downstream attribution."""
    # Reduced minimum data requirement from 50 to 20 for faster signal generation
    if len(prices) < 20:
        return None

    price_list = list(prices)
    current_price = price_list[-1]

    # Calculate technical indicators
    sma_20 = sma(price_list, 20)
    sma_50 = sma(price_list, 50) if len(price_list) >= 50 else None
    rsi_val = rsi(price_list, 14)
    momentum = calculate_momentum(price_list, window=5)  # Calculate momentum

    if not all([sma_20, rsi_val]):
        return None

    # Get current position
    pos = broker.get_position(sym)
    has_position = pos["qty"] > 1e-6

    # Load market intelligence
    intel = load_market_intelligence(sym)
    market_sentiment = intel.get("composite_sentiment", 0.0) if intel else 0.0
    market_recommendation = intel.get("recommendation", "HOLD") if intel else "HOLD"

    # Load active strategies (use Strategy Manager if available)
    if HAS_STRATEGY_MANAGER:
        try:
            from agents.strategy_manager import StrategyManager

            sm = StrategyManager()
            active_strategies = sm.get_active_strategies()
        except:
            active_strategies = load_active_strategies()
    else:
        active_strategies = load_active_strategies()

    # Strategy signals (vote-based)
    strategy_votes = {"buy": 0, "sell": 0, "hold": 0}
    strategy_signals = {}  # Store individual strategy signals for executor

    # Strategy 1: Turtle Trading (Trend Following)
    if "turtle_trading" in active_strategies:
        high_20 = max(price_list[-20:])
        low_10 = min(price_list[-10:]) if len(price_list) >= 10 else current_price
        if current_price > high_20 and not has_position:
            strategy_votes["buy"] += 1
        elif current_price < low_10 and has_position:
            strategy_votes["sell"] += 1

    # Strategy 2: Mean Reversion (RSI)
    # TEST MODE: Lowered thresholds for testing (was 30/70, now 45/55)
    if "mean_reversion_rsi" in active_strategies:
        if rsi_val < 60 and not has_position:  # TEST MODE: More aggressive (was 30)
            strategy_votes["buy"] += 1
        elif rsi_val > 55 and has_position:  # TEST MODE: More aggressive (was 70)
            strategy_votes["sell"] += 1

    # Strategy 3: Momentum SMA Crossover
    if "momentum_sma_crossover" in active_strategies and sma_50:
        if sma_20 > sma_50 and current_price > sma_20 and not has_position:
            strategy_votes["buy"] += 1
        elif sma_20 < sma_50 and has_position:
            strategy_votes["sell"] += 1

    # Strategy 4: Pairs Trading (Statistical Arbitrage) - TOP STRATEGY (1.8 Sharpe)
    if "pairs_trading" in active_strategies:
        # For pairs trading, need another correlated symbol
        # Simplified: use SPY/QQQ correlation
        if sym in ["SPY", "QQQ"]:
            # Would need price history of pair - placeholder for now
            # In full implementation, calculate spread Z-score
            pass

    # Strategy 5: VIX Fear Greed Strategy (1.6 Sharpe)
    if "vix_strategy" in active_strategies:
        # VIX strategy: buy when fear (VIX high), sell when greed (VIX low)
        # Simplified: check if we have VIX data or proxy
        # This would require separate VIX data feed
        pass

    # Strategy 6: Breakout Trading (Bollinger Bands)
    if "breakout_trading" in active_strategies:
        bb = bollinger_bands(price_list, 20, 2.0)
        if bb:
            if current_price > bb["upper"] and not has_position:
                strategy_votes["buy"] += 1  # Breakout above upper band
            elif current_price < bb["lower"] and has_position:
                strategy_votes["sell"] += 1  # Break below lower band

    # Strategy 7: MACD Momentum
    if "macd_momentum" in active_strategies:
        macd_data = macd(price_list, 12, 26, 9)
        if macd_data:
            if (
                macd_data["macd"] > macd_data["signal"]
                and macd_data["histogram"] > 0
                and not has_position
            ):
                strategy_votes["buy"] += 1
            elif macd_data["macd"] < macd_data["signal"] and has_position:
                strategy_votes["sell"] += 1

    # Strategy 8: Bollinger Bands Mean Reversion
    if "bollinger_bands" in active_strategies:
        bb = bollinger_bands(price_list, 20, 2.0)
        if bb:
            if current_price < bb["lower"] and not has_position:
                strategy_votes["buy"] += 1  # Oversold - mean reversion buy
            elif current_price > bb["upper"] and has_position:
                strategy_votes["sell"] += 1  # Overbought - mean reversion sell

    # === MULTI-STRATEGY EXECUTOR (Phase 3500-3700) ===
    # Use Strategy Executor to combine signals if available
    # Note: strategy_executor is initialized in main() - skip executor for now
    # (strategy_executor would need to be passed as parameter or made global)
    tech_signal = None  # Will be determined by vote-based system below

    # Combine signals with market intelligence
    final_signal = None

    # Technical signal (from strategies or executor)
    if tech_signal is None:
        if strategy_votes["buy"] > strategy_votes["sell"] and strategy_votes["buy"] > 0:
            tech_signal = "buy"
        elif strategy_votes["sell"] > strategy_votes["buy"] and strategy_votes["sell"] > 0:
            tech_signal = "sell"

    # ADAPTIVE SIGNAL WEIGHTING: Momentum + Confidence fusion
    # If confidence > 0.7 and momentum < 0, bias toward SELL
    # If confidence > 0.7 and momentum > 0, bias toward BUY
    momentum_bias = None
    if confidence > 0.7 and momentum is not None:
        if momentum < 0:
            momentum_bias = "sell"
        elif momentum > 0:
            momentum_bias = "buy"

    # CRYPTO: More aggressive BUY signals for 24/7 trading
    # Check RSI-based signals FIRST (before strategy confirmation) to ensure they work
    # Made more aggressive: crypto RSI < 75 (was 70), stocks RSI < 65 (was 60)
    crypto_symbol = "-USD" in sym
    if crypto_symbol and rsi_val is not None and rsi_val < 75 and not has_position:
        final_signal = "buy"  # Direct RSI buy signal for crypto
        logger.info(f"🪙 CRYPTO: Direct RSI buy signal for {sym} (RSI={rsi_val:.1f} < 75)")
    elif not crypto_symbol and rsi_val is not None and rsi_val < 65 and not has_position:
        final_signal = "buy"  # Direct RSI buy signal for stocks/testing
        logger.info(f"🧪 TEST MODE: Direct RSI buy signal for {sym} (RSI={rsi_val:.1f} < 65)")

    # Market intelligence confirmation (only if no RSI signal was set)
    if final_signal is None:
        if tech_signal == "buy":
            # Buy if technical + positive sentiment OR high confidence OR positive momentum bias
            # ENHANCED: More permissive for crypto trading - allow buys with lower thresholds
            if crypto_symbol:
                # Crypto: More aggressive buying (lower thresholds)
                if (
                    market_sentiment > 0.1
                    or (market_recommendation == "BUY" and confidence > 0.4)
                    or momentum_bias == "buy"
                    or confidence > 0.5
                ):
                    final_signal = "buy"
                elif confidence < 0.2:  # Skip only if very low confidence
                    final_signal = None
                else:
                    final_signal = "buy"  # Technical signal strong enough for crypto
            else:
                # Stocks: Original logic
                if (
                    market_sentiment > 0.2
                    or (market_recommendation == "BUY" and confidence > 0.5)
                    or momentum_bias == "buy"
                ):
                    final_signal = "buy"
                elif confidence < 0.3:  # Skip if low confidence
                    final_signal = None
                else:
                    final_signal = "buy"  # Technical signal strong enough

        elif tech_signal == "sell":
            # Sell if technical signal OR negative sentiment OR negative momentum bias
            if (
                market_sentiment < -0.2
                or market_recommendation == "SELL"
                or momentum_bias == "sell"
            ):
                final_signal = "sell"
            else:
                final_signal = "sell"  # Technical exit signal

    # ENHANCED SELL LOGIC: RSI > 80 and position > 0 triggers sell (override any buy signal)
    if rsi_val is not None and rsi_val > 80 and has_position:
        final_signal = "sell"  # Overbought - force sell

    # ============================================================================
    # AI-ENHANCED SIGNAL GENERATION (World-Class Integration)
    # ============================================================================
    ai_analysis = None
    ai_signal_override = None
    ai_confidence_boost = 0.0
    ai_reasoning = None

    try:
        # Import AI client (graceful fallback if unavailable)
        from utils.agent_ai_client import analyze_trading_signal

        # Prepare indicators dict for AI
        indicators_dict = {
            "rsi": rsi_val,
            "momentum": momentum,
            "sma_20": sma_20,
            "sma_50": sma_50,
        }

        # Add MACD if available
        macd_data = macd(price_list, 12, 26, 9) if len(price_list) >= 26 else None
        if macd_data:
            indicators_dict["macd"] = macd_data.get("macd")
            indicators_dict["macd_signal"] = macd_data.get("signal")
            indicators_dict["macd_histogram"] = macd_data.get("histogram")

        # Add Bollinger Bands if available
        bb = bollinger_bands(price_list, 20, 2.0)
        if bb:
            indicators_dict["bb_upper"] = bb.get("upper")
            indicators_dict["bb_lower"] = bb.get("lower")
            indicators_dict["bb_middle"] = bb.get("middle")

        # Determine if this is a critical decision (use RapidAPI)
        # Critical: Large position (>10% portfolio) or high-value trade (>$10k)
        portfolio_value = broker.fetch_portfolio_value()
        current_position_value = broker.get_position(sym).get("qty", 0.0) * current_price
        is_critical = (
            current_position_value > portfolio_value * 0.1  # >10% portfolio
            or current_position_value > 10000  # >$10k position
            or (final_signal == "buy" and portfolio_value * 0.1 > 10000)  # New large buy
        )

        # Get AI analysis (use RapidAPI for critical, Ollama for daily)
        use_rapidapi = is_critical and final_signal in ["buy", "sell"]

        logger.debug(
            f"🤖 AI Analysis [{sym}]: "
            f"critical={is_critical} | "
            f"use_rapidapi={use_rapidapi} | "
            f"current_signal={final_signal}"
        )

        ai_analysis = analyze_trading_signal(
            symbol=sym, price=current_price, indicators=indicators_dict, use_rapidapi=use_rapidapi
        )

        if ai_analysis:
            ai_signal = ai_analysis.get("signal", "HOLD").upper()
            ai_confidence = ai_analysis.get("confidence", 0.5)
            ai_risk = ai_analysis.get("risk", "MEDIUM")
            ai_reasoning = ai_analysis.get("reasoning", "")

            # AI signal override logic (only if AI is very confident)
            if ai_confidence > 0.7:
                if ai_signal in ["BUY", "SELL"]:
                    # AI override: only if AI confidence > 0.7 and contradicts current signal
                    if final_signal and ai_signal.lower() != final_signal.lower():
                        logger.info(
                            f"🤖 AI OVERRIDE [{sym}]: "
                            f"Technical={final_signal} → AI={ai_signal.lower()} "
                            f"(confidence={ai_confidence:.2f}, risk={ai_risk})"
                        )
                        ai_signal_override = ai_signal.lower()
                    elif not final_signal and ai_signal in ["BUY", "SELL"]:
                        # AI provides signal when technical doesn't
                        logger.info(
                            f"🤖 AI SIGNAL [{sym}]: "
                            f"AI={ai_signal.lower()} "
                            f"(confidence={ai_confidence:.2f}, risk={ai_risk})"
                        )
                        ai_signal_override = ai_signal.lower()

            # AI confidence boost (enhance existing signal)
            if final_signal and ai_signal.lower() == final_signal.lower():
                # AI confirms technical signal - boost confidence
                ai_confidence_boost = min(0.2, ai_confidence * 0.2)
                logger.debug(
                    f"✅ AI CONFIRMATION [{sym}]: "
                    f"Signal={final_signal} confirmed "
                    f"(boost={ai_confidence_boost:.2f}, reasoning={ai_reasoning[:50] if ai_reasoning else 'N/A'}...)"
                )
            elif final_signal and ai_signal.lower() != final_signal.lower():
                # AI contradicts - reduce confidence
                ai_confidence_boost = -min(0.15, ai_confidence * 0.15)
                logger.debug(
                    f"⚠️ AI CONTRADICTION [{sym}]: "
                    f"Technical={final_signal} vs AI={ai_signal.lower()} "
                    f"(penalty={ai_confidence_boost:.2f})"
                )

            # Log AI analysis for monitoring
            logger.info(
                f"🤖 AI ANALYSIS [{sym}]: "
                f"signal={ai_signal} | "
                f"confidence={ai_confidence:.2f} | "
                f"risk={ai_risk} | "
                f"reasoning={ai_reasoning[:80] if ai_reasoning else 'N/A'}..."
            )
        else:
            logger.debug(f"⚠️ AI analysis unavailable for {sym} (Ollama/RapidAPI may be down)")

    except ImportError:
        logger.debug("⚠️ AI client not available (utils/agent_ai_client.py not found)")
    except Exception as e:
        logger.warning(f"⚠️ AI analysis failed for {sym}: {e}", exc_info=False)
        # Don't fail signal generation if AI fails - graceful degradation

    # Apply AI override if available and confident
    if ai_signal_override and ai_analysis and ai_analysis.get("confidence", 0) > 0.7:
        final_signal = ai_signal_override
        logger.info(f"🎯 AI OVERRIDE APPLIED [{sym}]: {final_signal}")

    # Apply AI confidence boost
    if ai_confidence_boost != 0.0:
        confidence = max(0.0, min(1.0, confidence + ai_confidence_boost))
        logger.debug(f"📈 Confidence adjusted: {confidence:.2f} (boost={ai_confidence_boost:+.2f})")

    # Risk scaling: reduce position size if low confidence
    # TEST MODE: Lowered to 0.1 for easier testing (was 0.3)
    # Very low confidence (< 0.1) still blocks to prevent bad trades
    if final_signal == "buy" and confidence < 0.1:  # TEST MODE: Very permissive for testing
        final_signal = None  # Skip trades only if confidence extremely low

    # ADDITIONAL FILTERING: Require stronger signal consensus
    # Reduced threshold to 0 for more trading activity (was 1) - allow trades even without strategy votes if RSI condition met
    vote_threshold = 0  # Allow trades without strategy votes (for testing)
    # Only block if we have explicit sell votes and no buy votes
    if final_signal == "buy" and strategy_votes["sell"] > strategy_votes["buy"]:
        final_signal = None  # Block if sell votes outweigh buy votes

    if final_signal == "sell" and strategy_votes["sell"] < vote_threshold:
        # Allow sells with single strategy (exit protection)
        pass

    # Emit signal event (Phase 3900-4100: Event-Driven Architecture)
    metadata = {
        "strategy_votes": strategy_votes,
        "strategy_signals": strategy_signals,
        "active_strategies": active_strategies,
        "market_sentiment": market_sentiment,
        "confidence": confidence,
        "momentum": momentum,
        "rsi": rsi_val,
        "has_position": has_position,
    }

    if final_signal:
        try:
            from phases.phase_3900_4100_events import process_event

            process_event(
                f"SIGNAL_{final_signal.upper()}",
                {
                    "symbol": sym,
                    "signal": final_signal,
                    "confidence": confidence,
                    "risk_scaler": risk_scaler,
                    "rsi": float(rsi_val) if rsi_val else None,
                    "momentum": float(momentum) if momentum else None,
                    "strategy_votes": strategy_votes,
                    "market_sentiment": market_sentiment,
                    "has_position": has_position,
                },
                source="signal_generator",
            )
        except ImportError:
            pass  # Event system not available
        except Exception as e:
            logger.debug(f"Signal event emission failed: {e}")

    return final_signal, metadata


# =============== LOAD CONFIG ==================
def load_allocations() -> dict[str, float]:
    """
    Load target allocations.
    CRITICAL: Only returns valid trading symbols, filters out strategy names.
    """
    candidate_files = [
        (ROOT / "runtime" / "allocations_symbols.json", "allocations_symbols"),
        (ROOT / "runtime" / "allocations_override.json", "allocations_override"),
    ]

    strategy_name_patterns = [
        "trading",
        "strategy",
        "reversion",
        "momentum",
        "breakout",
        "bollinger",
        "vix",
        "pairs",
        "turtle",
        "macd",
    ]

    def extract_valid_symbols(raw: dict[str, float]) -> dict[str, float]:
        valid: dict[str, float] = {}
        for key, value in raw.items():
            is_strategy_name = any(pattern in key.lower() for pattern in strategy_name_patterns)
            if is_strategy_name:
                logger.debug(f"⚠️ Skipping strategy name in allocations: {key}")
                continue
            if "-" in key or (len(key) <= 5 and key.isupper()):
                valid[key] = value
        return valid

    for path, label in candidate_files:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            allocations = data.get("allocations", {}) if isinstance(data, dict) else {}
            if isinstance(allocations, dict) and allocations:
                valid_symbols = extract_valid_symbols(allocations)
                if valid_symbols:
                    logger.info(
                        f"✅ Loaded {len(valid_symbols)} valid trading symbols from {label}.json"
                    )
                    return valid_symbols
                else:
                    logger.debug(f"⚠️ {label}.json did not contain valid trading symbols")
        except Exception as e:
            logger.warning(f"⚠️ Error loading {label}.json allocations: {e}, continuing fallback")

    # Default allocations - Crypto 24/7 + Top Stocks/Commodities
    default_allocations = {
        # Crypto (24/7 trading)
        "BTC-USD": 0.12,
        "ETH-USD": 0.10,
        "SOL-USD": 0.06,
        # Large-cap equities & tech leaders (market hours)
        "SPY": 0.08,
        "QQQ": 0.08,
        "AAPL": 0.06,
        "MSFT": 0.06,
        "NVDA": 0.06,
        "TSLA": 0.04,
        # Commodities / diversifiers
        "GLD": 0.05,
        "SLV": 0.04,
        "USO": 0.04,
        # Broad index & bond funds (market hours)
        "VTSAX": 0.05,  # Vanguard Total Stock Market Index Fund Admiral Shares
        "VFIAX": 0.05,  # Vanguard 500 Index Fund Admiral Shares
        "FXAIX": 0.05,  # Fidelity 500 Index Fund
        "VTIAX": 0.05,  # Vanguard Total International Stock Index Fund Admiral Shares
        "VBTLX": 0.05,  # Vanguard Total Bond Market Index Fund Admiral Shares
        "VOO": 0.05,  # Vanguard S&P 500 ETF
        "SWPPX": 0.04,  # Schwab S&P 500 Index Fund
    }

    # Validate allocations sum to 1.0 (or close, with tolerance for rounding)
    total = sum(default_allocations.values())
    if abs(total - 1.0) > 0.01:  # Allow 1% tolerance
        logger.warning(f"⚠️ Default allocations sum to {total:.3f}, normalizing to 1.0")
        default_allocations = {k: v / total for k, v in default_allocations.items()}

    return default_allocations


def load_brain() -> dict[str, float]:
    """Load orchestrator brain state."""
    brain_file = ROOT / "runtime" / "atlas_brain.json"
    if brain_file.exists():
        try:
            brain = json.loads(brain_file.read_text())
            # Ensure confidence is reasonable (not too low)
            if brain.get("confidence", 0.5) < 0.1:
                brain["confidence"] = 0.5  # Reset very low confidence to default
            return brain
        except:
            pass
    return {"risk_scaler": 1.0, "confidence": 0.5}


# =============== ATLAS BRIDGE INTEGRATION ==================
def send_to_atlas_bridge(data: dict[str, Any]) -> bool:
    """Send telemetry data to Atlas Bridge for dashboard integration."""
    try:
        import requests  # type: ignore

        dashboard_url = os.getenv("NEOLIGHT_DASHBOARD_URL", "http://localhost:8100")
        response = requests.post(f"{dashboard_url}/atlas/update", json=data, timeout=5)
        return response.status_code == 200
    except Exception:
        return False  # Silent fail if dashboard not available


# =============== PERFORMANCE ATTRIBUTION ==================
def track_trade_decision(
    symbol: str,
    side: str,
    reasoning: str,
    rsi: Optional[float],
    momentum: Optional[float],
    confidence: float,
) -> Optional[int]:
    """Track trade decision for performance attribution. Returns decision index."""
    try:
        sys.path.insert(0, str(ROOT))
        from agents.performance_attribution import track_decision

        agent_name = "SmartTrader"
        decision_str = f"{side.upper()} {symbol}"
        reasoning_full = (
            f"RSI={rsi:.1f}, Momentum={momentum:.3f}%, Confidence={confidence:.2f} | {reasoning}"
            if rsi and momentum
            else f"Confidence={confidence:.2f} | {reasoning}"
        )

        track_decision(agent_name, decision_str, reasoning_full)

        # Get decision index (latest decision)
        attribution_file = ROOT / "state" / "performance_attribution.json"
        if attribution_file.exists():
            data = json.loads(attribution_file.read_text())
            decisions = data.get("decisions", [])
            return len(decisions) - 1 if decisions else None
    except Exception:
        pass  # Silent fail if attribution not available
    return None


def update_trade_pnl(decision_idx: Optional[int], pnl: float) -> None:
    """Update P&L for tracked trade decision."""
    if decision_idx is None:
        return
    try:
        sys.path.insert(0, str(ROOT))
        from agents.performance_attribution import update_decision_pnl

        update_decision_pnl(decision_idx, pnl)
    except Exception:
        pass  # Silent fail


# =============== GUARDIAN AUTOPAUSE ==================
def check_guardian_pause(broker: PaperBroker, state: dict[str, Any]) -> tuple[bool, float, str]:
    """
    Check if Guardian wants to pause trading (drawdown protection).
    Returns: (is_paused, current_drawdown_pct, reason)
    """
    try:
        # Check drawdown threshold (15% default for paper trading, 8% for live)
        trading_mode = os.getenv("NEOLIGHT_TRADING_MODE", "PAPER_MODE")
        default_threshold = "15.0" if trading_mode == "PAPER_MODE" else "8.0"
        max_drawdown_pct = float(os.getenv("NEOLIGHT_MAX_DRAWDOWN_PCT", default_threshold))
        start_equity = state["daily"].get("start_equity", broker.equity)

        # Ensure start_equity is valid (not zero or negative)
        if start_equity <= 0:
            start_equity = broker.equity
            state["daily"]["start_equity"] = start_equity

        daily_pnl_pct = (broker.equity - start_equity) / max(1.0, start_equity) * 100
        current_drawdown = -daily_pnl_pct if daily_pnl_pct < 0 else 0.0

        # Only pause if drawdown is significant AND we have enough trades to be meaningful
        total_trades = state.get("total_trades", 0)
        min_trades_for_pause = 5  # Don't pause on early drawdowns

        if daily_pnl_pct <= -max_drawdown_pct and total_trades >= min_trades_for_pause:
            reason = (
                f"Daily drawdown {current_drawdown:.2f}% exceeds threshold (-{max_drawdown_pct}%)"
            )
            print(f"⏸️ GUARDIAN AUTOPAUSE: {reason}", flush=True)
            send_telegram(
                f"⏸️ Guardian AutoPause\n"
                f"📉 Drawdown: {current_drawdown:.2f}%\n"
                f"Trades: {total_trades}",
                include_mode=True,
                state=state,
            )
            return (True, current_drawdown, reason)

        # Check for Guardian pause signal file
        pause_file = ROOT / "state" / "guardian_pause.json"
        if pause_file.exists():
            try:
                pause_data = json.loads(pause_file.read_text())
                if pause_data.get("paused", False):
                    pause_until_raw = pause_data.get("until")
                    if pause_until_raw:
                        try:
                            pause_until = dt.datetime.fromisoformat(
                                pause_until_raw.replace("Z", "+00:00")
                            )
                        except ValueError:
                            pause_until = None
                        if pause_until and dt.datetime.now(dt.UTC) >= pause_until:
                            pause_file.unlink(missing_ok=True)
                            return (False, current_drawdown, "Guardian pause expired")
                    reason = pause_data.get("reason", "Guardian intervention")
                    print(f"⏸️ GUARDIAN PAUSED: {reason}", flush=True)
                    return (True, current_drawdown, reason)
            except:
                pass

        return (False, current_drawdown, "Normal operation")

    except Exception:
        return (False, 0.0, "Error checking pause status")


# =============== CIRCUIT BREAKER ==================
class CircuitBreaker:
    """Circuit breaker pattern for error handling with state change tracking."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,
        name: str = "CircuitBreaker",
        half_open_success_threshold: int = 2,
        half_open_failure_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.previous_state = "CLOSED"  # Track state changes for alerts
        self.state_changed = False

        # HALF_OPEN recovery tracking
        self.half_open_success_threshold = (
            half_open_success_threshold  # Require N successes to close
        )
        self.half_open_failure_threshold = (
            half_open_failure_threshold  # Allow N failures before re-opening
        )
        self.half_open_success_count = 0
        self.half_open_failure_count = 0

    def record_success(self):
        """Record successful operation."""
        self.previous_state = self.state

        if self.state == "HALF_OPEN":
            # In HALF_OPEN, track successes for recovery
            self.half_open_success_count += 1
            self.half_open_failure_count = 0  # Reset failure count on success

            # If we've achieved enough successes, close the circuit
            if self.half_open_success_count >= self.half_open_success_threshold:
                self.state_changed = True
                self.state = "CLOSED"
                self.failure_count = 0
                self.half_open_success_count = 0
                self.half_open_failure_count = 0
                print(
                    f"🟢 {self.name} CLOSED after {self.half_open_success_count} successful recovery attempts",
                    flush=True,
                )
            else:
                self.state_changed = False
        else:
            # In CLOSED state, reset counters
            self.failure_count = 0
            if self.state != "CLOSED":
                self.state_changed = True
                self.state = "CLOSED"
            else:
                self.state_changed = False
            self.half_open_success_count = 0
            self.half_open_failure_count = 0

    def record_failure(self):
        """Record failed operation."""
        self.previous_state = self.state
        self.last_failure_time = time.time()

        if self.state == "HALF_OPEN":
            # In HALF_OPEN, track failures for re-opening
            self.half_open_failure_count += 1
            self.half_open_success_count = 0  # Reset success count on failure

            # If we've exceeded the failure threshold, re-open the circuit
            if self.half_open_failure_count >= self.half_open_failure_threshold:
                self.state_changed = True
                self.state = "OPEN"
                self.failure_count = self.failure_threshold  # Set to threshold to keep it open
                self.half_open_success_count = 0
                self.half_open_failure_count = 0
                print(
                    f"🔴 {self.name} RE-OPENED after {self.half_open_failure_threshold} failures in HALF_OPEN",
                    flush=True,
                )
            else:
                self.state_changed = False
        elif self.state == "OPEN":
            # In OPEN state, don't increment failure_count (already open)
            # Just update the timestamp
            self.state_changed = False
        else:
            # In CLOSED state, track failures normally
            self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                self.state_changed = True
                self.state = "OPEN"
                print(f"🔴 {self.name} OPENED after {self.failure_count} failures", flush=True)
            else:
                self.state_changed = False
        else:
            self.state_changed = False

    def can_proceed(self) -> bool:
        """Check if operation can proceed."""
        self.state_changed = False
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.previous_state = self.state
                self.state = "HALF_OPEN"
                self.state_changed = True
                # Reset HALF_OPEN counters when entering HALF_OPEN
                self.half_open_success_count = 0
                self.half_open_failure_count = 0
                print(f"🟡 {self.name} HALF_OPEN (recovery attempt)", flush=True)
                return True
            return False
        else:  # HALF_OPEN
            return True

    def get_state_info(self) -> dict[str, Any]:
        """Get current state information for telemetry."""
        info = {
            "state": self.state,
            "previous_state": self.previous_state,
            "state_changed": self.state_changed,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "time_until_recovery": max(
                0, self.recovery_timeout - (time.time() - self.last_failure_time)
            )
            if self.last_failure_time
            else 0,
        }
        # Add HALF_OPEN tracking info if in HALF_OPEN state
        if self.state == "HALF_OPEN":
            info["half_open_success_count"] = self.half_open_success_count
            info["half_open_failure_count"] = self.half_open_failure_count
            info["half_open_success_threshold"] = self.half_open_success_threshold
            info["half_open_failure_threshold"] = self.half_open_failure_threshold
        return info


# =============== MAIN LOOP ==================
def main():
    """
    SmartTrader Main Entrypoint
    Phase 5600+ Compliant | Supports Mode Persistence & Safe State
    World-class: Robust error handling, state persistence, graceful recovery
    """
    global state
    global logger

    # --- Step 0: Load environment variables from .env file ---
    try:
        from dotenv import load_dotenv  # type: ignore

        env_path = ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("✅ Loaded environment variables from .env file")
        else:
            logger.debug("⚠️ .env file not found, using system environment")
    except ImportError:
        logger.debug("⚠️ python-dotenv not available, using system environment")
    except Exception as e:
        logger.warning(f"⚠️ Failed to load .env file: {e}")

    # --- Step 1: Initialize state safely (load from file or create new) ---
    # WORLD-CLASS: Use atomic state manager
    state = {}
    state_file = ROOT / "state" / "trader_state.json"

    if HAS_WORLD_CLASS_UTILS:
        try:
            state_manager = StateManager(
                state_file, default_state={}, backup_count=24, backup_interval=3600.0
            )
            state = state_manager.load()
            logger.info("📂 Loaded state using atomic StateManager")
        except Exception as e:
            logger.warning(f"⚠️ StateManager failed, using fallback: {e}")
            state = {}
    else:
        # Fallback to original method
        try:
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                    logger.info("📂 Loaded existing trader_state.json")
            else:
                state = {}
                logger.info("🆕 No existing state found — starting fresh.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load trader_state.json: {e}")
            state = {}

    # Convert price_history lists back to deque if needed
    if "price_history" in state:
        for sym, prices in state["price_history"].items():
            if isinstance(prices, list):
                state["price_history"][sym] = deque(prices, maxlen=200)
            elif not isinstance(prices, deque):
                state["price_history"][sym] = deque(maxlen=200)

    # Ensure required state keys exist
    if "daily" not in state:
        state["daily"] = {}
    if "price_history" not in state:
        state["price_history"] = {}
    if "last_trade" not in state:
        state["last_trade"] = {}
    if "trade_count" not in state:
        state["trade_count"] = 0
    if "test_sells" not in state:
        state["test_sells"] = 0
    if "test_trade_executed" not in state:
        state["test_trade_executed"] = False

    # --- Step 2: Load trading mode from persistence ---
    trading_mode = "TEST_MODE"  # Default
    mode_file = ROOT / "state" / "trading_mode.json"

    try:
        if mode_file.exists():
            with open(mode_file) as f:
                mode_data = json.load(f)
                persisted_mode = mode_data.get("mode", "TEST_MODE")
                if persisted_mode in ["TEST_MODE", "PAPER_TRADING_MODE", "LIVE_MODE"]:
                    trading_mode = persisted_mode
                    logger.info(f"🔁 Loaded trading mode: {trading_mode}")
                else:
                    logger.warning(
                        f"⚠️ Invalid mode in file: {persisted_mode}, defaulting to TEST_MODE"
                    )
        else:
            trading_mode = "TEST_MODE"
            logger.info("⚙️ No mode file found — defaulting to TEST_MODE")
    except Exception as e:
        logger.error(f"❌ Error loading trading_mode.json: {e}")
        trading_mode = "TEST_MODE"

    # --- Step 3: Bind mode to state & persist immediately ---
    state["trading_mode"] = trading_mode

    try:
        # Ensure state directory exists
        (ROOT / "state").mkdir(parents=True, exist_ok=True)

        # Save state
        state_to_save = state.copy()
        # Convert deque to list for JSON serialization
        if "price_history" in state_to_save:
            state_to_save["price_history"] = {
                sym: list(prices) if isinstance(prices, deque) else prices
                for sym, prices in state_to_save["price_history"].items()
            }

        # WORLD-CLASS: Use atomic state save if available
        if HAS_WORLD_CLASS_UTILS and "state_manager" in locals():
            state_manager.save(state_to_save)
            logger.info(f"💾 State saved atomically with mode={trading_mode}")
        else:
            # Fallback to original method
            with open(state_file, "w") as f:
                json.dump(state_to_save, f, indent=4)
            logger.info(f"💾 State initialized with mode={trading_mode}")
    except Exception as e:
        logger.warning(f"⚠️ Could not save trader_state.json: {e}")

    # --- Step 4: Initialize QuoteService (if available) ---
    quote_service = None
    if HAS_QUOTE_SERVICE:
        try:
            quote_service = get_quote_service()
            logger.info("✅ QuoteService initialized (world-class immutable quotes)")
            logger.info(
                f"📊 Quote sources: Alpaca={'✅' if os.getenv('NEOLIGHT_USE_ALPACA_QUOTES', 'false').lower() == 'true' else '❌'} | "
                f"Finnhub={'✅' if os.getenv('FINNHUB_API_KEY') else '❌'} | "
                f"TwelveData={'✅' if os.getenv('TWELVEDATA_API_KEY') else '❌'} | "
                f"Yahoo={'✅' if HAS_YFINANCE else '❌'}"
            )
        except Exception as e:
            logger.warning(f"⚠️ QuoteService initialization failed: {e}")
            quote_service = None

    # --- Step 5: Initialize Paper Broker ---
    broker = PaperBroker()
    logger.info(f"✅ Paper Broker initialized with ${broker.equity:,.2f} equity")

    # --- Step 6: Initialize Health Check (WORLD-CLASS) ---
    health_check = None
    if HAS_WORLD_CLASS_UTILS:
        try:
            health_check = HealthCheck("smart_trader", check_interval=60.0)

            # Add health checks
            def check_state_file():
                try:
                    from utils.health_check import check_file_exists

                    return check_file_exists(str(state_file), max_age=3600)
                except:
                    return True  # Skip if function not available

            health_check.add_check(check_state_file, "state_file")

            def check_broker_health():
                try:
                    equity = broker.equity
                    return {
                        "status": "healthy" if equity > 0 else "unhealthy",
                        "message": f"Broker equity: ${equity:,.2f}",
                    }
                except:
                    return {"status": "unhealthy", "message": "Broker check failed"}

            health_check.add_check(check_broker_health, "broker")

            health_check.start_monitoring()
            logger.info("🏥 Health check monitoring started")
        except Exception as e:
            logger.warning(f"⚠️ Health check initialization failed: {e}")

    # --- Step 7: Core startup banner ---
    print(f"🟣 SmartTrader starting ({trading_mode})", flush=True)
    logger.info(f"🟣 SmartTrader starting ({trading_mode})")
    logger.info("📊 System check: Guardian + CircuitBreaker active.")
    logger.info("🔁 Pre-loading market data...")

    # Load target allocations early so we can report symbol coverage and initialize portfolio core
    try:
        allocations = load_allocations()
        if not allocations or not isinstance(allocations, dict):
            raise ValueError("load_allocations returned invalid data")
    except Exception as e:
        logger.error(f"❌ Failed to load allocations: {e}, using defaults")
        allocations = {
            "BTC-USD": 0.12,
            "ETH-USD": 0.10,
            "SOL-USD": 0.06,
            "SPY": 0.08,
            "QQQ": 0.08,
            "AAPL": 0.06,
            "MSFT": 0.06,
            "NVDA": 0.06,
        }
    SYMBOLS = list(allocations.keys())

    # Enhanced startup message with symbol count
    symbol_count = len(SYMBOLS)
    send_telegram(
        f"SmartTrader active with {symbol_count} symbols.\n"
        f"📊 Guardian + CircuitBreaker: Active\n"
        f"🔁 Pre-loading market data...",
        include_mode=True,
        mode=trading_mode,
        state=state,
    )

    # Broker already initialized in Step 5 for health checks

    # Phase 2900-3100: Initialize Live Execution Engine if in LIVE_MODE
    live_engine = None
    if trading_mode == "LIVE_MODE" and HAS_LIVE_EXECUTION:
        try:
            use_paper = os.getenv("ALPACA_USE_PAPER", "true").lower() == "true"
            live_engine = LiveExecutionEngine(use_paper=use_paper)
            logger.info(
                f"✅ Live Execution Engine initialized ({'PAPER' if use_paper else 'LIVE'})"
            )
            send_telegram(
                f"🚀 LIVE MODE ACTIVATED\n"
                f"Execution Engine: {'PAPER' if use_paper else 'LIVE'}\n"
                f"⚠️ Real money trading enabled",
                include_mode=True,
                mode=trading_mode,
                state=state,
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize Live Execution Engine: {e}")
            send_telegram(
                f"❌ LIVE MODE ERROR\n"
                f"Failed to initialize execution engine: {e}\n"
                f"Falling back to paper trading",
                include_mode=True,
                mode="PAPER_TRADING_MODE",
                state=state,
            )
            trading_mode = "PAPER_TRADING_MODE"  # Fallback to paper mode

    # === ENTERPRISE PORTFOLIO CORE INITIALIZATION (Phases 2500-3500) ===
    portfolio_optimizer = None
    risk_manager = None
    strategy_manager = None
    strategy_executor = None
    signal_generator_cache = {}  # Cache per symbol
    portfolio_optimization_cycle = int(
        os.getenv("PORTFOLIO_OPT_CYCLE", "100")
    )  # Rebalance every N cycles
    risk_assessment_cycle = int(
        os.getenv("RISK_ASSESSMENT_CYCLE", "200")
    )  # Risk check every N cycles
    risk_assessment_cooldown_seconds = int(os.getenv("RISK_ASSESSMENT_COOLDOWN", "900"))
    last_optimization_cycle = 0
    last_risk_assessment_cycle = 0
    last_risk_notification_time = 0.0
    last_risk_snapshot = ""

    # Initialize Portfolio Core modules with graceful degradation
    try:
        import pandas as pd  # type: ignore

        # Load real price history if available, otherwise use sample data
        if HAS_YFINANCE and len(SYMBOLS) > 0:
            try:
                # Try to load real price history for optimization
                from analytics.portfolio_optimizer import load_price_history

                price_df = load_price_history(SYMBOLS[:5], days=30)  # Last 30 days for optimization

                if price_df is not None and not price_df.empty:
                    from analytics.portfolio_optimizer import PortfolioOptimizer

                    portfolio_optimizer = PortfolioOptimizer(price_df, risk_free_rate=0.02)
                    logger.info(
                        f"✅ Portfolio Optimizer initialized with real data ({price_df.shape})"
                    )
                else:
                    logger.warning(
                        "⚠️ Could not load price history, using sample data for optimizer"
                    )
                    price_df = None
            except Exception as e:
                logger.warning(f"⚠️ Price history loading failed: {e}")
                price_df = None
        else:
            price_df = None

        # Fallback to sample data if real data unavailable
        if portfolio_optimizer is None:
            sample_data = {
                "BTC-USD": [0.01, -0.02, 0.015, 0.03, 0.01, -0.01, 0.02],
                "ETH-USD": [0.02, -0.01, 0.012, 0.025, 0.015, -0.005, 0.018],
                "SPY": [0.003, -0.002, 0.004, 0.006, 0.002, -0.001, 0.003],
            }
            sample_df = pd.DataFrame(sample_data)
            from analytics.portfolio_optimizer import PortfolioOptimizer

            portfolio_optimizer = PortfolioOptimizer(sample_df, risk_free_rate=0.02)
            logger.info("✅ Portfolio Optimizer initialized with sample data")

        # Initialize Risk Manager with recent returns
        if price_df is not None and len(price_df) > 0:
            # Use actual returns from price data
            returns_series = price_df.pct_change().dropna().stack()
            if len(returns_series) > 0:
                from ai.risk_enhancements import AdvancedRiskManager

                risk_manager = AdvancedRiskManager(returns_series.values)
                logger.info(
                    f"✅ Risk Manager initialized with {len(returns_series)} return observations"
                )
        else:
            # Fallback sample returns
            sample_returns = [0.01, -0.02, 0.015, 0.03, -0.01, 0.02, -0.005, 0.015]
            from ai.risk_enhancements import AdvancedRiskManager

            risk_manager = AdvancedRiskManager(np.array(sample_returns))

        # === MULTI-STRATEGY FRAMEWORK (Phase 3500-3700) ===
        if HAS_STRATEGY_MANAGER:
            try:
                from agents.strategy_manager import StrategyManager
                from trader.strategy_executor import StrategyExecutor

                strategy_manager = StrategyManager()
                strategy_executor = StrategyExecutor()
                logger.info("✅ Strategy Manager and Executor initialized")
            except Exception as e:
                logger.warning(f"⚠️ Strategy Manager initialization failed: {e}")
                strategy_manager = None
                strategy_executor = None
            logger.info("✅ Risk Manager initialized with sample data")

        logger.info("✅ Portfolio Core modules initialized successfully")

    except Exception as e:
        logger.error(f"❌ Portfolio Core initialization failed: {e}")
        traceback.print_exc()
        logger.warning(
            "⚠️ Continuing without Portfolio Core features (optimization, risk management)"
        )

    # LIVE_MODE safety confirmation check
    confirm_live_ready = False
    if trading_mode == "LIVE_MODE":
        # Check for explicit confirmation flag
        confirm_file = ROOT / "state" / "live_mode_confirmed.json"
        if confirm_file.exists():
            try:
                confirm_data = json.loads(confirm_file.read_text())
                confirm_live_ready = confirm_data.get("confirmed", False)
            except:
                pass

        if not confirm_live_ready:
            logger.warning("⚠️ LIVE_MODE enabled but not confirmed. Safety check active.")
            send_telegram(
                "⚠️ LIVE_MODE Safety Check\n"
                "LIVE_MODE is enabled but not confirmed.\n"
                'Create state/live_mode_confirmed.json with {"confirmed": true} to proceed.',
                include_mode=True,
                mode=trading_mode,
                state=state,
            )

    # Initialize price history
    for sym in SYMBOLS:
        state["price_history"][sym] = deque(maxlen=200)
        state["last_trade"][sym] = 0

    # PRE-LOAD price history to speed up trading start
    print("📊 Pre-loading price history for faster trading start...", flush=True)
    if HAS_YFINANCE:
        for sym in SYMBOLS:
            try:
                ticker = yf.Ticker(sym)
                # Try to get historical data with more granular intervals
                # Try 1h, 5m, 1d intervals to get 20+ points
                prices_to_add = []
                for period, interval in [("5d", "1h"), ("1d", "5m"), ("1mo", "1d"), ("3mo", "1d")]:
                    try:
                        hist_data = ticker.history(period=period, interval=interval)
                        if not hist_data.empty:
                            # Get last 25 prices (we need 20, get extra for buffer)
                            prices_to_add = hist_data["Close"].tail(25).tolist()
                            if len(prices_to_add) >= 15:  # Have enough data
                                break
                    except:
                        continue

                if prices_to_add:
                    # Add prices to history
                    for price in prices_to_add:
                        state["price_history"][sym].append(float(price))
                    print(f"  ✅ {sym}: Pre-loaded {len(prices_to_add)} price points", flush=True)
                else:
                    print(
                        f"  ⚠️ {sym}: Could not pre-load history (will collect gradually)",
                        flush=True,
                    )
            except Exception as e:
                print(f"  ⚠️ {sym}: Could not pre-load history: {e}", flush=True)

    print(f"📊 Trading symbols: {SYMBOLS}", flush=True)
    print(f"💰 Starting capital: ${broker.equity:,.2f}", flush=True)

    loop_count = 0
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 10

    # Initialize circuit breakers for critical operations
    # HALF_OPEN recovery: require 3 successes to close, allow 3 failures before re-opening
    # Reduced failure threshold to open faster and prevent accumulating too many failures
    quote_breaker = CircuitBreaker(
        failure_threshold=5,  # Reduced from 10 to open faster
        recovery_timeout=300,
        name="QuoteFetcher",
        half_open_success_threshold=3,  # Need 3 successes to close
        half_open_failure_threshold=3,  # Allow 3 failures before re-opening
    )
    trade_breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=600,
        name="TradeExecution",
        half_open_success_threshold=2,
        half_open_failure_threshold=2,
    )

    # Track decision indices for P&L attribution
    pending_decisions: dict[str, int] = {}  # {symbol: decision_idx}
    trade_contexts: dict[str, dict[str, Any]] = {}  # {symbol: signal metadata}

    # Track circuit breaker state changes for Telegram alerts
    last_circuit_states = {"quote": "CLOSED", "trade": "CLOSED"}

    # --- Main trading loop with state persistence ---
    # FIX: Clean corrupted timestamps before starting loop
    print("🔧 Cleaning corrupted timestamps...", flush=True)
    now_ts = time.time()
    cleaned_count = 0
    for sym, ts in list(state.get("last_trade", {}).items()):
        if isinstance(ts, (int, float)):
            # If timestamp is more than 7 days old or in the future, reset it
            if ts > now_ts or ts < (now_ts - 604800):  # 7 days
                state["last_trade"][sym] = 0
                cleaned_count += 1
    if cleaned_count > 0:
        logger.info(f"🔧 Cleaned {cleaned_count} corrupted timestamps")
        print(f"🔧 Cleaned {cleaned_count} corrupted timestamps", flush=True)

    print("🔄 Entering main trading loop...", flush=True)
    logger.info("🔄 Entering main trading loop")

    try:
        while not stop_flag["stop"]:
            try:
                now = dt.datetime.now()
                loop_count += 1
                consecutive_errors = 0  # Reset on successful iteration

                # Log loop entry every 100 iterations for visibility
                if loop_count == 1 or loop_count % 100 == 0:
                    print(f"🔄 Loop iteration {loop_count} started", flush=True)
                    logger.info(f"🔄 Loop iteration {loop_count}")

                # Daily reset
                if "date" not in state.get("daily", {}) or "start_equity" not in state.get(
                    "daily", {}
                ):
                    state["daily"] = {
                        "date": now.date().isoformat(),
                        "pnl_pct": 0.0,
                        "start_equity": broker.equity,
                    }
                    print(f"🔁 New trading day: {state['daily']['date']}", flush=True)
                    send_telegram(
                        f"🔁 New Trading Day: {state['daily']['date']}\n"
                        f"💰 Starting Equity: ${broker.equity:,.2f}",
                        include_mode=True,
                        state=state,
                    )

                if state["daily"]["date"] != now.date().isoformat():
                    # Calculate daily P&L (ensure start_equity exists)
                    start_equity = state["daily"].get("start_equity", broker.equity)
                    daily_pnl = (broker.equity - start_equity) / max(1.0, start_equity) * 100
                    print(
                        f"📊 Daily P&L: {daily_pnl:.2f}% | Equity: ${broker.equity:,.2f}",
                        flush=True,
                    )
                    send_telegram(
                        f"📊 Daily P&L: {daily_pnl:.2f}% | Equity: ${broker.equity:,.2f}",
                        include_mode=True,
                        state=state,
                    )

                    # Reset for new day
                    state["daily"] = {
                        "date": now.date().isoformat(),
                        "pnl_pct": 0.0,
                        "start_equity": broker.equity,
                    }

                # Load brain state
                brain = load_brain()
                risk_scaler = brain.get("risk_scaler", 1.0)
                confidence = brain.get("confidence", 0.5)

                # Update portfolio value
                broker.fetch_portfolio_value()

                # GUARDIAN AUTOPAUSE: Check if Guardian wants to pause trading
                is_paused, guardian_drawdown, pause_reason = check_guardian_pause(broker, state)
                if is_paused:
                    print(
                        f"⏸️ Trading paused by Guardian - {pause_reason} | Waiting 60s before retry...",
                        flush=True,
                    )
                    # Send pause telemetry
                    send_to_atlas_bridge(
                        {
                            "type": "guardian_pause",
                            "is_paused": True,
                            "current_drawdown": guardian_drawdown,
                            "reason": pause_reason,
                            "mode": trading_mode,
                            "timestamp": dt.datetime.now(dt.UTC).isoformat(),
                        }
                    )
                    time.sleep(60)
                    continue

                # Market hours check (9:30 AM - 4:00 PM ET, Mon-Fri)
                # Crypto trades 24/7, stocks/commodities only during market hours
                is_market_hours = False
                now_et = dt.datetime.now(
                    dt.timezone(dt.timedelta(hours=-5))
                )  # EST (adjust for DST if needed)
                if now_et.weekday() < 5:  # Monday = 0, Friday = 4
                    market_open = dt.time(9, 30)  # 9:30 AM
                    market_close = dt.time(16, 0)  # 4:00 PM
                    current_time = now_et.time()
                    is_market_hours = market_open <= current_time <= market_close

                # Separate crypto (24/7) from stocks/commodities (market hours only)
                crypto_symbols = [
                    s for s in SYMBOLS if "-USD" in s or s in ["BTC-USD", "ETH-USD", "SOL-USD"]
                ]
                stock_commodity_symbols = [s for s in SYMBOLS if s not in crypto_symbols]

                # Trade crypto 24/7
                symbols_to_trade = crypto_symbols.copy()

                # Trade stocks/commodities only during market hours
                if is_market_hours:
                    symbols_to_trade.extend(stock_commodity_symbols)
                    if loop_count % 100 == 0:  # Log every ~8 minutes
                        print("📈 Market OPEN - Trading stocks/commodities", flush=True)
                else:
                    if loop_count % 100 == 0:  # Log every ~8 minutes
                        print("🌙 Market CLOSED - Trading crypto only", flush=True)

                # Log loop activity every 20 iterations (~100 seconds) for visibility
                if loop_count % 20 == 0:
                    crypto_count = len([s for s in symbols_to_trade if "-USD" in s])
                    print(
                        f"🔄 Loop {loop_count} | Trading {len(symbols_to_trade)} symbols ({crypto_count} crypto)",
                        flush=True,
                    )

                # === ENTERPRISE PORTFOLIO OPTIMIZATION HOOK (Phase 2500-2700) ===
                if (
                    portfolio_optimizer
                    and (loop_count - last_optimization_cycle) >= portfolio_optimization_cycle
                ):
                    try:
                        # Load fresh price history for optimization
                        if HAS_YFINANCE and len(SYMBOLS) > 0:
                            from analytics.portfolio_optimizer import load_price_history

                            opt_df = load_price_history(SYMBOLS[:5], days=30)

                            if opt_df is not None and not opt_df.empty:
                                # Update optimizer with fresh data
                                portfolio_optimizer.returns_df = opt_df
                                portfolio_optimizer.cov_matrix = (
                                    portfolio_optimizer.calculate_covariance_matrix()
                                )
                                portfolio_optimizer.mean_returns = (
                                    opt_df.pct_change().dropna().mean() * 252
                                )

                                # Optimize portfolio
                                weights = portfolio_optimizer.optimize_efficient_frontier()
                                if weights:
                                    portfolio_optimizer.save_allocations_to_state(
                                        weights, method="sharpe"
                                    )

                                    # CRITICAL: Ensure crypto symbols are included in allocations
                                    # Merge optimized weights with crypto defaults to ensure crypto trading
                                    crypto_defaults = {
                                        "BTC-USD": 0.12,
                                        "ETH-USD": 0.10,
                                        "SOL-USD": 0.06,
                                    }

                                    # Add crypto if not in optimized weights or if allocation is too low
                                    for crypto_sym, default_alloc in crypto_defaults.items():
                                        if (
                                            crypto_sym not in weights
                                            or weights.get(crypto_sym, 0) < 0.05
                                        ):
                                            weights[crypto_sym] = default_alloc

                                    # Renormalize to sum to 1.0
                                    total = sum(weights.values())
                                    if total > 0:
                                        weights = {k: v / total for k, v in weights.items()}

                                    # Format weights for Telegram
                                    weights_str = " | ".join(
                                        [f"{k}: {v:.1%}" for k, v in list(weights.items())[:5]]
                                    )
                                    sharpe = portfolio_optimizer.get_portfolio_metrics(weights).get(
                                        "expected_sharpe", 0
                                    )

                                    send_telegram(
                                        f"💼 Portfolio Rebalanced\n"
                                        f"{weights_str}\n"
                                        f"Target Sharpe: {sharpe:.2f}",
                                        include_mode=True,
                                        mode=trading_mode,
                                        state=state,
                                    )
                                    logger.info(
                                        f"💼 Portfolio rebalanced: {weights_str} | Sharpe: {sharpe:.2f}"
                                    )

                                    # Update allocations for SmartTrader
                                    allocations.update(weights)

                                    last_optimization_cycle = loop_count
                    except Exception as e:
                        logger.error(f"❌ Portfolio optimization error: {e}")
                        traceback.print_exc()

                # === ENTERPRISE RISK MANAGEMENT HOOK (Phase 2700-2900) ===
                if (
                    risk_manager
                    and (loop_count - last_risk_assessment_cycle) >= risk_assessment_cycle
                ):
                    try:
                        # Calculate risk metrics
                        cvar_95 = risk_manager.calculate_cvar(0.95)
                        cvar_99 = risk_manager.calculate_cvar(0.99)
                        stress_result = risk_manager.stress_test(-0.10)
                        stress_status = stress_result.get("status", "UNKNOWN")

                        # Use observed spreads for liquidity risk; fallback to baseline values
                        sample_spreads = (
                            list(RECENT_SPREADS) if RECENT_SPREADS else [0.002, 0.003, 0.0015]
                        )
                        liquidity = risk_manager.liquidity_risk(sample_spreads)
                        liquidity_status = liquidity.get("status", "UNKNOWN")

                        snapshot_signature = (
                            f"{cvar_95:.6f}|{cvar_99:.6f}|{stress_status}|{liquidity_status}"
                        )
                        now_ts = time.time()
                        should_notify = (
                            (now_ts - last_risk_notification_time)
                            >= risk_assessment_cooldown_seconds
                            or snapshot_signature != last_risk_snapshot
                        )

                        metrics_valid = all(math.isfinite(value) for value in (cvar_95, cvar_99))

                        if should_notify and metrics_valid:
                            send_telegram(
                                f"⚠️ Risk Assessment Update\n"
                                f"CVaR 95%: {cvar_95 * 100:.2f}%\n"
                                f"CVaR 99%: {cvar_99 * 100:.2f}%\n"
                                f"Stress (-10%): {stress_status}\n"
                                f"Liquidity: {liquidity_status}",
                                include_mode=True,
                                mode=trading_mode,
                                state=state,
                            )
                            logger.info(
                                "⚠️ Risk Assessment: CVaR99=%.2f%% | Stress=%s | Liquidity=%s",
                                cvar_99 * 100,
                                stress_status,
                                liquidity_status,
                            )
                            last_risk_notification_time = now_ts
                            last_risk_snapshot = snapshot_signature
                        else:
                            logger.debug(
                                "⏱️ Risk snapshot unchanged or metrics invalid (cooldown %ss); notification suppressed.",
                                risk_assessment_cooldown_seconds,
                            )

                        last_risk_assessment_cycle = loop_count
                    except Exception as e:
                        logger.error(f"❌ Risk assessment error: {e}")
                        traceback.print_exc()

                # === LIVE_MODE Safety Guard ===
                if trading_mode == "LIVE_MODE" and not confirm_live_ready:
                    if loop_count % 100 == 0:  # Log every ~8 minutes
                        logger.warning(
                            "⚠️ LIVE_MODE enabled but not confirmed. Awaiting safety check."
                        )
                    time.sleep(5)
                    continue

                # Prioritize: Top stocks first, then commodities, then crypto
                symbol_priority = sorted(
                    symbols_to_trade,
                    key=lambda x: (
                        x not in ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"],  # Top stocks first
                        x not in ["GLD", "SLV", "USO"],  # Commodities second
                        x,  # Then crypto
                    ),
                )

                for sym in symbol_priority:
                    # Circuit breaker check for quote fetching
                    if not quote_breaker.can_proceed():
                        continue

                    # ============================================================================
                    # DIAGNOSTIC LOGGING: Periodic circuit breaker status (every 50 iterations)
                    # ============================================================================
                    if loop_count % 50 == 0:  # Every 50 iterations (~5 minutes)
                        trade_state = trade_breaker.get_state_info()
                        quote_state = quote_breaker.get_state_info()
                        logger.info(
                            f"🔌 CIRCUIT BREAKER STATUS: "
                            f"Trade={trade_state['state']} (failures={trade_breaker.failure_count}/{trade_breaker.failure_threshold}) | "
                            f"Quote={quote_state['state']} (failures={quote_breaker.failure_count}/{quote_breaker.failure_threshold})"
                        )

                    throttle_until = QUOTE_BACKOFF.get(sym)
                    if throttle_until and time.time() < throttle_until:
                        if loop_count % 50 == 0:
                            remaining = max(0, int(throttle_until - time.time()))
                            logger.debug(f"⏳ Backing off {sym} quote fetch for {remaining}s")
                        continue

                    # Try QuoteService first (world-class immutable quotes with multi-source fallback)
                    quote = None
                    if quote_service:
                        try:
                            validated_quote = quote_service.get_quote(sym, max_age=60)
                            if validated_quote:
                                # Convert ValidatedQuote to dict format for compatibility
                                quote = validated_quote.to_dict()
                                logger.debug(
                                    f"📊 {sym} Quote ({validated_quote.source}): {validated_quote.last_price:.2f}"
                                )
                                quote_breaker.record_success()
                                reset_quote_backoff(sym)
                            else:
                                quote_breaker.record_failure()
                                if sym not in ["BTC-USD", "ETH-USD", "USDT/USD"]:
                                    logger.debug(f"⚠️ QuoteService failed to fetch quote for {sym}")
                                schedule_quote_backoff(sym)
                                continue
                        except Exception as e:
                            logger.warning(f"⚠️ QuoteService error for {sym}: {e}")
                            quote_breaker.record_failure()
                            schedule_quote_backoff(sym)
                            continue

                    # Fallback to legacy broker.fetch_quote() if QuoteService unavailable or failed
                    if not quote:
                        quote = broker.fetch_quote(sym)
                    if not quote:
                        quote_breaker.record_failure()
                        schedule_quote_backoff(sym)
                        # Log failures for debugging
                        if sym not in ["BTC-USD", "ETH-USD", "USDT/USD"]:
                            print(
                                f"⚠️  Failed to fetch quote for {sym} - may need different data source",
                                flush=True,
                            )
                        continue
                    quote_breaker.record_success()  # Successful quote fetch
                    reset_quote_backoff(sym)

                    # --- World-Class Safe Price Validation & Conversion ---
                    price_raw = (
                        quote.get("mid")
                        or quote.get("last")
                        or quote.get("regularMarketPrice")
                        or quote.get("currentPrice")
                    )

                    # Use safe conversion function
                    safe_price = safe_float_convert(
                        price_raw, symbol=sym, context="main loop quote price", state=state
                    )
                    if safe_price is None:
                        logger.warning(f"⚠️ Quote for {sym} missing or invalid price: {quote}")
                        continue

                    # CRITICAL: Use safe_price everywhere, never the raw price
                    price = safe_price

                    # Track liquidity spreads when bid/ask available
                    bid_candidates = [
                        quote.get("bid"),
                        quote.get("bidPrice"),
                        quote.get("bestBid"),
                        quote.get("b"),
                    ]
                    ask_candidates = [
                        quote.get("ask"),
                        quote.get("askPrice"),
                        quote.get("bestAsk"),
                        quote.get("a"),
                    ]

                    bid_value = None
                    for value in bid_candidates:
                        if value is None:
                            continue
                        converted = safe_float_convert(value, symbol=sym, context="bid")
                        if converted is not None:
                            bid_value = converted
                            break

                    ask_value = None
                    for value in ask_candidates:
                        if value is None:
                            continue
                        converted = safe_float_convert(value, symbol=sym, context="ask")
                        if converted is not None:
                            ask_value = converted
                            break
                    if bid_value and ask_value and ask_value > bid_value:
                        spread_bps = calculate_spread(bid_value, ask_value)
                        if spread_bps is not None and math.isfinite(spread_bps):
                            RECENT_SPREADS.append(spread_bps / 10000.0)

                    state["price_history"][sym].append(price)

                    # Log progress collecting data
                    data_count = len(state["price_history"][sym])
                    # Log data collection progress more frequently
                    if loop_count % 20 == 0:  # Log every ~100 seconds
                        print(
                            f"📊 {sym}: {data_count} price points | Current: ${price:.2f}",
                            flush=True,
                        )

                    # Check if enough data (reduced from 50 to 20 for faster start)
                    if data_count < 20:
                        if loop_count % 20 == 0:
                            print(
                                f"⏳ {sym}: Waiting for more data ({data_count}/20 points)",
                                flush=True,
                            )
                        continue

                    # Cooldown: don't trade too frequently
                    # CRYPTO: Reduced cooldown for 24/7 trading (5 min for crypto, 15 min for stocks)
                    is_crypto = "-USD" in sym
                    cooldown_seconds = 300 if is_crypto else 900  # 5 min crypto, 15 min stocks
                    last_trade_ts = state["last_trade"].get(sym, 0)
                    # FIX: Handle corrupted timestamps (very old values)
                    # If timestamp is more than 1 day old, treat as no cooldown
                    time_since_last = time.time() - last_trade_ts
                    if (
                        last_trade_ts > 0 and time_since_last < 86400
                    ):  # Only check cooldown if timestamp is recent (< 1 day)
                        if time_since_last < cooldown_seconds:
                            if loop_count % 20 == 0:  # Log occasionally
                                remaining = int(cooldown_seconds - time_since_last)
                                if remaining > 0:
                                    print(f"⏳ {sym}: Cooldown {remaining}s remaining", flush=True)
                            # ============================================================================
                            # DIAGNOSTIC LOGGING: Cooldown check
                            # ============================================================================
                            logger.warning(
                                f"❌ BLOCKED [{sym}]: Cooldown active "
                                f"({time_since_last:.0f}s < {cooldown_seconds}s) | "
                                f"{int(cooldown_seconds - time_since_last)}s remaining"
                            )
                            continue
                        else:
                            logger.info(
                                f"✅ DIAGNOSTIC [{sym}]: Cooldown OK "
                                f"(last trade {time_since_last:.0f}s ago, required {cooldown_seconds}s)"
                            )
                    elif last_trade_ts > 0:
                        # Corrupted timestamp - reset it
                        logger.warning(f"⚠️ Corrupted timestamp for {sym}, resetting cooldown")
                        state["last_trade"][sym] = 0
                    else:
                        # No previous trade - cooldown OK
                        logger.info(f"✅ DIAGNOSTIC [{sym}]: Cooldown OK (no previous trades)")

                    # Calculate indicators for detailed logging (always calculate momentum)
                    price_list = list(state["price_history"][sym])
                    rsi_val = (
                        rsi(price_list, min(14, len(price_list) - 1))
                        if len(price_list) >= 15
                        else None
                    )
                    sma_20 = (
                        sma(price_list, min(20, len(price_list))) if len(price_list) >= 10 else None
                    )
                    momentum = calculate_momentum(
                        price_list, window=5
                    )  # Use proper momentum function

                    # ENHANCED SELL LOGIC: RSI > 80 and position > 0 triggers sell (even without strategy vote)
                    pos = broker.get_position(sym)
                    has_position = pos["qty"] > 1e-6

                    # === ENTERPRISE ENHANCED SIGNAL GENERATION (Phase 3100-3300) ===
                    # Try enhanced signal generator first, fallback to standard
                    enhanced_signal = None
                    if HAS_NUMPY and len(state["price_history"][sym]) >= 20:
                        try:
                            # Cache signal generator per symbol
                            if sym not in signal_generator_cache:
                                price_df_signal = pd.DataFrame(
                                    {"Close": list(state["price_history"][sym])}
                                )
                                from agents.enhanced_signals import EnhancedSignalGenerator

                                signal_generator_cache[sym] = EnhancedSignalGenerator(
                                    price_df_signal
                                )

                            signal_result = signal_generator_cache[sym].generate_signal(price)
                            enhanced_signal = signal_result.get("signal")
                            enhanced_confidence = signal_result.get("confidence", confidence)

                            # Use enhanced confidence if available
                            if enhanced_confidence > confidence:
                                confidence = enhanced_confidence

                            logger.debug(
                                f"📊 Enhanced signal for {sym}: {enhanced_signal} (confidence: {enhanced_confidence:.2f})"
                            )
                        except Exception as e:
                            logger.debug(f"⚠️ Enhanced signal generation failed for {sym}: {e}")

                    # Generate standard signal (fallback or combined)
                    signal, signal_meta = generate_signal(
                        broker, sym, state["price_history"][sym], risk_scaler, confidence
                    )
                    if signal_meta is None:
                        signal_meta = {}

                    # CRYPTO: Force BUY if RSI < 75 and no position (FINAL - override everything)
                    # Made more aggressive to match signal generation logic
                    is_crypto = "-USD" in sym
                    if is_crypto and rsi_val is not None and rsi_val < 75 and not has_position:
                        signal = "buy"  # Force BUY for crypto when RSI < 75 - FINAL OVERRIDE
                        logger.info(
                            f"🪙 CRYPTO: Forcing BUY signal for {sym} (RSI={rsi_val:.1f} < 75) - OVERRIDING enhanced signal"
                        )

                    # Prefer enhanced signal if available and confident (but NEVER override crypto RSI BUY)
                    # CRITICAL FIX: Don't use SELL signals when we have no position
                    if enhanced_signal and enhanced_confidence > 0.6:
                        # NEVER override crypto RSI BUY signals
                        # NEVER use SELL signal when we have no position
                        if not (
                            is_crypto and rsi_val is not None and rsi_val < 75 and not has_position
                        ):
                            # Only use enhanced signal if it makes sense:
                            # - BUY signal is always fine
                            # - SELL signal only if we have a position
                            if enhanced_signal.lower() == "buy" or (
                                enhanced_signal.lower() == "sell" and has_position
                            ):
                                signal = enhanced_signal
                            else:
                                # Enhanced signal is SELL but no position - ignore it, use standard signal
                                logger.debug(
                                    f"⚠️ [{sym}]: Ignoring enhanced SELL signal (no position), using standard signal"
                                )

                    # Override signal if RSI > 80 and we have a position (overbought sell)
                    if rsi_val is not None and rsi_val > 80 and has_position and signal != "sell":
                        signal = "sell"

                    # DEBUG: Log detailed signal info with RSI, SMA, momentum (always log momentum)
                    # More frequent logging for crypto symbols to debug trading issues
                    is_crypto = "-USD" in sym
                    log_frequency = (
                        5 if is_crypto else 20
                    )  # Log crypto every 25 seconds, others every 100 seconds
                    if (
                        loop_count % log_frequency == 0 or signal
                    ):  # Always log when signal is generated
                        data_count = len(state["price_history"][sym])
                        rsi_str = f"{rsi_val:.1f}" if rsi_val else "N/A"
                        sma_str = f"${sma_20:.2f}" if sma_20 else "N/A"
                        momentum_str = f"{momentum:.3f}%" if momentum is not None else "N/A"
                        mode_str = f"[{trading_mode}]" if trading_mode == "TEST_MODE" else ""
                        signal_str = f"→ {signal.upper()}" if signal else "→ None"
                        print(
                            f"🔍 {sym}: RSI={rsi_str} SMA={sma_str} Momentum={momentum_str} {signal_str}, position={pos['qty']:.4f}, confidence={confidence:.2f} {mode_str}",
                            flush=True,
                        )
                        if signal:
                            logger.info(
                                f"📊 Signal generated for {sym}: {signal.upper()} (RSI={rsi_val:.1f}, confidence={confidence:.2f})"
                            )

                    if not signal:
                        continue

                    # ============================================================================
                    # DIAGNOSTIC LOGGING: Signal generated, starting execution checks
                    # ============================================================================
                    logger.info(
                        f"🔍 DIAGNOSTIC [{sym}]: Signal={signal.upper()}, Starting execution checks..."
                    )

                    # Circuit breaker check for trading
                    if not trade_breaker.can_proceed():
                        state_info = trade_breaker.get_state_info()
                        logger.warning(
                            f"❌ BLOCKED [{sym}]: Circuit breaker {state_info['state']} | "
                            f"failures={trade_breaker.failure_count}/{trade_breaker.failure_threshold} | "
                            f"last_failure={time.time() - trade_breaker.last_failure_time:.0f}s ago"
                            if trade_breaker.last_failure_time
                            else "last_failure=never"
                        )
                        print(
                            f"⏸️ Circuit breaker {state_info['state']} - skipping trade for {sym}",
                            flush=True,
                        )
                        continue
                    else:
                        logger.info(f"✅ DIAGNOSTIC [{sym}]: Circuit breaker OK (CLOSED)")

                    # Track decision for performance attribution
                    reasoning = f"Signal generated: {signal} (RSI={rsi_val:.1f}, Momentum={momentum:.3f}%, Confidence={confidence:.2f})"
                    decision_idx = track_trade_decision(
                        sym, signal, reasoning, rsi_val, momentum, confidence
                    )
                    if decision_idx is not None:
                        pending_decisions[sym] = decision_idx
                    if signal_meta:
                        trade_contexts[sym] = signal_meta

                    # ============================================================================
                    # DIAGNOSTIC LOGGING: Position size calculation with detailed logging
                    # ============================================================================
                    target_allocation = allocations.get(sym, 0.0) * risk_scaler
                    portfolio_value = broker.fetch_portfolio_value()
                    target_value = portfolio_value * target_allocation

                    # Log allocation details
                    logger.info(
                        f"💰 DIAGNOSTIC [{sym}]: "
                        f"portfolio=${portfolio_value:,.2f} | "
                        f"base_allocation={allocations.get(sym, 0.0):.4f} | "
                        f"risk_scaler={risk_scaler:.4f} | "
                        f"final_allocation={target_allocation:.4f} | "
                        f"target_value=${target_value:,.2f}"
                    )

                    # Get current position
                    pos = broker.get_position(sym)
                    current_qty = pos.get("qty", 0.0)
                    current_value = current_qty * price

                    logger.info(
                        f"📊 DIAGNOSTIC [{sym}]: "
                        f"current_qty={current_qty:.4f} | "
                        f"price=${price:,.2f} | "
                        f"current_value=${current_value:,.2f}"
                    )

                    if signal == "buy":
                        # Check if we need to buy more
                        # CRYPTO: More aggressive threshold (5% for crypto, 10% for stocks)
                        # Made more aggressive: allow buying even if at 98% of target (was 95%/90%)
                        is_crypto = "-USD" in sym
                        threshold = (
                            0.98 if is_crypto else 0.95
                        )  # 2% crypto, 5% stocks - more aggressive

                        # FIX: If target_allocation is 0 or very small, use minimum trade size instead
                        # This ensures we can still trade even if allocation is missing
                        if target_allocation < 0.01:  # Less than 1% allocation
                            # Use minimum position size: 1% of portfolio for crypto, 0.5% for stocks
                            min_allocation = 0.01 if is_crypto else 0.005
                            original_target = target_value
                            target_value = portfolio_value * min_allocation
                            logger.warning(
                                f"⚠️ DIAGNOSTIC [{sym}]: "
                                f"Low allocation ({target_allocation:.4f}), "
                                f"using minimum ({min_allocation:.4f}) | "
                                f"target changed: ${original_target:,.2f} → ${target_value:,.2f}"
                            )

                        # ============================================================================
                        # DIAGNOSTIC LOGGING: Buy condition check
                        # ============================================================================
                        should_buy = current_value < target_value * threshold
                        logger.info(
                            f"🔍 DIAGNOSTIC [{sym}]: BUY CONDITION CHECK | "
                            f"current=${current_value:,.2f} < "
                            f"target*threshold=${target_value * threshold:,.2f} | "
                            f"RESULT={should_buy}"
                        )

                        if not should_buy:
                            logger.warning(
                                f"❌ BLOCKED [{sym}]: Buy condition failed | "
                                f"Already at target (${current_value:,.2f} >= ${target_value * threshold:,.2f})"
                            )
                            continue

                        # If we reach here, buy should execute
                        logger.info(
                            f"🚀 DIAGNOSTIC [{sym}]: Buy conditions MET, proceeding to order submission..."
                        )

                        if current_value < target_value * threshold:
                            # Calculate initial buy value
                            buy_value = min(target_value - current_value, broker.cash * 0.95)

                            # ============================================================================
                            # AI RISK ASSESSMENT (World-Class Integration)
                            # ============================================================================
                            # Perform AI risk assessment for large positions (>10% portfolio or >$10k)
                            proposed_position_value = current_value + buy_value
                            is_large_position = (
                                proposed_position_value > portfolio_value * 0.1  # >10% portfolio
                                or proposed_position_value > 10000  # >$10k
                            )

                            if is_large_position:
                                try:
                                    from utils.agent_ai_client import assess_risk

                                    # Prepare market conditions for AI
                                    market_conditions = {
                                        "volatility": abs(momentum)
                                        if momentum is not None
                                        else 0.0,
                                        "trend": "UP"
                                        if momentum and momentum > 0
                                        else "DOWN"
                                        if momentum and momentum < 0
                                        else "NEUTRAL",
                                        "rsi": rsi_val,
                                        "market_sentiment": signal_meta.get("market_sentiment", 0.0)
                                        if signal_meta
                                        else 0.0,
                                        "confidence": confidence,
                                    }

                                    logger.info(
                                        f"🛡️ AI RISK ASSESSMENT [{sym}]: "
                                        f"Large position detected (${proposed_position_value:,.2f} = "
                                        f"{(proposed_position_value/portfolio_value*100):.1f}% of portfolio) | "
                                        f"Requesting AI analysis..."
                                    )

                                    # Use RapidAPI for critical risk assessment (large positions)
                                    risk_analysis = assess_risk(
                                        symbol=sym,
                                        position_size=proposed_position_value,
                                        portfolio_value=portfolio_value,
                                        market_conditions=market_conditions,
                                        use_rapidapi=True,  # Use RapidAPI for critical risk decisions
                                    )

                                    if risk_analysis:
                                        risk_level = risk_analysis.get("risk_level", "MEDIUM")
                                        risk_action = risk_analysis.get("action", "HOLD")
                                        max_position_recommended = risk_analysis.get(
                                            "max_position", proposed_position_value
                                        )
                                        risk_reasoning = risk_analysis.get("reasoning", "")

                                        logger.info(
                                            f"🛡️ AI RISK ASSESSMENT [{sym}]: "
                                            f"risk_level={risk_level} | "
                                            f"action={risk_action} | "
                                            f"max_recommended=${max_position_recommended:,.2f} | "
                                            f"reasoning={risk_reasoning[:100] if risk_reasoning else 'N/A'}..."
                                        )

                                        # Apply AI risk recommendations
                                        if risk_level == "CRITICAL":
                                            # Critical risk - reduce position by 75% or skip
                                            buy_value = buy_value * 0.25
                                            logger.warning(
                                                f"🚨 CRITICAL RISK [{sym}]: "
                                                f"AI detected critical risk - reducing position by 75% "
                                                f"(new buy_value=${buy_value:,.2f})"
                                            )
                                            send_telegram(
                                                f"🚨 CRITICAL RISK: {sym}\n"
                                                f"AI Risk Level: CRITICAL\n"
                                                f"Action: Reduced position by 75%\n"
                                                f"New Size: ${buy_value:,.2f}\n"
                                                f"Reasoning: {risk_reasoning[:150] if risk_reasoning else 'High risk detected'}",
                                                include_mode=True,
                                                state=state,
                                            )
                                        elif risk_level == "HIGH":
                                            # High risk - reduce position by 50%
                                            buy_value = buy_value * 0.5
                                            logger.warning(
                                                f"⚠️ HIGH RISK [{sym}]: "
                                                f"AI detected high risk - reducing position by 50% "
                                                f"(new buy_value=${buy_value:,.2f})"
                                            )
                                        elif risk_action == "REDUCE":
                                            # AI recommends reduction - reduce by 30%
                                            buy_value = buy_value * 0.7
                                            logger.info(
                                                f"📉 AI REDUCE [{sym}]: "
                                                f"AI recommends position reduction - reducing by 30% "
                                                f"(new buy_value=${buy_value:,.2f})"
                                            )
                                        elif risk_action == "EXIT" and current_value > 0:
                                            # AI recommends exit - skip new buy, consider selling existing
                                            logger.warning(
                                                f"🛑 AI EXIT [{sym}]: "
                                                f"AI recommends exit - skipping new buy "
                                                f"(existing position=${current_value:,.2f})"
                                            )
                                            buy_value = 0  # Skip buy

                                        # Apply max position recommendation
                                        if (
                                            isinstance(max_position_recommended, (int, float))
                                            and max_position_recommended > 0
                                        ):
                                            max_position_value = float(max_position_recommended)
                                            if proposed_position_value > max_position_value:
                                                buy_value = max(
                                                    0, max_position_value - current_value
                                                )
                                                logger.info(
                                                    f"📊 AI MAX POSITION [{sym}]: "
                                                    f"AI recommends max position=${max_position_value:,.2f} | "
                                                    f"adjusted buy_value=${buy_value:,.2f}"
                                                )
                                    else:
                                        logger.debug(
                                            f"⚠️ AI risk assessment unavailable for {sym} "
                                            f"(RapidAPI may be down or quota exhausted)"
                                        )

                                except ImportError:
                                    logger.debug(
                                        "⚠️ AI risk assessment not available (utils/agent_ai_client.py not found)"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"⚠️ AI risk assessment failed for {sym}: {e}",
                                        exc_info=False,
                                    )
                                    # Don't fail trade if AI risk assessment fails - graceful degradation

                            # Skip if buy_value was reduced to 0 or negative
                            if buy_value <= 0:
                                logger.info(
                                    f"⏭️ Skipping buy for {sym} (buy_value={buy_value:.2f} after risk assessment)"
                                )
                                continue

                            # ADD MAX POSITION SIZE: Don't allocate more than 30% per trade
                            max_trade_size = portfolio_value * 0.30
                            buy_value = min(buy_value, max_trade_size)

                            # === ENTERPRISE KELLY POSITION SIZING (Phase 3300-3500) ===
                            kelly_fraction = None
                            if HAS_KELLY_SIZING:
                                try:
                                    # Calculate win rate and reward-risk from recent trades
                                    # In production, load from performance tracker
                                    win_rate = 0.60  # Default, should come from performance tracker
                                    rr_ratio = 1.4  # Default, should come from performance tracker

                                    # Get stop loss distance (2% default)
                                    stop_loss_distance = float(
                                        os.getenv("STOP_LOSS_DISTANCE", "0.02")
                                    )

                                    # Calculate Kelly-based position size
                                    from analytics.kelly_sizing import calculate_position_size

                                    position_info = calculate_position_size(
                                        equity=broker.equity,
                                        win_rate=win_rate,
                                        reward_risk_ratio=rr_ratio,
                                        stop_loss_distance=stop_loss_distance,
                                        kelly_fraction=0.5,  # Half Kelly for safety
                                        max_risk_per_trade=0.01,  # 1% max risk
                                    )

                                    kelly_position_size = position_info.get(
                                        "position_size", buy_value
                                    )
                                    kelly_fraction = position_info.get("kelly_fraction", None)

                                    # Use Kelly sizing if it's more conservative than default
                                    if kelly_position_size < buy_value:
                                        buy_value = kelly_position_size
                                        logger.info(
                                            f"⚖️ Kelly sizing: {buy_value:,.2f} (Kelly: {kelly_fraction:.2%})"
                                        )
                                except Exception as e:
                                    logger.debug(f"⚠️ Kelly sizing calculation failed: {e}")

                            qty = buy_value / price
                            # CRYPTO: Lower minimum for crypto (0.0001 BTC vs 0.001 stocks)
                            is_crypto = "-USD" in sym
                            min_qty = 0.0001 if is_crypto else 0.001
                            if qty > min_qty:
                                try:
                                    # Add to approval queue for large trades (>$1000)
                                    # PAPER_TRADING_MODE: Auto-approve (skip approval queue)
                                    # Only require approval in LIVE_MODE
                                    require_approval = (
                                        trading_mode == "LIVE_MODE" and buy_value > 1000.0
                                    )
                                    if require_approval:
                                        approval_data = {
                                            "type": "BUY",
                                            "symbol": sym,
                                            "qty": qty,
                                            "price": price,
                                            "amount": buy_value,
                                            "details": f"BUY {qty:.4f} {sym} @ ${price:.2f}",
                                        }
                                        try:
                                            approval_file = ROOT / "state" / "approval_queue.json"
                                            if approval_file.exists():
                                                queue = json.loads(approval_file.read_text())
                                            else:
                                                queue = []
                                            approval_data["id"] = len(queue) + 1
                                            approval_data["timestamp"] = dt.datetime.now(
                                                dt.UTC
                                            ).isoformat()
                                            queue.append(approval_data)
                                            approval_file.write_text(json.dumps(queue, indent=2))
                                            send_telegram(
                                                f"⏸️ Pending Approval: BUY {sym}\n"
                                                f"💰 Amount: ${buy_value:,.2f}\n"
                                                f"📊 Check dashboard for approval",
                                                include_mode=True,
                                                state=state,
                                            )
                                            print(
                                                f"⏸️ Trade queued for approval (amount: ${buy_value:,.2f})",
                                                flush=True,
                                            )
                                            continue
                                        except:
                                            pass  # If approval system not available, proceed

                                    try:
                                        # Phase 2900-3100: Use live execution if in LIVE_MODE
                                        if trading_mode == "LIVE_MODE" and live_engine:
                                            live_result = live_engine.execute_order(
                                                symbol=sym, qty=qty, side="buy", order_type="market"
                                            )
                                            if live_result.get("status") == "success":
                                                # Record paper trade for tracking
                                                result = broker.submit_order(sym, "buy", qty, price)
                                                trade_breaker.record_success()
                                                state["last_trade"][sym] = time.time()
                                                state["trade_count"] += 1
                                                logger.info(
                                                    f"🚀 LIVE TRADE EXECUTED: {sym} BUY x {qty}"
                                                )
                                            elif live_result.get("status") == "halted":
                                                logger.warning(
                                                    f"🛑 Circuit breaker halted trade: {live_result.get('reason')}"
                                                )
                                                continue
                                            else:
                                                logger.error(
                                                    f"❌ Live trade failed: {live_result.get('message')}"
                                                )
                                                trade_breaker.record_failure()
                                                continue
                                        else:
                                            # Paper trading mode
                                            result = broker.submit_order(sym, "buy", qty, price)
                                            trade_breaker.record_success()  # Successful trade
                                            state["last_trade"][sym] = time.time()
                                            state["trade_count"] += 1
                                            # ============================================================================
                                            # DIAGNOSTIC LOGGING: Order submitted
                                            # ============================================================================
                                            logger.info(
                                                f"✅ ORDER SUBMITTED [{sym}]: BUY | "
                                                f"qty={qty:.4f} | "
                                                f"price=${price:,.2f} | "
                                                f"value=${qty * price:,.2f}"
                                            )
                                    except Exception as trade_error:
                                        trade_breaker.record_failure()
                                        raise trade_error

                                    # Log based on mode
                                    if trading_mode == "TEST_MODE":
                                        print(
                                            f"🧪 TEST BUY: {sym}: {qty:.4f} @ ${price:.2f} | RSI={rsi_val:.1f} | Momentum={momentum:.3f}% | Confidence={confidence:.2f} | Fee: ${result['fee']:.2f}",
                                            flush=True,
                                        )
                                        send_telegram(
                                            f"🧪 TEST BUY: {sym}\n"
                                            f"📊 Size: {qty:.4f} @ ${price:.2f}\n"
                                            f"📈 RSI: {rsi_val:.1f} | Momentum: {momentum:.3f}% | Confidence: {confidence:.2f}",
                                            include_mode=True,
                                            state=state,
                                        )
                                    else:
                                        kelly_msg = (
                                            f" | Kelly: {kelly_fraction:.1%}"
                                            if kelly_fraction
                                            else ""
                                        )
                                        print(
                                            f"✅ PAPER BUY: {sym}: {qty:.4f} @ ${price:.2f} | RSI={rsi_val:.1f} | Momentum={momentum:.3f}% | Confidence={confidence:.2f}{kelly_msg} | Fee: ${result['fee']:.2f}",
                                            flush=True,
                                        )
                                        telegram_msg = (
                                            f"✅ PAPER BUY: {sym}\n"
                                            f"📊 Size: {qty:.4f} @ ${price:.2f}\n"
                                            f"📈 RSI: {rsi_val:.1f} | Momentum: {momentum:.3f}% | Confidence: {confidence:.2f}"
                                        )
                                        if kelly_fraction:
                                            telegram_msg += f"\n⚖️ Kelly: {kelly_fraction:.1%}"
                                        send_telegram(telegram_msg, include_mode=True, state=state)

                                    # Update performance attribution (buy has no P&L yet)
                                    # P&L will be updated on sell

                                    # Enhanced trade telemetry with circuit breaker states
                                    start_equity = state["daily"].get("start_equity", broker.equity)
                                    daily_pnl_pct = (
                                        (broker.fetch_portfolio_value() - start_equity)
                                        / max(1.0, start_equity)
                                        * 100
                                    )
                                    current_drawdown = -daily_pnl_pct if daily_pnl_pct < 0 else 0.0

                                    send_to_atlas_bridge(
                                        {
                                            "type": "trade",
                                            "symbol": sym,
                                            "side": "buy",
                                            "qty": qty,
                                            "price": price,
                                            "rsi": rsi_val,
                                            "momentum": momentum,
                                            "confidence": confidence,
                                            "mode": trading_mode,
                                            "current_drawdown": current_drawdown,
                                            "circuit_breaker_state": {
                                                "quote": quote_breaker.get_state_info()["state"],
                                                "trade": trade_breaker.get_state_info()["state"],
                                            },
                                            "timestamp": dt.datetime.now(dt.UTC).isoformat(),
                                        }
                                    )
                                    trade_contexts[sym] = signal_meta
                                except Exception as e:
                                    print(f"❌ Buy error: {e}", flush=True)

                    elif signal == "sell":
                        # ============================================================================
                        # DIAGNOSTIC LOGGING: Sell condition check
                        # ============================================================================
                        pos = broker.get_position(sym)
                        has_position = pos["qty"] > 1e-6

                        logger.info(
                            f"🔍 DIAGNOSTIC [{sym}]: SELL CONDITION CHECK | "
                            f"position_qty={pos['qty']:.6f} > 0.000001 | "
                            f"RESULT={has_position}"
                        )

                        if not has_position:
                            logger.warning(
                                f"❌ BLOCKED [{sym}]: No position to sell (qty={pos['qty']:.6f})"
                            )
                            continue

                        # If we reach here, sell should execute
                        logger.info(
                            f"🚀 DIAGNOSTIC [{sym}]: Sell conditions MET, proceeding to order submission..."
                        )

                        if pos["qty"] > 1e-6:
                            # Sell entire position or trim
                            sell_qty = pos["qty"]
                            # INCREASED threshold from 5% to 10% to reduce overtrading
                            if current_value > target_value * 1.10:  # 10% threshold
                                sell_qty = min(sell_qty, (current_value - target_value) / price)

                            if sell_qty > 1e-6:
                                try:
                                    # Phase 2900-3100: Use live execution if in LIVE_MODE
                                    if trading_mode == "LIVE_MODE" and live_engine:
                                        live_result = live_engine.execute_order(
                                            symbol=sym,
                                            qty=sell_qty,
                                            side="sell",
                                            order_type="market",
                                        )
                                        if live_result.get("status") == "success":
                                            # Record paper trade for tracking
                                            result = broker.submit_order(
                                                sym, "sell", sell_qty, price
                                            )
                                            trade_breaker.record_success()
                                            state["last_trade"][sym] = time.time()
                                            state["trade_count"] += 1
                                            logger.info(
                                                f"🚀 LIVE TRADE EXECUTED: {sym} SELL x {sell_qty}"
                                            )
                                        elif live_result.get("status") == "halted":
                                            logger.warning(
                                                f"🛑 Circuit breaker halted trade: {live_result.get('reason')}"
                                            )
                                            continue
                                        else:
                                            logger.error(
                                                f"❌ Live trade failed: {live_result.get('message')}"
                                            )
                                            trade_breaker.record_failure()
                                            continue
                                    else:
                                        # Paper trading mode
                                        result = broker.submit_order(sym, "sell", sell_qty, price)
                                        trade_breaker.record_success()  # Successful trade
                                        state["last_trade"][sym] = time.time()
                                        state["trade_count"] += 1
                                        # ============================================================================
                                        # DIAGNOSTIC LOGGING: Order submitted
                                        # ============================================================================
                                        logger.info(
                                            f"✅ ORDER SUBMITTED [{sym}]: SELL | "
                                            f"qty={sell_qty:.4f} | "
                                            f"price=${price:,.2f} | "
                                            f"value=${sell_qty * price:,.2f}"
                                        )
                                    pnl = result.get("pnl", 0)
                                    # Calculate P&L percentage safely
                                    if sell_qty > 0 and pos.get("avg_price", 0) > 0:
                                        pnl_pct = (pnl / (sell_qty * pos["avg_price"])) * 100
                                    else:
                                        pnl_pct = 0.0

                                    # Log P&L for debugging
                                    logger.info(
                                        f"💰 P&L CALCULATION [{sym}]: "
                                        f"pnl=${pnl:.2f} | "
                                        f"pnl_pct={pnl_pct:.2f}% | "
                                        f"sell_qty={sell_qty:.4f} | "
                                        f"avg_price=${pos.get('avg_price', 0):.2f}"
                                    )

                                    # Update performance attribution with P&L
                                    decision_idx = pending_decisions.pop(sym, None)
                                    if decision_idx is not None:
                                        update_trade_pnl(decision_idx, pnl)

                                    # === UPDATE STRATEGY PERFORMANCE (Phase 3500-3700) ===
                                    if HAS_STRATEGY_MANAGER and strategy_manager:
                                        try:
                                            context = trade_contexts.get(sym, {})
                                            strategy_signals_ctx = context.get(
                                                "strategy_signals", {}
                                            )
                                            strategy_votes_ctx = context.get("strategy_votes", {})
                                            active_strategies_ctx = context.get(
                                                "active_strategies", []
                                            )

                                            contributing_strategies = []
                                            if strategy_signals_ctx:
                                                if signal == "buy":
                                                    contributing_strategies = [
                                                        s
                                                        for s, sig in strategy_signals_ctx.items()
                                                        if sig.get("signal") == "buy"
                                                    ]
                                                elif signal == "sell":
                                                    contributing_strategies = [
                                                        s
                                                        for s, sig in strategy_signals_ctx.items()
                                                        if sig.get("signal") == "sell"
                                                    ]

                                            if not contributing_strategies:
                                                if (
                                                    signal == "buy"
                                                    and strategy_votes_ctx.get("buy", 0) > 0
                                                ) or (
                                                    signal == "sell"
                                                    and strategy_votes_ctx.get("sell", 0) > 0
                                                ):
                                                    contributing_strategies = list(
                                                        active_strategies_ctx
                                                    )[:2]

                                            if contributing_strategies:
                                                pnl_per_strategy = pnl / len(
                                                    contributing_strategies
                                                )
                                                for strategy_name in contributing_strategies:
                                                    strategy_manager.update_strategy_pnl(
                                                        strategy_name,
                                                        pnl_per_strategy,
                                                        trade_count=1,
                                                    )
                                                logger.debug(
                                                    f"📊 Updated strategy P&L: {contributing_strategies} = {pnl_per_strategy:.2f} each"
                                                )
                                        except Exception as e:
                                            logger.debug(
                                                f"⚠️ Strategy performance update failed: {e}"
                                            )
                                        finally:
                                            trade_contexts.pop(sym, None)
                                    else:
                                        trade_contexts.pop(sym, None)

                                    # DIAGNOSTIC: Log before mode check
                                    logger.info(
                                        f"🔍 DIAGNOSTIC [{sym}]: About to check trading mode for Telegram send | "
                                        f"trading_mode={trading_mode} | "
                                        f"pnl=${pnl:.2f} | "
                                        f"pnl_pct={pnl_pct:.2f}%"
                                    )

                                    # Track test sells for mode transition
                                    if trading_mode == "TEST_MODE":
                                        # CRITICAL: Ensure test_sells counter exists and increment
                                        if "test_sells" not in state:
                                            state["test_sells"] = 0
                                        state["test_sells"] += 1
                                        test_sell_count = state["test_sells"]

                                        # CRITICAL: Save state immediately after increment
                                        try:
                                            state_to_save = state.copy()
                                            if "price_history" in state_to_save:
                                                state_to_save["price_history"] = {
                                                    sym: list(prices)
                                                    if isinstance(prices, deque)
                                                    else prices
                                                    for sym, prices in state_to_save[
                                                        "price_history"
                                                    ].items()
                                                }
                                            state_file = ROOT / "state" / "trader_state.json"
                                            with open(state_file, "w") as f:
                                                json.dump(state_to_save, f, indent=4)
                                            logger.info(
                                                f"💾 Saved state: test_sells={test_sell_count}"
                                            )
                                        except Exception as e:
                                            logger.warning(
                                                f"⚠️ Could not save state after test sell: {e}"
                                            )

                                        print(
                                            f"🧪 TEST SELL: {sym}: {sell_qty:.4f} @ ${price:.2f} | RSI={rsi_val:.1f} | Momentum={momentum:.3f}% | Confidence={confidence:.2f} | P&L: ${result.get('pnl', 0):.2f} ({pnl_pct:.2f}%) | Test sells: {test_sell_count}/2",
                                            flush=True,
                                        )
                                        logger.info(
                                            f"📊 Test sell #{test_sell_count} completed for {sym}"
                                        )

                                        send_telegram(
                                            f"🧪 TEST SELL #{test_sell_count}: {sym}\n"
                                            f"📊 Size: {sell_qty:.4f} @ ${price:.2f}\n"
                                            f"💰 P&L: ${result.get('pnl', 0):.2f}\n"
                                            f"📈 Progress: {test_sell_count}/2 test sells",
                                            include_mode=True,
                                            state=state,
                                        )

                                        # Auto-switch to PAPER_TRADING_MODE after 2 test sells
                                        logger.info(
                                            f"🔍 Checking transition: test_sell_count={test_sell_count}, trading_mode={trading_mode}"
                                        )
                                        if test_sell_count >= 2:
                                            trading_mode = "PAPER_TRADING_MODE"
                                            state["trading_mode"] = (
                                                trading_mode  # Persist mode in state
                                            )

                                            # Persist mode to file for recovery
                                            try:
                                                (ROOT / "state").mkdir(parents=True, exist_ok=True)
                                                mode_file = ROOT / "state" / "trading_mode.json"
                                                mode_file.write_text(
                                                    json.dumps(
                                                        {
                                                            "mode": trading_mode,
                                                            "timestamp": dt.datetime.now(
                                                                dt.UTC
                                                            ).isoformat(),
                                                            "reason": "2 test sells completed",
                                                        },
                                                        indent=2,
                                                    )
                                                )
                                                logger.info(
                                                    f"💾 Saved trading mode: {trading_mode}"
                                                )

                                                # Also save state immediately
                                                state_to_save = state.copy()
                                                if "price_history" in state_to_save:
                                                    state_to_save["price_history"] = {
                                                        sym: list(prices)
                                                        if isinstance(prices, deque)
                                                        else prices
                                                        for sym, prices in state_to_save[
                                                            "price_history"
                                                        ].items()
                                                    }
                                                state_file = ROOT / "state" / "trader_state.json"
                                                with open(state_file, "w") as f:
                                                    json.dump(state_to_save, f, indent=4)
                                            except Exception as e:
                                                logger.warning(f"⚠️ Could not persist mode: {e}")

                                            print(
                                                "🚀 Switching SmartTrader from TEST MODE → PAPER_TRADING_MODE",
                                                flush=True,
                                            )
                                            print(
                                                f"✅ Mode transition complete: {trading_mode}",
                                                flush=True,
                                            )
                                            logger.info(
                                                "✅ Transition trigger: 2 test sells completed"
                                            )
                                            logger.info(
                                                "🔁 Switching from TEST_MODE → PAPER_TRADING_MODE"
                                            )
                                            send_telegram(
                                                "🚀 Mode Transition: TEST_MODE → PAPER_TRADING_MODE\n"
                                                "✅ 2 test sells completed successfully\n"
                                                "🟢 Paper trading now active",
                                                include_mode=True,
                                                mode="PAPER_TRADING_MODE",
                                                state=state,
                                            )

                                            # Send mode transition telemetry
                                            send_to_atlas_bridge(
                                                {
                                                    "type": "mode_transition",
                                                    "from": "TEST_MODE",
                                                    "to": "PAPER_TRADING_MODE",
                                                    "reason": "2 test sells completed",
                                                    "timestamp": dt.datetime.now(
                                                        dt.UTC
                                                    ).isoformat(),
                                                }
                                            )
                                    else:
                                        # DIAGNOSTIC: Log before PAPER SELL Telegram send
                                        logger.info(
                                            f"🔍 DIAGNOSTIC [{sym}]: Entering PAPER_TRADING_MODE block | "
                                            f"About to send Telegram message"
                                        )
                                        print(
                                            f"✅ PAPER SELL: {sym}: {sell_qty:.4f} @ ${price:.2f} | RSI={rsi_val:.1f} | Momentum={momentum:.3f}% | Confidence={confidence:.2f} | P&L: ${pnl:.2f} ({pnl_pct:.2f}%)",
                                            flush=True,
                                        )
                                        logger.info(
                                            f"📤 DIAGNOSTIC [{sym}]: Calling send_telegram() for PAPER SELL"
                                        )
                                        send_telegram(
                                            f"✅ PAPER SELL: {sym}\n"
                                            f"📊 Size: {sell_qty:.4f} @ ${price:.2f}\n"
                                            f"💰 P&L: ${pnl:.2f} ({pnl_pct:.2f}%)\n"
                                            f"📈 RSI: {rsi_val:.1f} | Momentum: {momentum:.3f}%",
                                            include_mode=True,
                                            state=state,
                                        )
                                        logger.info(
                                            f"✅ DIAGNOSTIC [{sym}]: send_telegram() call completed"
                                        )

                                    # Enhanced trade telemetry with circuit breaker states
                                    start_equity = state["daily"].get("start_equity", broker.equity)
                                    daily_pnl_pct = (
                                        (broker.fetch_portfolio_value() - start_equity)
                                        / max(1.0, start_equity)
                                        * 100
                                    )
                                    current_drawdown = -daily_pnl_pct if daily_pnl_pct < 0 else 0.0

                                    send_to_atlas_bridge(
                                        {
                                            "type": "trade",
                                            "symbol": sym,
                                            "side": "sell",
                                            "qty": sell_qty,
                                            "price": price,
                                            "rsi": rsi_val,
                                            "momentum": momentum,
                                            "confidence": confidence,
                                            "pnl": result.get("pnl", 0),
                                            "pnl_pct": pnl_pct,
                                            "mode": trading_mode,
                                            "current_drawdown": current_drawdown,
                                            "circuit_breaker_state": {
                                                "quote": quote_breaker.get_state_info()["state"],
                                                "trade": trade_breaker.get_state_info()["state"],
                                            },
                                            "timestamp": dt.datetime.now(dt.UTC).isoformat(),
                                        }
                                    )
                                except Exception as trade_error:
                                    trade_breaker.record_failure()
                                    print(f"❌ Sell error: {trade_error}", flush=True)

                # TEST MODE: Sanity trade after 10 loops if no trades executed
                if (
                    trading_mode == "TEST_MODE"
                    and loop_count >= 10
                    and state["trade_count"] == 0
                    and not state.get("test_trade_executed", False)
                ):
                    # Place a small test trade to validate order flow
                    test_symbol = (
                        crypto_symbols[0] if crypto_symbols else SYMBOLS[0]
                    )  # Use first crypto or first symbol

                    logger.info("=" * 80)
                    logger.info(f"🧪 TEST_MODE: Executing test trade for {test_symbol}")
                    logger.info("=" * 80)

                    # ========================================================================
                    # FIX #1: Check quote_service exists with detailed logging
                    # ========================================================================

                    if quote_service is None:
                        logger.error("❌ CRITICAL: quote_service is None!")
                        logger.error("   quote_service failed to initialize at startup")
                        logger.error("   Check startup logs for initialization errors")
                        logger.error("   Verify trader/quote_service.py exists")
                        logger.error("   Verify HAS_QUOTE_SERVICE is True")

                        # Mark as executed to prevent infinite retries
                        state["test_trade_executed"] = True
                        continue  # Skip to next loop iteration

                    logger.info(f"✅ quote_service available: {type(quote_service).__name__}")

                    # ========================================================================
                    # FIX #2: Use SAME method as PAPER_TRADING_MODE (proven to work)
                    # Remove atomic_trade_context() - it was throwing exceptions
                    # ========================================================================

                    try:
                        logger.info(f"📊 Fetching quote for {test_symbol}...")

                        # Use direct quote fetch (same as PAPER_TRADING_MODE at line 2381)
                        # Changed from max_age=10 (too strict) to max_age=60 (same as PAPER_TRADING_MODE)
                        validated_quote = quote_service.get_quote(test_symbol, max_age=60)
                        if validated_quote is None:
                            # Detailed error logging for troubleshooting
                            logger.error(f"❌ quote_service.get_quote() returned None for {test_symbol}")
                            logger.error("")
                            logger.error("   ALL quote sources failed:")
                            logger.error("   1. Alpaca API")
                            logger.error("   2. Finnhub")
                            logger.error("   3. TwelveData")
                            logger.error("   4. AlphaVantage")
                            logger.error("   5. Yahoo Finance")
                            logger.error("")
                            logger.error("   Possible causes:")
                            logger.error("   - API keys not set: Check ALPACA_API_KEY, FINNHUB_API_KEY, etc.")
                            logger.error("   - Rate limits hit: Wait and retry")
                            logger.error("   - Network issues: Check Render connectivity")
                            logger.error("   - Symbol format: BTC-USD might not be recognized")
                            logger.error("")
                            logger.error("   Environment variables:")
                            logger.error(f"     ALPACA_API_KEY: {'SET' if os.getenv('ALPACA_API_KEY') else 'NOT SET'}")
                            logger.error(f"     NEOLIGHT_USE_ALPACA_QUOTES: {os.getenv('NEOLIGHT_USE_ALPACA_QUOTES')}")

                            # Mark as executed
                            state["test_trade_executed"] = True
                            continue

                        # ====================================================================
                        # SUCCESS: Quote fetched
                        # ====================================================================

                        logger.info(f"✅ Quote fetched successfully:")
                        logger.info(f"   Symbol: {test_symbol}")
                        logger.info(f"   Price: ${validated_quote.last_price:,.2f}")
                        logger.info(f"   Source: {validated_quote.source}")
                        logger.info(f"   Age: {validated_quote.age_seconds:.1f}s")
                        logger.info(f"   Spread: {validated_quote.spread_percent:.3f}%")

                        # Convert to float safely
                        raw_price = validated_quote.last_price
                        if isinstance(raw_price, (int, float)):
                            test_price = float(raw_price)
                        else:
                            # Handle Decimal or string edge cases
                            test_price = safe_float_convert(
                                raw_price,
                                symbol=test_symbol,
                                context="quote last_price",
                                state=state,
                            )
                            if test_price is None:
                                error_msg = f"Invalid price from quote: {raw_price} ({type(raw_price)})"
                                logger.error(f"❌ {error_msg}")
                                raise ValueError(error_msg)

                        # CRITICAL: Verify price is actually a float before using
                        if not isinstance(test_price, (int, float)) or test_price <= 0:
                            error_msg = f"Invalid price type after conversion: {test_price} ({type(test_price)})"
                            logger.error(f"❌ {error_msg}")
                            raise ValueError(error_msg)

                        logger.info(
                            f"🧪 Using quote: {test_symbol} @ ${test_price:,.2f} (source={validated_quote.source}, type={type(test_price).__name__})"
                        )

                        # Small test trade: 0.001 BTC or equivalent
                        if test_symbol == "BTC-USD":
                            test_qty = 0.001
                        elif test_symbol == "ETH-USD":
                            test_qty = 0.01  # ETH equivalent
                        else:
                            test_qty = max(
                                0.001, 10.0 / test_price
                            )  # $10 worth, minimum 0.001

                        # CRITICAL: Log exactly what we're passing to submit_order
                        logger.info(
                            f"🔍 About to call submit_order: symbol={test_symbol}, qty={test_qty} (type={type(test_qty).__name__}), price={test_price} (type={type(test_price).__name__})"
                        )

                        try:
                            result = broker.submit_order(
                                test_symbol, "buy", test_qty, test_price
                            )
                            trade_breaker.record_success()  # Successful trade
                            state["last_trade"][test_symbol] = time.time()
                            state["trade_count"] += 1
                            state["test_trade_executed"] = True

                            # Log successful test trade
                            logger.info("=" * 80)
                            logger.info("✅ TEST TRADE EXECUTED SUCCESSFULLY")
                            logger.info("=" * 80)
                            logger.info(f"   Symbol: {test_symbol}")
                            logger.info(f"   Side: BUY")
                            logger.info(f"   Price: ${test_price:,.2f}")
                            logger.info(f"   Quantity: {test_qty:.4f}")
                            logger.info(f"   Source: {validated_quote.source}")
                            logger.info(f"   Mode: TEST")
                            logger.info("=" * 80)

                            print(
                                f"🧪 TEST TRADE: BUY {test_symbol}: {test_qty:.4f} @ ${test_price:.2f} | Fee: ${result.get('fee', 0):.2f}",
                                flush=True,
                            )
                            print(
                                f"💥 Executed TEST BUY: {test_symbol} @ ${test_price:,.2f} | Size: {test_qty:.4f}",
                                flush=True,
                            )
                            send_telegram(
                                f"✅ TEST TRADE EXECUTED\n"
                                f"Symbol: {test_symbol}\n"
                                f"Side: BUY\n"
                                f"Price: ${test_price:,.2f}\n"
                                f"Quantity: {test_qty:.4f}\n"
                                f"Source: {validated_quote.source}\n"
                                f"Mode: TEST",
                                include_mode=True,
                                state=state,
                            )

                            # Send to Atlas Bridge
                            send_to_atlas_bridge(
                                {
                                    "type": "test_trade",
                                    "symbol": test_symbol,
                                    "side": "buy",
                                    "qty": test_qty,
                                    "price": test_price,
                                    "quote_sequence": validated_quote.sequence_id,
                                    "mode": trading_mode,
                                    "timestamp": dt.datetime.now(dt.UTC).isoformat(),
                                }
                            )
                        except (ValueError, TypeError) as e:
                            trade_breaker.record_failure()
                            error_msg = f"Order validation error: {e}"
                            logger.error(
                                f"❌ Test trade validation error for {test_symbol}: {error_msg}"
                            )
                            print(f"❌ Test trade error: {error_msg}", flush=True)
                            send_telegram(
                                f"⚠️ Test trade skipped: {test_symbol}\n"
                                f"📊 Reason: {error_msg}",
                                include_mode=True,
                                state=state,
                            )
                        except Exception as e:
                            trade_breaker.record_failure()
                            logger.error(
                                f"❌ Test trade execution error for {test_symbol}: {e}",
                                exc_info=True,
                            )
                            print(f"❌ Test trade error: {e}", flush=True)
                            send_telegram(
                                f"⚠️ Test trade execution error: {test_symbol}\n"
                                f"📊 Error: {str(e)}",
                                include_mode=True,
                                state=state,
                            )
                    except Exception as e:
                            logger.warning(f"⚠️ Test trade skipped: {test_symbol} - {e}")
                            send_telegram(
                                f"⚠️ Test trade skipped: {test_symbol}\n📊 Reason: {str(e)}",
                                include_mode=True,
                                state=state,
                            )
                    else:
                        # Fallback: Try to use quote_service if available, otherwise use broker.fetch_quote()
                        quote = None
                        
                        # First, try to re-initialize quote_service if it's None but available
                        if not quote_service and HAS_QUOTE_SERVICE:
                            try:
                                quote_service = get_quote_service()
                                logger.info("✅ Re-initialized QuoteService for TEST_MODE fallback")
                            except Exception as e:
                                logger.warning(f"⚠️ Failed to re-initialize QuoteService: {e}")
                        
                        # Try quote_service first (if available)
                        if quote_service:
                            try:
                                validated_quote = quote_service.get_quote(test_symbol, max_age=10)
                                if validated_quote:
                                    quote = validated_quote.to_dict()
                                    logger.debug(f"📊 {test_symbol} Quote ({validated_quote.source}): {validated_quote.last_price:.2f}")
                            except Exception as e:
                                logger.warning(f"⚠️ QuoteService failed for {test_symbol}: {e}")
                        
                        # If quote_service didn't work, try broker.fetch_quote() as fallback
                        if not quote:
                            logger.debug(f"⚠️ QuoteService unavailable or failed, trying broker.fetch_quote() for {test_symbol}")
                            quote = broker.fetch_quote(test_symbol)
                            if quote:
                                logger.debug(f"📊 {test_symbol} Quote (broker fallback): {quote.get('mid', quote.get('last', 'N/A'))}")
                        
                        if not quote:
                            logger.warning(
                                f"⚠️ Could not fetch quote for test trade ({test_symbol}), skipping"
                            )
                            send_telegram(
                                f"⚠️ Test trade skipped: {test_symbol}\n"
                                f"📊 Reason: Could not fetch quote",
                                include_mode=True,
                                state=state,
                            )
                        else:
                            # Use safe conversion function
                            test_price_candidate = (
                                quote.get("mid")
                                or quote.get("last")
                                or quote.get("regularMarketPrice")
                                or quote.get("currentPrice")
                            )
                            safe_test_price = safe_float_convert(
                                test_price_candidate,
                                symbol=test_symbol,
                                context="test trade price",
                                state=state,
                            )
                            if safe_test_price is None:
                                logger.error(
                                    f"❌ Test trade validation error for {test_symbol}: Invalid or empty price in quote"
                                )
                                send_telegram(
                                    f"⚠️ Test trade skipped: {test_symbol}\n"
                                    f"📊 Reason: Invalid or empty price received from data source",
                                    include_mode=True,
                                    state=state,
                                )
                                continue

                            test_price = safe_test_price

                            # Small test trade
                            if test_symbol == "BTC-USD":
                                test_qty = 0.001
                            elif test_symbol == "ETH-USD":
                                test_qty = 0.01
                            else:
                                test_qty = max(0.001, 10.0 / test_price)

                            try:
                                result = broker.submit_order(
                                    test_symbol, "buy", test_qty, test_price
                                )
                                trade_breaker.record_success()
                                state["last_trade"][test_symbol] = time.time()
                                state["trade_count"] += 1
                                state["test_trade_executed"] = True
                                print(
                                    f"🧪 TEST TRADE: BUY {test_symbol}: {test_qty:.4f} @ ${test_price:.2f}",
                                    flush=True,
                                )
                                send_telegram(
                                    f"🧪 TEST TRADE: BUY {test_symbol}\n"
                                    f"📊 Size: {test_qty:.4f} @ ${test_price:.2f}",
                                    include_mode=True,
                                    state=state,
                                )
                            except Exception as e:
                                trade_breaker.record_failure()
                                logger.error(f"❌ Test trade error for {test_symbol}: {e}")
                                send_telegram(
                                    f"⚠️ Test trade skipped: {test_symbol}\n📊 Reason: {str(e)}",
                                    include_mode=True,
                                    state=state,
                                )

                # Periodic state persistence (every 5 minutes)
                if loop_count % 60 == 0:  # Every 5 minutes (60 loops * 5 seconds)
                    try:
                        state_to_save = state.copy()
                        if "price_history" in state_to_save:
                            state_to_save["price_history"] = {
                                sym: list(prices) if isinstance(prices, deque) else prices
                                for sym, prices in state_to_save["price_history"].items()
                            }
                        state_file = ROOT / "state" / "trader_state.json"
                        with open(state_file, "w") as f:
                            json.dump(state_to_save, f, indent=4)
                    except Exception as e:
                        logger.warning(f"⚠️ Could not save state periodically: {e}")

                # PHASE 5400: Enhanced telemetry with Guardian + Circuit Breaker states
                if loop_count % 60 == 0:  # Every 5 minutes (60 loops * 5 seconds)
                    equity = broker.fetch_portfolio_value()
                    start_equity = state["daily"].get("start_equity", broker.equity)
                    daily_pnl_pct = (equity - start_equity) / max(1.0, start_equity) * 100
                    current_drawdown = -daily_pnl_pct if daily_pnl_pct < 0 else 0.0

                    # Get circuit breaker states
                    quote_state = quote_breaker.get_state_info()
                    trade_state = trade_breaker.get_state_info()

                    # Check for state changes and send Telegram alerts
                    if quote_state["state"] != last_circuit_states["quote"]:
                        if quote_state["state"] == "CLOSED":
                            send_telegram(
                                "🟢 Circuit breaker CLOSED\n"
                                "📊 QuoteFetcher: Normal trading resumed",
                                include_mode=True,
                                state=state,
                            )
                            print(
                                "🟢 Circuit breaker CLOSED - QuoteFetcher: Normal trading resumed",
                                flush=True,
                            )
                        elif quote_state["state"] == "OPEN":
                            send_telegram(
                                f"🔴 Circuit breaker OPEN\n"
                                f"📊 QuoteFetcher: {quote_state['failure_count']} failures",
                                include_mode=True,
                                state=state,
                            )
                        last_circuit_states["quote"] = quote_state["state"]

                    if trade_state["state"] != last_circuit_states["trade"]:
                        if trade_state["state"] == "CLOSED":
                            send_telegram(
                                "🟢 Circuit breaker CLOSED\n"
                                "📊 TradeExecution: Normal trading resumed",
                                include_mode=True,
                                state=state,
                            )
                            print(
                                "🟢 Circuit breaker CLOSED - TradeExecution: Normal trading resumed",
                                flush=True,
                            )
                        elif trade_state["state"] == "OPEN":
                            send_telegram(
                                f"🔴 Circuit breaker OPEN\n"
                                f"📊 TradeExecution: {trade_state['failure_count']} failures",
                                include_mode=True,
                                state=state,
                            )
                        last_circuit_states["trade"] = trade_state["state"]

                    # Enhanced telemetry payload
                    telemetry_data = {
                        "type": "telemetry",
                        "equity": equity,
                        "cash": broker.cash,
                        "daily_pnl_pct": daily_pnl_pct,
                        "current_drawdown": current_drawdown,
                        "mode": trading_mode,
                        "trade_count": state["trade_count"],
                        "test_sells": state.get("test_sells", 0),
                        "loop_count": loop_count,
                        "guardian": {
                            "is_paused": is_paused,
                            "current_drawdown": current_drawdown,
                            "pause_reason": pause_reason if is_paused else "Normal operation",
                        },
                        "circuit_breakers": {
                            "quote_fetcher": quote_state,
                            "trade_execution": trade_state,
                        },
                        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
                    }

                    send_to_atlas_bridge(telemetry_data)

                    # PHASE 5600: Push to meta-metrics endpoint as well
                    try:
                        import sys

                        sys.path.insert(0, str(ROOT))
                        from agents.phase_5600_hive_telemetry import (
                            build_meta_metrics,
                            push_to_meta_metrics,
                        )

                        # Update mode in metrics
                        meta_metrics = build_meta_metrics()
                        meta_metrics["mode"] = trading_mode
                        meta_metrics["guardian"]["drawdown"] = current_drawdown
                        meta_metrics["guardian"]["is_paused"] = is_paused
                        meta_metrics["breakers"]["quote_state"] = quote_state["state"]
                        meta_metrics["breakers"]["trade_state"] = trade_state["state"]
                        push_to_meta_metrics(meta_metrics)
                    except Exception:
                        pass  # Silent fail if Phase 5600 not available

                    # Log state summary every 5 minutes
                    print(
                        f"📊 Phase 5400 Telemetry: Drawdown={current_drawdown:.2f}% | Quote={quote_state['state']} | Trade={trade_state['state']} | Mode={trading_mode}",
                        flush=True,
                    )

                # Hourly status update
                if loop_count % 3600 == 0:  # Every hour (assuming 1s sleep)
                    equity = broker.fetch_portfolio_value()
                    start_equity = state["daily"].get("start_equity", broker.equity)
                    daily_pnl_pct = (equity - start_equity) / max(1.0, start_equity) * 100
                    print(
                        f"⏰ Hourly Status | Equity: ${equity:,.2f} | Daily P&L: {daily_pnl_pct:.2f}% | Trades: {state['trade_count']}",
                        flush=True,
                    )
                    send_telegram(
                        f"⏰ Hourly Status\n"
                        f"💰 Equity: ${equity:,.2f}\n"
                        f"📊 Daily P&L: {daily_pnl_pct:.2f}%\n"
                        f"📈 Trades: {state['trade_count']}",
                        include_mode=True,
                        state=state,
                    )

                time.sleep(5)  # Check every 5 seconds

            except KeyboardInterrupt:
                stop_flag["stop"] = True
                break
            except Exception as e:
                consecutive_errors += 1
                print(
                    f"💥 Loop error ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {e}",
                    flush=True,
                )
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print(
                        "❌ Too many consecutive errors - exiting for Guardian to restart",
                        flush=True,
                    )
                    send_telegram(
                        f"❌ SmartTrader exiting after {consecutive_errors} errors\n"
                        f"🔄 Guardian will restart automatically",
                        include_mode=True,
                        state=state,
                    )
                    break
                traceback.print_exc()
                time.sleep(10)

    except KeyboardInterrupt:
        logger.warning("🛑 SmartTrader manually stopped (KeyboardInterrupt)")
        print("🛑 SmartTrader manually stopped.", flush=True)
    except Exception as e:
        logger.exception(f"💥 Unhandled exception in SmartTrader: {e}")
        print(f"💥 Unhandled exception: {e}", flush=True)
        send_telegram(
            f"❌ SmartTrader crashed: {str(e)}\n🔄 Guardian will restart automatically",
            include_mode=True,
            state=state,
        )
    finally:
        # --- Final state persistence on exit ---
        try:
            # Ensure state directory exists
            (ROOT / "state").mkdir(parents=True, exist_ok=True)

            # Convert deque to list for JSON serialization
            state_to_save = state.copy()
            if "price_history" in state_to_save:
                state_to_save["price_history"] = {
                    sym: list(prices) if isinstance(prices, deque) else prices
                    for sym, prices in state_to_save["price_history"].items()
                }

            # Save state
            with open(state_file, "w") as f:
                json.dump(state_to_save, f, indent=4)
            logger.info("✅ State saved successfully on exit")
        except Exception as e:
            logger.error(f"❌ Failed to save state on exit: {e}")

    # Final summary
    try:
        final_equity = broker.fetch_portfolio_value()
        total_return = (final_equity - 100000.0) / 100000.0 * 100
        print("\n👋 Final Summary:")
        print("   Starting Equity: $100,000.00")
        print(f"   Final Equity: ${final_equity:,.2f}")
        print(f"   Total Return: {total_return:.2f}%")
        print(f"   Total Trades: {state.get('trade_count', 0)}", flush=True)
        send_telegram(
            f"👋 SmartTrader stopped\n"
            f"💰 Final Equity: ${final_equity:,.2f}\n"
            f"📊 Total Return: {total_return:.2f}%",
            include_mode=True,
            state=state,
        )
    except Exception as e:
        logger.warning(f"⚠️ Could not generate final summary: {e}")

    print("👋 Exiting cleanly.", flush=True)


if __name__ == "__main__":
    main()

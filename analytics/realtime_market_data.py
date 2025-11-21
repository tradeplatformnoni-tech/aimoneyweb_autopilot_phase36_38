#!/usr/bin/env python3
"""
Real-Time Market Data Pipeline - World-Class Implementation
==========================================================
Enhanced market data infrastructure for paper trading:
- Streaming price updates
- Order book simulation
- Trade tape analysis
- Volume profile analysis
- Real-time volatility calculation
"""

import json
import logging
import os
import time
import traceback
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import pandas as pd

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import yfinance as yf

    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
DATA = ROOT / "data"
LOGS = ROOT / "logs"
UNIVERSE_FILE = STATE / "market_universe_snapshot.json"
ALLOCATION_OVERRIDE_FILE = RUNTIME / "allocations_override.json"
ALLOCATION_SYMBOLS_FILE = RUNTIME / "allocations_symbols.json"

YAHOO_ONLY_SYMBOLS: list[str] = [
    "GC=F",
    "SI=F",
    "CL=F",
    "NG=F",
    "PL=F",
    "PA=F",
    "RB=F",
    "HO=F",
    "HG=F",
    "ZS=F",
    "KC=F",
    "SB=F",
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "NZDUSD=X",
    "USDMXN=X",
    "USDZAR=X",
    "USDNOK=X",
    "USDSEK=X",
    "^TYX",
    "^FVX",
    "^VIX",
    "MOVE.P",
    "SRLN",
    "FDN",
    "BOTZ",
    "ROBO",
    "ARKQ",
    "AIQ",
    "GBTC",
    "BITO",
    "BKCH",
    "PALL",
    "PPLT",
    "URA",
    "LIT",
    "REMX",
]


def _load_alpaca_universe() -> list[str]:
    """Load Alpaca-facing symbols from allocations override."""
    try:
        for path in (ALLOCATION_SYMBOLS_FILE, ALLOCATION_OVERRIDE_FILE):
            if path.exists():
                data = json.loads(path.read_text())
                allocations = data.get("allocations", {}) if isinstance(data, dict) else {}
                if isinstance(allocations, dict) and allocations:
                    return sorted(allocations.keys())
    except Exception as exc:
        # Defer to defaults if file is missing or malformed
        logging.getLogger("realtime_market_data").warning(
            "⚠️ Failed to load allocations override: %s", exc
        )
    return [
        "BTC-USD",
        "ETH-USD",
        "SOL-USD",
        "NVDA",
        "MSFT",
        "GOOGL",
        "META",
        "AVGO",
        "ASML",
        "AMD",
        "SMCI",
        "AMZN",
        "COST",
        "GLD",
        "USO",
        "TLT",
    ]


ALPACA_CORE_SYMBOLS: list[str] = _load_alpaca_universe()
DEFAULT_SYMBOLS: list[str] = sorted(set(ALPACA_CORE_SYMBOLS + YAHOO_ONLY_SYMBOLS))

for d in [STATE, RUNTIME, DATA, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS / "realtime_market_data.log"
logger = logging.getLogger("realtime_market_data")
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


def _write_universe_snapshot() -> None:
    """Persist latest market universe snapshot for downstream dashboards."""
    snapshot = {
        "timestamp": datetime.now(UTC).isoformat(),
        "alpaca_symbols": ALPACA_CORE_SYMBOLS,
        "yahoo_only_symbols": YAHOO_ONLY_SYMBOLS,
    }
    try:
        UNIVERSE_FILE.write_text(json.dumps(snapshot, indent=2))
    except Exception as exc:
        logger.debug("Universe snapshot write failed: %s", exc)


_write_universe_snapshot()

MARKET_DATA_FILE = STATE / "realtime_market_data.json"
ORDER_BOOK_FILE = STATE / "order_book_simulation.json"
TRADE_TAPE_FILE = STATE / "trade_tape.json"


class RealTimeMarketDataPipeline:
    """Enhanced real-time market data pipeline."""

    def __init__(self, symbols: list[str] = None):
        """
        Initialize market data pipeline.

        Args:
            symbols: List of symbols to track
        """
        selected_symbols = symbols or DEFAULT_SYMBOLS
        # Preserve insertion order while ensuring uniqueness
        seen = set()
        ordered_symbols: list[str] = []
        for sym in selected_symbols:
            if sym not in seen:
                ordered_symbols.append(sym)
                seen.add(sym)

        self.symbols = ordered_symbols
        self.alpaca_symbols = [s for s in ordered_symbols if s in ALPACA_CORE_SYMBOLS]
        self.yahoo_only_symbols = [s for s in ordered_symbols if s in YAHOO_ONLY_SYMBOLS]

        self.price_history = {symbol: deque(maxlen=1000) for symbol in self.symbols}
        self.volume_history = {symbol: deque(maxlen=1000) for symbol in self.symbols}
        self.order_books = {}
        self.trade_tape = {symbol: deque(maxlen=500) for symbol in self.symbols}

        logger.info(
            "✅ RealTimeMarketDataPipeline initialized for %d symbols (%d Alpaca / %d Yahoo-only)",
            len(self.symbols),
            len(self.alpaca_symbols),
            len(self.yahoo_only_symbols),
        )

    def fetch_latest_prices(self) -> dict[str, dict[str, Any]]:
        """
        Fetch latest prices for all symbols.

        Returns:
            Dictionary of {symbol: {price: float, volume: float, timestamp: str}}
        """
        if not HAS_YFINANCE:
            logger.warning("⚠️  yfinance not available, using fallback")
            return self._fallback_prices()

        prices = {}

        for symbol in self.symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="1d", interval="1m")

                if not hist.empty:
                    latest = hist.iloc[-1]
                    price = float(latest["Close"])
                    volume = float(latest["Volume"]) if "Volume" in latest else 0.0

                    prices[symbol] = {
                        "price": price,
                        "volume": volume,
                        "high": float(latest["High"]) if "High" in latest else price,
                        "low": float(latest["Low"]) if "Low" in latest else price,
                        "open": float(latest["Open"]) if "Open" in latest else price,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }

                    # Update history
                    self.price_history[symbol].append(price)
                    self.volume_history[symbol].append(volume)

                elif "currentPrice" in info:
                    # Fallback to info if history not available
                    price = float(info.get("currentPrice", 0))
                    prices[symbol] = {
                        "price": price,
                        "volume": 0.0,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    self.price_history[symbol].append(price)

            except Exception as e:
                logger.debug(f"Error fetching {symbol}: {e}")
                continue

        return prices

    def _fallback_prices(self) -> dict[str, dict[str, Any]]:
        """Fallback prices when yfinance is not available."""
        prices = {}
        for symbol in self.symbols:
            # Use last known price or default
            if self.price_history[symbol]:
                price = self.price_history[symbol][-1]
            else:
                price = 100.0  # Default fallback

            prices[symbol] = {
                "price": price,
                "volume": 0.0,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        return prices

    def calculate_realized_volatility(self, symbol: str, window: int = 20) -> float:
        """
        Calculate realized volatility from price history.

        Args:
            symbol: Symbol to calculate volatility for
            window: Window size for volatility calculation

        Returns:
            Annualized volatility (as decimal, e.g., 0.15 for 15%)
        """
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return 0.02  # Default 2% volatility

        prices = list(self.price_history[symbol])[-window:]

        if len(prices) < 2:
            return 0.02

        if HAS_NUMPY:
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns) * np.sqrt(252)  # Annualized
            return float(volatility)
        else:
            # Simple calculation
            returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = (variance**0.5) * (252**0.5)
            return float(volatility)

    def simulate_order_book(self, symbol: str, mid_price: float) -> dict[str, Any]:
        """
        Simulate order book for a symbol.

        Args:
            symbol: Symbol to simulate order book for
            mid_price: Mid price

        Returns:
            Simulated order book data
        """
        if not HAS_NUMPY:
            spread = 0.001  # 0.1% spread
        else:
            spread = np.random.uniform(0.0005, 0.002)  # 0.05% to 0.2% spread

        bid_price = mid_price * (1 - spread / 2)
        ask_price = mid_price * (1 + spread / 2)

        # Simulate order book levels
        bids = []
        asks = []

        for i in range(10):  # 10 levels on each side
            level_spread = (i + 1) * 0.0001  # Increasing spread per level
            bid_level_price = bid_price * (1 - level_spread)
            ask_level_price = ask_price * (1 + level_spread)

            # Random volume at each level
            if HAS_NUMPY:
                volume = np.random.uniform(100, 1000)
            else:
                import random

                volume = random.uniform(100, 1000)

            bids.append({"price": float(bid_level_price), "size": float(volume)})
            asks.append({"price": float(ask_level_price), "size": float(volume)})

        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "spread": float(spread),
            "mid_price": mid_price,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def analyze_trade_tape(self, symbol: str) -> dict[str, Any]:
        """
        Analyze trade tape for a symbol.

        Args:
            symbol: Symbol to analyze

        Returns:
            Trade tape analysis
        """
        if symbol not in self.trade_tape or len(self.trade_tape[symbol]) == 0:
            return {
                "symbol": symbol,
                "total_trades": 0,
                "avg_trade_size": 0.0,
                "buy_volume": 0.0,
                "sell_volume": 0.0,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        trades = list(self.trade_tape[symbol])

        if HAS_NUMPY:
            trade_sizes = np.array([t.get("size", 0) for t in trades])
            buy_volume = np.sum([t.get("size", 0) for t in trades if t.get("side") == "buy"])
            sell_volume = np.sum([t.get("size", 0) for t in trades if t.get("side") == "sell"])
            avg_trade_size = np.mean(trade_sizes) if len(trade_sizes) > 0 else 0.0
        else:
            trade_sizes = [t.get("size", 0) for t in trades]
            buy_volume = sum([t.get("size", 0) for t in trades if t.get("side") == "buy"])
            sell_volume = sum([t.get("size", 0) for t in trades if t.get("side") == "sell"])
            avg_trade_size = sum(trade_sizes) / len(trade_sizes) if trade_sizes else 0.0

        return {
            "symbol": symbol,
            "total_trades": len(trades),
            "avg_trade_size": float(avg_trade_size),
            "buy_volume": float(buy_volume),
            "sell_volume": float(sell_volume),
            "imbalance": float(buy_volume - sell_volume) / max(1, buy_volume + sell_volume),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def calculate_volume_profile(self, symbol: str, window: int = 100) -> dict[str, Any]:
        """
        Calculate volume profile for a symbol.

        Args:
            symbol: Symbol to analyze
            window: Window size for analysis

        Returns:
            Volume profile data
        """
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return {}

        prices = list(self.price_history[symbol])[-window:]
        volumes = list(self.volume_history[symbol])[-window:]

        if len(volumes) < len(prices):
            volumes = volumes + [0.0] * (len(prices) - len(volumes))

        if HAS_NUMPY:
            # Calculate price bins
            price_min = min(prices)
            price_max = max(prices)
            bins = 20
            bin_edges = np.linspace(price_min, price_max, bins + 1)

            # Calculate volume per bin
            volume_profile = {}
            for i in range(len(bin_edges) - 1):
                bin_prices = [p for p in prices if bin_edges[i] <= p < bin_edges[i + 1]]
                bin_volumes = [volumes[prices.index(p)] for p in bin_prices if p in prices]
                volume_profile[f"{bin_edges[i]:.2f}-{bin_edges[i + 1]:.2f}"] = float(
                    sum(bin_volumes)
                )

            # Find Point of Control (POC) - price level with highest volume
            max_volume_bin = (
                max(volume_profile.items(), key=lambda x: x[1])[0] if volume_profile else None
            )

            return {
                "symbol": symbol,
                "volume_profile": volume_profile,
                "poc": max_volume_bin,
                "total_volume": float(sum(volumes)),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        else:
            return {
                "symbol": symbol,
                "total_volume": float(sum(volumes)),
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def update_market_data(self) -> dict[str, Any]:
        """
        Update all market data for tracked symbols.

        Returns:
            Complete market data dictionary
        """
        prices = self.fetch_latest_prices()

        market_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "prices": prices,
            "volatilities": {},
            "order_books": {},
            "trade_tape_analysis": {},
            "volume_profiles": {},
        }

        # Calculate volatilities
        for symbol in self.symbols:
            if symbol in prices:
                vol = self.calculate_realized_volatility(symbol)
                market_data["volatilities"][symbol] = vol

                # Simulate order book
                price = prices[symbol]["price"]
                market_data["order_books"][symbol] = self.simulate_order_book(symbol, price)

                # Analyze trade tape
                market_data["trade_tape_analysis"][symbol] = self.analyze_trade_tape(symbol)

                # Calculate volume profile
                market_data["volume_profiles"][symbol] = self.calculate_volume_profile(symbol)

        return market_data


def main():
    """Main market data pipeline loop."""
    logger.info("🚀 Real-Time Market Data Pipeline starting...")

    # Get symbols from allocations or use defaults
    symbols = ["BTC-USD", "ETH-USD", "SPY", "QQQ", "GLD"]
    alloc_file = RUNTIME / "allocations_override.json"
    if alloc_file.exists():
        try:
            data = json.loads(alloc_file.read_text())
            symbols = list(data.get("allocations", {}).keys()) or symbols
        except Exception:
            pass

    pipeline = RealTimeMarketDataPipeline(symbols=symbols)
    update_interval = int(os.getenv("NEOLIGHT_MARKET_DATA_INTERVAL", "60"))  # Default 60 seconds

    while True:
        try:
            # Update market data
            market_data = pipeline.update_market_data()

            # Save to files
            MARKET_DATA_FILE.write_text(json.dumps(market_data, indent=2))

            # Save order books separately
            order_books = {
                symbol: market_data["order_books"][symbol]
                for symbol in symbols
                if symbol in market_data["order_books"]
            }
            ORDER_BOOK_FILE.write_text(json.dumps(order_books, indent=2))

            logger.info(f"✅ Market data updated for {len(market_data['prices'])} symbols")
            price_list = ", ".join(
                [f"{sym}: ${data['price']:.2f}" for sym, data in market_data["prices"].items()]
            )
            logger.info(f"   Prices: {price_list}")

            time.sleep(update_interval)

        except KeyboardInterrupt:
            logger.info("🛑 Real-Time Market Data Pipeline stopping...")
            break
        except Exception as e:
            logger.error(f"❌ Error in market data pipeline: {e}")
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    main()

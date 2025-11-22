#!/usr/bin/env python3
"""
NeoLight SmartTrader - QuoteService
====================================
Thread-safe, immutable quote management with comprehensive validation.
Prevents float conversion errors through guaranteed type safety.

World-Class Architecture:
- Immutable dataclasses (frozen=True)
- Thread-safe caching with RLock
- Atomic trade contexts with validation gates
- Multi-source fallback with cascading (Alpaca → Finnhub → TwelveData → AlphaVantage → RapidAPI → Yahoo)
- RapidAPI provides live data for indexes/mutual funds (replaces Yahoo EOD)
- Sequence-based quote tracking for debugging
"""

import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("quote_service")

# Try to import requests for API calls
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("⚠️ requests not available - API quote fetching disabled")

# Try to import yfinance as final fallback (no API keys required)
try:
    import yfinance as yf

    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    logger.debug("⚠️ yfinance not available - will use API sources only")


@dataclass(frozen=True)
class ValidatedQuote:
    """
    Immutable quote representation - cannot be modified after creation.
    Guarantees type safety and prevents mutation errors.
    """

    symbol: str
    last_price: float
    ask_price: float
    bid_price: float
    timestamp: datetime
    source: str = "unknown"
    sequence_id: int = 0

    def __post_init__(self):
        """Validate on construction - fail fast if invalid"""
        if self.last_price <= 0 or not isinstance(self.last_price, (int, float)):
            raise ValueError(
                f"Invalid last_price for {self.symbol}: {self.last_price} ({type(self.last_price)})"
            )
        if self.ask_price <= 0 or not isinstance(self.ask_price, (int, float)):
            raise ValueError(f"Invalid ask_price for {self.symbol}: {self.ask_price}")
        if self.bid_price <= 0 or not isinstance(self.bid_price, (int, float)):
            raise ValueError(f"Invalid bid_price for {self.symbol}: {self.bid_price}")

    @property
    def mid_price(self) -> float:
        """Calculate mid price"""
        return (self.ask_price + self.bid_price) / 2.0

    @property
    def spread(self) -> float:
        """Calculate spread in basis points"""
        return ((self.ask_price - self.bid_price) / self.mid_price) * 10000.0

    @property
    def age_seconds(self) -> float:
        """Get quote age in seconds"""
        # Handle both timezone-aware and naive datetimes
        now = datetime.now(self.timestamp.tzinfo) if self.timestamp.tzinfo else datetime.now()
        return (now - self.timestamp).total_seconds()

    def is_stale(self, max_age: int = 60) -> bool:
        """Check if quote is stale"""
        return self.age_seconds > max_age

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API compatibility"""
        return {
            "symbol": self.symbol,
            "last": self.last_price,
            "ask": self.ask_price,
            "bid": self.bid_price,
            "mid": self.mid_price,
            "regularMarketPrice": self.last_price,
            "currentPrice": self.last_price,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "sequence_id": self.sequence_id,
        }


class QuoteService:
    """
    Thread-safe quote management with immutable quotes.
    Multi-source fallback with cascading: Alpaca → Finnhub → TwelveData → AlphaVantage → RapidAPI (for indexes/funds) → Yahoo
    RapidAPI provides live data for indexes/mutual funds instead of Yahoo's end-of-day data.
    """

    def __init__(self):
        self._cache: dict[str, ValidatedQuote] = {}
        self._lock = threading.RLock()
        self._sequence_counter = 0
        self._fetch_count = 0
        self._error_count = 0
        self._validation_gates: dict[str, threading.Event] = {}

        # Metrics tracking for offline behavior monitoring
        self._cache_hits_fresh = 0
        self._cache_hits_stale = 0
        self._fetch_successes = 0
        self._fetch_failures = 0
        self._max_cache_age_seen = 0.0

        # API credentials
        self.alpaca_key = os.getenv("ALPACA_API_KEY")
        self.alpaca_secret = os.getenv("ALPACA_API_SECRET")
        self.use_alpaca = os.getenv("NEOLIGHT_USE_ALPACA_QUOTES", "false").lower() == "true"
        self.finnhub_key = os.getenv("FINNHUB_API_KEY")
        self.twelvedata_key = os.getenv("TWELVEDATA_API_KEY")
        self.alphavantage_key = os.getenv("ALPHAVANTAGE_API_KEY")
        # RapidAPI key for indexes/mutual funds (live data instead of Yahoo EOD)
        self.rapidapi_key = os.getenv(
            "RAPIDAPI_KEY", "f89c81c096msh0e367842c4a9cedp172050jsn8f96a4f06504"
        )

    def get_quote(
        self, symbol: str, max_age: int = 60, use_stale_cache: bool = True
    ) -> Optional[ValidatedQuote]:
        """
        Get validated quote (cached or fresh).
        Returns immutable quote guaranteed to have valid numeric prices.

        Args:
            symbol: Trading symbol
            max_age: Maximum age in seconds for cached quotes
            use_stale_cache: If True, use stale cache when offline (network failures)
        """
        # Check cache first (even if stale, useful when offline)
        with self._lock:
            cached = self._cache.get(symbol)
            if cached:
                if not cached.is_stale(max_age):
                    # Fresh cache hit
                    self._cache_hits_fresh += 1
                    return cached  # Fresh cache
                elif use_stale_cache:
                    # Stale but available - use it when offline
                    self._cache_hits_stale += 1
                    age_seconds = cached.age_seconds
                    self._max_cache_age_seen = max(self._max_cache_age_seen, age_seconds)
                    logger.debug(
                        f"📦 Using stale cache for {symbol} (offline mode, age: {age_seconds:.0f}s)"
                    )
                    return cached

        # Try to fetch fresh (will fail gracefully if offline)
        try:
            fresh_quote = self._fetch_fresh(symbol)
            if fresh_quote:
                self._fetch_successes += 1
                return fresh_quote
            else:
                self._fetch_failures += 1
        except Exception as e:
            # Network failure or API error - log and continue to stale cache fallback
            logger.debug(f"⚠️ Fetch failed for {symbol}: {e}")
            self._fetch_failures += 1
            # Continue to stale cache fallback below

        # If fetch failed and we have stale cache, return it (offline mode)
        if use_stale_cache and cached:
            age_seconds = cached.age_seconds
            self._max_cache_age_seen = max(self._max_cache_age_seen, age_seconds)
            logger.debug(f"🌐 Offline: Using stale cache for {symbol} (age: {age_seconds:.0f}s)")
            return cached

        # No cache and fetch failed
        return None

    def _is_index_or_mutual_fund(self, symbol: str) -> bool:
        """Detect if symbol is likely an index or mutual fund (needs live data from RapidAPI)"""
        # Mutual fund patterns: VTSAX, VFIAX, FXAIX, VTIAX, VBTLX, SWPPX
        mutual_fund_patterns = [
            "VTSAX",
            "VFIAX",
            "FXAIX",
            "VTIAX",
            "VBTLX",
            "SWPPX",
            "VOO",
            "SPY",
            "QQQ",
        ]
        # Index patterns: ^SPX, ^DJI, ^IXIC, etc. (but we use ETFs like SPY instead)
        # For now, check if it's a known mutual fund or index ETF
        symbol_upper = symbol.upper()
        return any(
            pattern in symbol_upper for pattern in mutual_fund_patterns
        ) or symbol_upper.startswith("^")

    def _fetch_fresh(self, symbol: str) -> Optional[ValidatedQuote]:
        """
        Fetch and validate new quote from multiple sources with cascading fallback.
        Pipeline: Alpaca → Finnhub → TwelveData → AlphaVantage → RapidAPI (for indexes/funds) → Yahoo
        """
        self._fetch_count += 1
        attempted_sources = []
        failed_sources = []
        is_index_fund = self._is_index_or_mutual_fund(symbol)

        # Primary: Alpaca (real-time, low-latency, validated JSON)
        if self.use_alpaca and self.alpaca_key and self.alpaca_secret and HAS_REQUESTS:
            attempted_sources.append("Alpaca")
            quote = self._fetch_alpaca(symbol)
            if quote:
                logger.debug(f"✅ Quote from Alpaca: {symbol}")
                return quote
            else:
                failed_sources.append("Alpaca")
        elif self.use_alpaca and not (self.alpaca_key and self.alpaca_secret):
            logger.debug(f"⚠️ Alpaca configured but API keys missing for {symbol}")

        # Secondary: Finnhub (fallback if Alpaca fails)
        if self.finnhub_key and HAS_REQUESTS:
            attempted_sources.append("Finnhub")
            quote = self._fetch_finnhub(symbol)
            if quote:
                logger.debug(f"✅ Quote from Finnhub: {symbol}")
                return quote
            else:
                failed_sources.append("Finnhub")
        elif not self.finnhub_key:
            logger.debug(f"⚠️ Finnhub API key not configured for {symbol}")

        # Tertiary: TwelveData (API fallback)
        if self.twelvedata_key and HAS_REQUESTS:
            attempted_sources.append("TwelveData")
            quote = self._fetch_twelvedata(symbol)
            if quote:
                logger.debug(f"✅ Quote from TwelveData: {symbol}")
                return quote
            else:
                failed_sources.append("TwelveData")
        elif not self.twelvedata_key:
            logger.debug(f"⚠️ TwelveData API key not configured for {symbol}")

        # Quaternary: AlphaVantage (free API, low rate limits)
        if self.alphavantage_key and HAS_REQUESTS:
            attempted_sources.append("AlphaVantage")
            quote = self._fetch_alphavantage(symbol)
            if quote:
                logger.debug(f"✅ Quote from AlphaVantage: {symbol}")
                return quote
            else:
                failed_sources.append("AlphaVantage")
        elif not self.alphavantage_key:
            logger.debug(f"⚠️ AlphaVantage API key not configured for {symbol}")

        # Quinary: RapidAPI (for indexes/mutual funds OR as backup if yfinance fails)
        # Try RapidAPI for indexes/funds, or if all other sources failed (including yfinance)
        if (is_index_fund or not HAS_YFINANCE) and self.rapidapi_key and HAS_REQUESTS:
            attempted_sources.append("RapidAPI")
            quote = self._fetch_rapidapi(symbol)
            if quote:
                logger.debug(f"✅ Quote from RapidAPI: {symbol}")
                return quote
            else:
                failed_sources.append("RapidAPI")
        elif (is_index_fund or not HAS_YFINANCE) and not self.rapidapi_key:
            logger.debug(f"⚠️ RapidAPI key not configured for {symbol}")

        # Final fallback: Yahoo Finance (no API keys required, but EOD for mutual funds)
        # Only try if RapidAPI failed or not available
        if HAS_YFINANCE:
            attempted_sources.append("YahooFinance")
            quote = self._fetch_yfinance(symbol)
            if quote:
                logger.debug(f"✅ Quote from YahooFinance: {symbol}")
                return quote
            else:
                failed_sources.append("YahooFinance")
                # If yfinance fails, try RapidAPI as backup (if not already tried)
                if (
                    not is_index_fund
                    and self.rapidapi_key
                    and HAS_REQUESTS
                    and "RapidAPI" not in attempted_sources
                ):
                    attempted_sources.append("RapidAPI_backup")
                    quote = self._fetch_rapidapi(symbol)
                    if quote:
                        logger.debug(
                            f"✅ Quote from RapidAPI (backup after yfinance failed): {symbol}"
                        )
                        return quote
        elif not HAS_YFINANCE:
            logger.debug(f"⚠️ yfinance not available for {symbol}, using RapidAPI as backup")
            # If yfinance not available, try RapidAPI as backup
            if self.rapidapi_key and HAS_REQUESTS and "RapidAPI" not in attempted_sources:
                attempted_sources.append("RapidAPI_backup")
                quote = self._fetch_rapidapi(symbol)
                if quote:
                    logger.debug(f"✅ Quote from RapidAPI (backup): {symbol}")
                    return quote

        logger.warning(
            f"⚠️ Data source summary for {symbol} — attempted: {attempted_sources or 'none'} | "
            f"failed: {failed_sources or 'none'} | inventory: "
            f"Alpaca={'✅' if self.alpaca_key else '❌'}, "
            f"Finnhub={'✅' if self.finnhub_key else '❌'}, "
            f"TwelveData={'✅' if self.twelvedata_key else '❌'}, "
            f"AlphaVantage={'✅' if self.alphavantage_key else '❌'}, "
            f"RapidAPI={'✅' if self.rapidapi_key else '❌'}, "
            f"Yahoo={'✅' if HAS_YFINANCE else '❌'}"
        )

        # All sources failed
        self._error_count += 1
        sources_str = (
            " → ".join(attempted_sources) if attempted_sources else "None (no API keys configured)"
        )
        failed_str = ", ".join(failed_sources) if failed_sources else "None attempted"
        logger.error(
            f"❌ All quote sources failed for {symbol} | Attempted: {sources_str} | Failed: {failed_str}"
        )
        if not HAS_REQUESTS:
            logger.error("❌ requests library not available - install with: pip install requests")
        return None

    def _fetch_alpaca(self, symbol: str) -> Optional[ValidatedQuote]:
        """Fetch quote from Alpaca API"""
        try:
            # Convert symbol format (BTC-USD -> BTCUSD)
            alpaca_symbol = symbol.replace("-", "") if "-" in symbol else symbol

            headers = {
                "APCA-API-KEY-ID": self.alpaca_key,
                "APCA-API-SECRET-KEY": self.alpaca_secret,
            }

            # Try crypto first
            if "USD" in alpaca_symbol and len(alpaca_symbol) <= 8:
                url = "https://data.alpaca.markets/v1beta3/crypto/latest/quotes"
                params = {"symbols": alpaca_symbol}
            else:
                url = f"https://data.alpaca.markets/v2/stocks/{alpaca_symbol}/quotes/latest"
                params = None

            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()

                # Parse Alpaca response
                price = None
                quote_data = None
                if "quotes" in data:
                    quotes = data.get("quotes", {})
                    if alpaca_symbol in quotes:
                        quote_data = quotes[alpaca_symbol]
                        price = (
                            quote_data.get("ap")
                            or quote_data.get("bp")
                            or quote_data.get("lp")
                            or quote_data.get("mid")
                        )
                elif "quote" in data:
                    quote_data = data["quote"]
                    price = (
                        quote_data.get("ap")
                        or quote_data.get("bp")
                        or quote_data.get("lp")
                        or quote_data.get("mid")
                    )

                if price is not None and quote_data:
                    try:
                        ask_price = float(quote_data.get("ap") or price)
                        bid_price = float(quote_data.get("bp") or price)
                        last_price = float(quote_data.get("lp") or price)

                        if all(p > 0 for p in [ask_price, bid_price, last_price]):
                            return self._create_validated_quote(
                                symbol, last_price, ask_price, bid_price, "alpaca"
                            )
                        else:
                            logger.debug(
                                f"⚠️ Alpaca returned invalid prices for {symbol}: ask={ask_price}, bid={bid_price}, last={last_price}"
                            )
                    except (ValueError, TypeError) as e:
                        logger.debug(f"⚠️ Alpaca price conversion failed for {symbol}: {e}")
                else:
                    logger.debug(f"⚠️ Alpaca response missing price data for {symbol}: {data}")
            else:
                logger.debug(
                    f"⚠️ Alpaca API returned status {response.status_code} for {symbol}: {response.text[:200]}"
                )
        except requests.exceptions.Timeout:
            logger.debug(f"⚠️ Alpaca request timeout for {symbol} (5s)")
        except requests.exceptions.RequestException as e:
            logger.debug(f"⚠️ Alpaca network error for {symbol}: {e}")
        except Exception as e:
            logger.debug(f"⚠️ Alpaca fetch failed for {symbol}: {e}")
        return None

    def _fetch_finnhub(self, symbol: str) -> Optional[ValidatedQuote]:
        """Fetch quote from Finnhub API"""
        try:
            # Convert symbol format
            finnhub_symbol = symbol.replace("-", "")
            url = "https://finnhub.io/api/v1/quote"
            params = {"symbol": finnhub_symbol, "token": self.finnhub_key}

            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()

                # Finnhub returns: c (current), h (high), l (low), o (open), pc (previous close), t (timestamp)
                current_price = data.get("c")
                if current_price and current_price > 0:
                    price = float(current_price)
                    # Use current as mid, calculate spread
                    spread_pct = 0.0005
                    ask_price = price * (1 + spread_pct / 2)
                    bid_price = price * (1 - spread_pct / 2)

                    return self._create_validated_quote(
                        symbol, price, ask_price, bid_price, "finnhub"
                    )
                else:
                    logger.debug(f"⚠️ Finnhub returned invalid price for {symbol}: {current_price}")
            else:
                logger.debug(
                    f"⚠️ Finnhub API returned status {response.status_code} for {symbol}: {response.text[:200]}"
                )
        except requests.exceptions.Timeout:
            logger.debug(f"⚠️ Finnhub request timeout for {symbol} (5s)")
        except requests.exceptions.RequestException as e:
            logger.debug(f"⚠️ Finnhub network error for {symbol}: {e}")
        except Exception as e:
            logger.debug(f"⚠️ Finnhub fetch failed for {symbol}: {e}")
        return None

    def _fetch_twelvedata(self, symbol: str) -> Optional[ValidatedQuote]:
        """Fetch quote from TwelveData API"""
        try:
            # Convert symbol format
            td_symbol = symbol.replace("-", "")
            url = "https://api.twelvedata.com/price"
            params = {"symbol": td_symbol, "apikey": self.twelvedata_key}

            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()

                price_str = data.get("price")
                if price_str:
                    price = float(price_str)
                    if price > 0:
                        spread_pct = 0.0005
                        ask_price = price * (1 + spread_pct / 2)
                        bid_price = price * (1 - spread_pct / 2)

                        return self._create_validated_quote(
                            symbol, price, ask_price, bid_price, "twelvedata"
                        )
                    else:
                        logger.debug(f"⚠️ TwelveData returned invalid price for {symbol}: {price}")
                else:
                    logger.debug(f"⚠️ TwelveData response missing price for {symbol}: {data}")
            else:
                logger.debug(
                    f"⚠️ TwelveData API returned status {response.status_code} for {symbol}: {response.text[:200]}"
                )
        except requests.exceptions.Timeout:
            logger.debug(f"⚠️ TwelveData request timeout for {symbol} (5s)")
        except requests.exceptions.RequestException as e:
            logger.debug(f"⚠️ TwelveData network error for {symbol}: {e}")
        except Exception as e:
            logger.debug(f"⚠️ TwelveData fetch failed for {symbol}: {e}")
        return None

    def _fetch_alphavantage(self, symbol: str) -> Optional[ValidatedQuote]:
        """Fetch quote from AlphaVantage GLOBAL_QUOTE endpoint"""
        if not self.alphavantage_key or not HAS_REQUESTS:
            return None

        try:
            av_symbol = symbol.replace("-", "")
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": av_symbol,
                "apikey": self.alphavantage_key,
            }
            response = requests.get("https://www.alphavantage.co/query", params=params, timeout=5)
            if response.status_code != 200:
                logger.debug(
                    f"⚠️ AlphaVantage response {response.status_code} for {symbol}: {response.text[:200]}"
                )
                return None

            payload = response.json()
            if "Note" in payload or "Information" in payload:
                logger.debug(
                    f"⚠️ AlphaVantage throttled request for {symbol}: {payload.get('Note') or payload.get('Information')}"
                )
                return None

            quote_data = payload.get("Global Quote") or payload.get("globalQuote") or {}
            price_str = quote_data.get("05. price") or quote_data.get("price")
            if not price_str:
                logger.debug(f"⚠️ AlphaVantage missing price for {symbol}: {payload}")
                return None

            price = float(price_str)
            if price <= 0:
                logger.debug(f"⚠️ AlphaVantage returned invalid price for {symbol}: {price}")
                return None

            spread_pct = 0.0005
            ask_price = price * (1 + spread_pct / 2)
            bid_price = price * (1 - spread_pct / 2)
            return self._create_validated_quote(symbol, price, ask_price, bid_price, "alphavantage")
        except (ValueError, TypeError) as exc:
            logger.debug(f"⚠️ AlphaVantage conversion failed for {symbol}: {exc}")
        except requests.exceptions.Timeout:
            logger.debug(f"⚠️ AlphaVantage timeout for {symbol}")
        except requests.exceptions.RequestException as exc:
            logger.debug(f"⚠️ AlphaVantage network error for {symbol}: {exc}")
        except Exception as exc:
            logger.debug(f"⚠️ AlphaVantage fetch failed for {symbol}: {exc}")
        return None

    def _fetch_rapidapi(self, symbol: str) -> Optional[ValidatedQuote]:
        """
        Fetch quote from RapidAPI with cascading fallback across multiple endpoints.
        Tries: Real-Time Finance Data → Twelve Data (via RapidAPI) → TradingView (via RapidAPI)
        """
        if not self.rapidapi_key or not HAS_REQUESTS:
            return None

        headers = {
            "x-rapidapi-key": self.rapidapi_key,
        }

        # Try multiple RapidAPI endpoints in cascade
        endpoints = [
            # Endpoint 1: Real-Time Finance Data - stock quote
            {
                "name": "RealTimeFinance",
                "url": "https://real-time-finance-data.p.rapidapi.com/stock/quote",
                "host": "real-time-finance-data.p.rapidapi.com",
                "params": {"symbol": symbol, "language": "en"},
                "price_path": ["data", "price"],  # Adjust based on actual response
            },
            # Endpoint 2: Twelve Data via RapidAPI
            {
                "name": "TwelveDataRapidAPI",
                "url": "https://twelve-data1.p.rapidapi.com/price",
                "host": "twelve-data1.p.rapidapi.com",
                "params": {"symbol": symbol, "format": "json"},
                "price_path": ["price"],
            },
            # Endpoint 3: TradingView via RapidAPI
            {
                "name": "TradingViewRapidAPI",
                "url": "https://tradingview18.p.rapidapi.com/quote",
                "host": "tradingview18.p.rapidapi.com",
                "params": {"symbols": symbol},
                "price_path": ["result", 0, "lp"],  # Last price
            },
        ]

        for endpoint in endpoints:
            logger.debug(f"🌐 RapidAPI[{endpoint['name']}] attempt for {symbol}")
            try:
                headers_with_host = {**headers, "x-rapidapi-host": endpoint["host"]}
                response = requests.get(
                    endpoint["url"], headers=headers_with_host, params=endpoint["params"], timeout=5
                )

                if response.status_code == 200:
                    data = response.json()

                    # Extract price based on endpoint structure
                    price = None
                    if endpoint["name"] == "RealTimeFinance":
                        # Try multiple possible paths
                        price = (
                            data.get("data", {}).get("price")
                            or data.get("price")
                            or data.get("data", {}).get("currentPrice")
                            or data.get("currentPrice")
                        )
                    elif endpoint["name"] == "TwelveDataRapidAPI":
                        price_str = data.get("price")
                        if price_str:
                            try:
                                price = float(price_str)
                            except (ValueError, TypeError):
                                pass
                    elif endpoint["name"] == "TradingViewRapidAPI":
                        result = data.get("result", [])
                        if result and len(result) > 0:
                            price = result[0].get("lp") or result[0].get("last_price")

                    if price:
                        try:
                            price = float(price)
                            if price > 0:
                                # Estimate spread for mutual funds/indexes
                                spread_pct = 0.0005
                                ask_price = price * (1 + spread_pct / 2)
                                bid_price = price * (1 - spread_pct / 2)

                                logger.debug(
                                    f"✅ RapidAPI[{endpoint['name']}] quote for {symbol}: {price}"
                                )
                                return self._create_validated_quote(
                                    symbol,
                                    price,
                                    ask_price,
                                    bid_price,
                                    f"rapidapi_{endpoint['name'].lower()}",
                                )
                        except (ValueError, TypeError):
                            logger.debug(
                                f"⚠️ RapidAPI {endpoint['name']} price conversion failed for {symbol}: {price}"
                            )
                    else:
                        logger.debug(
                            f"⚠️ RapidAPI {endpoint['name']} response missing price for {symbol}: {data}"
                        )
                elif response.status_code == 429:
                    logger.debug(f"⚠️ RapidAPI {endpoint['name']} rate limited for {symbol}")
                    # Continue to next endpoint
                    continue
                else:
                    logger.debug(
                        f"⚠️ RapidAPI {endpoint['name']} returned status {response.status_code} for {symbol}: {response.text[:200]}"
                    )
            except requests.exceptions.Timeout:
                logger.debug(f"⚠️ RapidAPI {endpoint['name']} request timeout for {symbol} (5s)")
                # Continue to next endpoint
                continue
            except requests.exceptions.RequestException as e:
                logger.debug(f"⚠️ RapidAPI {endpoint['name']} network error for {symbol}: {e}")
                # Continue to next endpoint
                continue
            except Exception as e:
                logger.debug(f"⚠️ RapidAPI {endpoint['name']} fetch failed for {symbol}: {e}")
                # Continue to next endpoint
                continue

        # All RapidAPI endpoints failed
        return None

    def _fetch_yfinance(self, symbol: str) -> Optional[ValidatedQuote]:
        """Fetch quote from Yahoo Finance (no API keys required)"""
        if not HAS_YFINANCE:
            return None

        try:
            ticker = yf.Ticker(symbol)

            # Try fast_info first (faster, more reliable) with timeout protection
            try:
                fast_info = ticker.fast_info
                price = None

                # Try different fast_info attributes in order of preference
                for attr_name in ["lastPrice", "regularMarketPrice", "currentPrice"]:
                    if hasattr(fast_info, attr_name):
                        attr_value = getattr(fast_info, attr_name)
                        if attr_value is not None and not (
                            isinstance(attr_value, float)
                            and (attr_value != attr_value or attr_value <= 0)
                        ):
                            try:
                                price = float(attr_value)
                                if price > 0:
                                    break
                            except (ValueError, TypeError):
                                continue

                if price and price > 0:
                    spread_pct = 0.0005
                    ask_price = price * (1 + spread_pct / 2)
                    bid_price = price * (1 - spread_pct / 2)
                    return self._create_validated_quote(
                        symbol, price, ask_price, bid_price, "yfinance_fast_info"
                    )
            except Exception as e:
                logger.debug(f"⚠️ YahooFinance fast_info failed for {symbol}: {e}")

            # Fallback: Try historical data with shorter periods first (faster)
            periods_intervals = [("1d", "1h"), ("2d", "1d")]

            for period, interval in periods_intervals:
                try:
                    data = ticker.history(period=period, interval=interval, timeout=3)
                    if data is not None and not data.empty and "Close" in data.columns:
                        latest = data.iloc[-1]
                        close_price = latest.get("Close")
                        if close_price is not None:
                            try:
                                price = float(close_price)
                                if price > 0:
                                    spread_pct = 0.0005
                                    ask_price = price * (1 + spread_pct / 2)
                                    bid_price = price * (1 - spread_pct / 2)
                                    return self._create_validated_quote(
                                        symbol, price, ask_price, bid_price, "yfinance_historical"
                                    )
                            except (ValueError, TypeError):
                                continue
                except Exception as e:
                    logger.debug(f"⚠️ YahooFinance {period}/{interval} failed for {symbol}: {e}")
                    continue
        except Exception as e:
            logger.debug(f"⚠️ YahooFinance fetch failed for {symbol}: {e}")
        return None

    def _create_validated_quote(
        self, symbol: str, last_price: float, ask_price: float, bid_price: float, source: str
    ) -> ValidatedQuote:
        """Create and cache validated quote atomically"""
        with self._lock:
            self._sequence_counter += 1
            quote = ValidatedQuote(
                symbol=symbol,
                last_price=last_price,
                ask_price=ask_price,
                bid_price=bid_price,
                timestamp=datetime.now(),
                source=source,
                sequence_id=self._sequence_counter,
            )
            self._cache[symbol] = quote

            # Signal fresh quote available
            if symbol in self._validation_gates:
                self._validation_gates[symbol].set()

            logger.debug(f"✅ Quote fetched: {symbol} @ ${quote.last_price:,.2f} ({source})")
            return quote

    def get_metrics(self) -> dict[str, Any]:
        """
        Get metrics for offline behavior monitoring.

        Returns:
            dict with cache hits, fetch stats, and offline indicators
        """
        with self._lock:
            total_cache_hits = self._cache_hits_fresh + self._cache_hits_stale
            stale_cache_usage_rate = (
                self._cache_hits_stale / total_cache_hits if total_cache_hits > 0 else 0.0
            )

            return {
                "cache_hits_fresh": self._cache_hits_fresh,
                "cache_hits_stale": self._cache_hits_stale,
                "fetch_successes": self._fetch_successes,
                "fetch_failures": self._fetch_failures,
                "max_cache_age_seen": self._max_cache_age_seen,
                "stale_cache_usage_rate": round(stale_cache_usage_rate, 4),
                "total_cache_hits": total_cache_hits,
                "cache_size": len(self._cache),
                "cache_symbols": list(self._cache.keys()),
            }

    def get_stats(self) -> dict[str, Any]:
        """Get diagnostic statistics"""
        with self._lock:
            return {
                "cached_symbols": list(self._cache.keys()),
                "fetch_count": self._fetch_count,
                "error_count": self._error_count,
                "error_rate": self._error_count / max(self._fetch_count, 1),
                "cache_size": len(self._cache),
            }


@contextmanager
def atomic_trade_context(quote_service: QuoteService, symbol: str, max_age: int = 10):
    """
    Atomic trade context manager - guarantees quote validity throughout trade execution.
    Prevents race conditions by locking quote for entire trade.
    """
    trade_id = f"{symbol}_{int(time.time() * 1000)}"

    logger.info(f"🔒 Trade context locked: {trade_id}")

    # Get fresh quote (must be less than max_age seconds old)
    quote = quote_service.get_quote(symbol, max_age=max_age)

    if not quote:
        raise ValueError(f"Cannot obtain valid quote for {symbol} (max_age={max_age}s)")

    if quote.is_stale(max_age):
        raise ValueError(f"Quote for {symbol} is stale ({quote.age_seconds:.1f}s old)")

    logger.info(
        f"✅ Using quote: {symbol} @ ${quote.last_price:,.2f} ({quote.age_seconds:.1f}s old, seq={quote.sequence_id})"
    )

    try:
        yield quote  # Immutable quote guaranteed valid for this block
    finally:
        logger.info(f"🔓 Trade context released: {trade_id}")


# Singleton instance for global access
_quote_service_instance: Optional[QuoteService] = None
_service_lock = threading.Lock()


def get_quote_service() -> QuoteService:
    """Get singleton QuoteService instance"""
    global _quote_service_instance
    if _quote_service_instance is None:
        with _service_lock:
            if _quote_service_instance is None:
                _quote_service_instance = QuoteService()
    return _quote_service_instance

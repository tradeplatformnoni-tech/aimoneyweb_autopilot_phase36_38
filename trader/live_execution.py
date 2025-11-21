#!/usr/bin/env python3
"""
NeoLight Live Trading Execution - Phase 2900–3100
=================================================
World-class live order execution with Alpaca API integration.
Includes safety controls, circuit breakers, and Telegram notifications.
"""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️  Install requests: pip install requests")

# Setup paths
ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

# Setup logging
LOG_FILE = LOGS / "live_execution.log"
logger = logging.getLogger("live_execution")
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


class LiveExecutionEngine:
    """
    World-class live trading execution engine with safety controls.
    Uses Alpaca API for order submission.
    """

    def __init__(self, use_paper: bool = True):
        """
        Initialize live execution engine.

        Args:
            use_paper: If True, use paper trading API (default). Set False for live.
        """
        self.use_paper = use_paper
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")

        if use_paper:
            self.base_url = "https://paper-api.alpaca.markets/v2"
        else:
            self.base_url = "https://api.alpaca.markets/v2"

        if not self.api_key or not self.secret_key:
            logger.warning("⚠️  Alpaca API keys not found in environment")
            logger.warning("   Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables")
        else:
            logger.info(f"✅ LiveExecutionEngine initialized ({'PAPER' if use_paper else 'LIVE'})")

        self.headers = {
            "APCA-API-KEY-ID": self.api_key or "",
            "APCA-API-SECRET-KEY": self.secret_key or "",
        }

        # Circuit breaker state
        self.circuit_breaker_file = STATE / "circuit_breaker.json"
        self.daily_loss_limit = float(os.getenv("DAILY_LOSS_LIMIT", "0.05"))  # 5% daily loss limit
        self.max_daily_trades = int(os.getenv("MAX_DAILY_TRADES", "50"))
        self.daily_trade_count = 0
        self.last_reset_date = datetime.now().date()

        # Load circuit breaker state
        self._load_circuit_breaker_state()

    def _load_circuit_breaker_state(self):
        """Load circuit breaker state from file."""
        if self.circuit_breaker_file.exists():
            try:
                data = json.loads(self.circuit_breaker_file.read_text())
                self.daily_trade_count = data.get("daily_trade_count", 0)
                last_reset = data.get("last_reset_date")
                if last_reset:
                    self.last_reset_date = datetime.fromisoformat(last_reset).date()
            except Exception as e:
                logger.warning(f"⚠️  Error loading circuit breaker state: {e}")

    def _save_circuit_breaker_state(self):
        """Save circuit breaker state to file."""
        try:
            data = {
                "daily_trade_count": self.daily_trade_count,
                "last_reset_date": self.last_reset_date.isoformat(),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            self.circuit_breaker_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"❌ Error saving circuit breaker state: {e}")

    def _check_circuit_breaker(self) -> tuple[bool, str]:
        """
        Check if circuit breaker should halt trading.

        Returns:
            (is_halted, reason)
        """
        # Reset daily counters if new day
        today = datetime.now().date()
        if today > self.last_reset_date:
            self.daily_trade_count = 0
            self.last_reset_date = today
            self._save_circuit_breaker_state()

        # Check daily trade limit
        if self.daily_trade_count >= self.max_daily_trades:
            return True, f"Daily trade limit reached ({self.max_daily_trades})"

        # Check daily drawdown limit
        try:
            equity_file = STATE / "equity_curve.json"
            if equity_file.exists():
                data = json.loads(equity_file.read_text())
                if "daily_pnl" in data:
                    daily_pnl = float(data["daily_pnl"])
                    if daily_pnl < -self.daily_loss_limit:
                        return True, f"Daily loss limit exceeded ({daily_pnl:.2%})"
        except Exception as e:
            logger.debug(f"Could not check daily drawdown: {e}")

        # Check for manual halt
        halt_file = RUNTIME / "drawdown_state.json"
        if halt_file.exists():
            try:
                data = json.loads(halt_file.read_text())
                if data.get("halt", False):
                    return True, "Manual halt activated"
            except:
                pass

        return False, ""

    def _send_telegram_notification(self, message: str):
        """Send Telegram notification about trade execution."""
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")

            if not token or not chat_id:
                return

            import urllib.parse
            import urllib.request

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}

            req = urllib.request.Request(
                url, data=urllib.parse.urlencode(data).encode(), method="POST"
            )

            with urllib.request.urlopen(req, timeout=5) as response:
                pass  # Notification sent

        except Exception as e:
            logger.debug(f"Could not send Telegram notification: {e}")

    def execute_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        time_in_force: str = "gtc",
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict[str, Any]:
        """
        Execute live order via Alpaca API.

        Args:
            symbol: Trading symbol (e.g., "BTCUSD", "AAPL")
            qty: Quantity to trade
            side: "buy" or "sell"
            order_type: "market", "limit", "stop", "stop_limit"
            time_in_force: "gtc", "ioc", "fok", "day"
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price

        Returns:
            Dictionary with order result
        """
        if not HAS_REQUESTS:
            return {"status": "error", "message": "requests library not available"}

        if not self.api_key or not self.secret_key:
            return {"status": "error", "message": "Alpaca API keys not configured"}

        # Check circuit breaker
        is_halted, reason = self._check_circuit_breaker()
        if is_halted:
            logger.warning(f"🛑 Circuit breaker active: {reason}")
            return {"status": "halted", "reason": reason}

        # Convert symbol format if needed (BTC-USD -> BTCUSD for Alpaca)
        alpaca_symbol = symbol.replace("-", "") if "-" in symbol else symbol

        # Prepare order data
        url = f"{self.base_url}/orders"
        order_data = {
            "symbol": alpaca_symbol,
            "qty": str(qty),
            "side": side.lower(),
            "type": order_type.lower(),
            "time_in_force": time_in_force.lower(),
        }

        # Add optional fields
        if stop_loss:
            order_data["stop_loss"] = str(stop_loss)
        if take_profit:
            order_data["take_profit"] = str(take_profit)

        try:
            # Submit order
            response = requests.post(url, json=order_data, headers=self.headers, timeout=10)

            if response.status_code == 200:
                order_result = response.json()

                # Increment daily trade count
                self.daily_trade_count += 1
                self._save_circuit_breaker_state()

                # Log success
                logger.info(f"✅ LIVE {side.upper()} executed: {symbol} x {qty} @ {order_type}")

                # Send Telegram notification
                mode = "PAPER" if self.use_paper else "LIVE"
                telegram_msg = (
                    f"🚀 {mode} TRADE EXECUTED\n"
                    f"{symbol} {side.upper()} x {qty}\n"
                    f"Type: {order_type.upper()}\n"
                    f"Order ID: {order_result.get('id', 'N/A')}"
                )
                self._send_telegram_notification(telegram_msg)

                return {
                    "status": "success",
                    "order_id": order_result.get("id"),
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "order_type": order_type,
                    "result": order_result,
                }
            else:
                error_msg = f"Order failed: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")

                # Send Telegram alert
                self._send_telegram_notification(f"❌ LIVE TRADE FAILED\n{error_msg}")

                return {
                    "status": "error",
                    "message": error_msg,
                    "status_code": response.status_code,
                }

        except Exception as e:
            error_msg = f"Exception executing order: {e}"
            logger.error(f"❌ {error_msg}")
            import traceback

            traceback.print_exc()

            return {"status": "error", "message": error_msg}

    def get_account_info(self) -> dict[str, Any]:
        """Get account information from Alpaca."""
        if not HAS_REQUESTS or not self.api_key:
            return {"status": "error", "message": "API not configured"}

        try:
            url = f"{self.base_url}/account"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                account = response.json()
                return {
                    "status": "success",
                    "account": account,
                    "equity": float(account.get("equity", 0)),
                    "cash": float(account.get("cash", 0)),
                    "buying_power": float(account.get("buying_power", 0)),
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get account: {response.status_code}",
                }
        except Exception as e:
            logger.error(f"❌ Error getting account info: {e}")
            return {"status": "error", "message": str(e)}

    def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions from Alpaca."""
        if not HAS_REQUESTS or not self.api_key:
            return []

        try:
            url = f"{self.base_url}/positions"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                positions = response.json()
                return positions
            else:
                logger.warning(f"⚠️  Failed to get positions: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ Error getting positions: {e}")
            return []


# Example usage
if __name__ == "__main__":
    logger.info("🧪 Testing Live Execution Engine...")

    engine = LiveExecutionEngine(use_paper=True)

    # Check account info
    account = engine.get_account_info()
    if account.get("status") == "success":
        print("\n✅ Account Info:")
        print(f"  Equity: ${account['equity']:,.2f}")
        print(f"  Cash: ${account['cash']:,.2f}")
        print(f"  Buying Power: ${account['buying_power']:,.2f}")

    # Get positions
    positions = engine.get_positions()
    print(f"\n✅ Current Positions: {len(positions)}")

    # Note: Uncomment to test actual order (use with caution!)
    # result = engine.execute_order("BTCUSD", 0.001, "buy", "market")
    # print(f"\n✅ Order Result: {result}")

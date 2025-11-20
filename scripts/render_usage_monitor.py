#!/usr/bin/env python3
"""
Render Usage Monitor - Proactive Failover System
================================================
Tracks Render free tier usage (750 hours/month) and triggers
automatic failover to Google Cloud Run before hitting limits.

World-Class Features:
- Real-time usage tracking via Render API
- Proactive threshold alerts (700h warning, 720h switch)
- Automatic failover orchestration
- Monthly reset detection
- Comprehensive logging and metrics
"""

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

# Configuration
ROOT = Path(__file__).parent.parent
LOG_DIR = ROOT / "logs"
RUN_DIR = ROOT / "run"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RUN_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "render_usage_monitor.log"
STATUS_FILE = RUN_DIR / "render_usage_status.json"
CONFIG_FILE = RUN_DIR / "render_monitor_config.json"

# Render API Configuration
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "")
RENDER_API_BASE = "https://api.render.com/v1"

# Thresholds
WARNING_THRESHOLD = 700  # Hours - send alert
SWITCH_THRESHOLD = 720  # Hours - trigger failover
FREE_TIER_LIMIT = 750  # Hours - Render free tier limit

# Monitoring interval (check every hour)
CHECK_INTERVAL = 3600  # 1 hour

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("render_usage_monitor")


class RenderUsageMonitor:
    """Monitor Render service usage and manage proactive failover"""
    
    def __init__(self):
        self.api_key = RENDER_API_KEY
        self.service_id = RENDER_SERVICE_ID
        self.current_month = datetime.now(UTC).strftime("%Y-%m")
        self.load_state()
        
    def load_state(self):
        """Load previous state from disk"""
        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE) as f:
                    self.state = json.load(f)
                # Check if month has changed
                if self.state.get("month") != self.current_month:
                    logger.info(f"Month changed: {self.state.get('month')} -> {self.current_month}, resetting usage")
                    self.state = {
                        "month": self.current_month,
                        "hours_used": 0,
                        "last_check": None,
                        "last_switch": None,
                        "switches_this_month": 0,
                        "current_provider": "render"
                    }
            except Exception as e:
                logger.warning(f"Failed to load state: {e}, starting fresh")
                self.state = {
                    "month": self.current_month,
                    "hours_used": 0,
                    "last_check": None,
                    "last_switch": None,
                    "switches_this_month": 0,
                    "current_provider": "render"
                }
        else:
            self.state = {
                "month": self.current_month,
                "hours_used": 0,
                "last_check": None,
                "last_switch": None,
                "switches_this_month": 0,
                "current_provider": "render"
            }
        self.save_state()
    
    def save_state(self):
        """Save state to disk"""
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def get_render_headers(self) -> dict[str, str]:
        """Get Render API headers"""
        if not self.api_key:
            raise ValueError("RENDER_API_KEY not set")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def fetch_render_usage(self) -> dict[str, Any] | None:
        """Fetch current usage from Render API"""
        if not self.api_key or not self.service_id:
            logger.warning("Render API credentials not configured, using estimated usage")
            return None
        
        try:
            # Render API endpoint for service metrics
            url = f"{RENDER_API_BASE}/services/{self.service_id}/metrics"
            response = requests.get(url, headers=self.get_render_headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Render usage: {e}")
            return None
    
    def estimate_usage(self) -> float:
        """Estimate usage based on uptime tracking"""
        # If we have last check time, estimate hours since then
        if self.state.get("last_check"):
            try:
                last_check = datetime.fromisoformat(self.state["last_check"].replace("Z", "+00:00"))
                now = datetime.now(UTC)
                hours_since = (now - last_check).total_seconds() / 3600
                # Add to existing usage
                estimated = self.state.get("hours_used", 0) + hours_since
                return min(estimated, FREE_TIER_LIMIT)  # Cap at limit
            except Exception as e:
                logger.warning(f"Failed to estimate usage: {e}")
        
        return self.state.get("hours_used", 0)
    
    def get_current_usage(self) -> float:
        """Get current usage hours (from API or estimation)"""
        usage_data = self.fetch_render_usage()
        
        if usage_data:
            # Parse usage from Render API response
            # Note: Render API structure may vary, adjust as needed
            hours = usage_data.get("hours_used", 0) or self.estimate_usage()
        else:
            hours = self.estimate_usage()
        
        return hours
    
    def check_thresholds(self, hours_used: float) -> str:
        """Check if usage exceeds thresholds"""
        if hours_used >= SWITCH_THRESHOLD:
            return "switch"  # Trigger failover
        elif hours_used >= WARNING_THRESHOLD:
            return "warning"  # Send alert
        else:
            return "ok"  # Within limits
    
    def trigger_failover(self):
        """Trigger automatic failover to Google Cloud Run"""
        logger.warning(f"⚠️ Usage threshold reached ({self.state['hours_used']:.1f}h), triggering failover to Cloud Run")
        
        try:
            # Call auto-switch script
            import subprocess
            script_path = ROOT / "scripts" / "auto_failover_switch.sh"
            if script_path.exists():
                result = subprocess.run(
                    ["bash", str(script_path), "render_to_cloudrun"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode == 0:
                    logger.info("✅ Failover to Cloud Run successful")
                    self.state["last_switch"] = datetime.now(UTC).isoformat()
                    self.state["switches_this_month"] = self.state.get("switches_this_month", 0) + 1
                    self.state["current_provider"] = "cloudrun"
                    self.save_state()
                    return True
                else:
                    logger.error(f"❌ Failover script failed: {result.stderr}")
                    return False
            else:
                logger.error(f"❌ Failover script not found: {script_path}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to trigger failover: {e}")
            return False
    
    def send_alert(self, message: str, level: str = "warning"):
        """Send alert notification (Telegram, etc.)"""
        # Check for Telegram credentials
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        if telegram_token and telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                payload = {
                    "chat_id": telegram_chat_id,
                    "text": f"🚨 Render Usage Alert: {message}",
                    "parse_mode": "HTML"
                }
                requests.post(url, json=payload, timeout=5)
            except Exception as e:
                logger.warning(f"Failed to send Telegram alert: {e}")
        
        logger.warning(f"ALERT: {message}")
    
    def run_check(self):
        """Run a single usage check"""
        # Check if month changed
        if self.state.get("month") != self.current_month:
            logger.info(f"📅 Month changed, resetting usage tracking")
            self.state["month"] = self.current_month
            self.state["hours_used"] = 0
            self.state["switches_this_month"] = 0
            self.state["current_provider"] = "render"
        
        # Get current usage
        hours_used = self.get_current_usage()
        self.state["hours_used"] = hours_used
        self.state["last_check"] = datetime.now(UTC).isoformat()
        
        # Check thresholds
        status = self.check_thresholds(hours_used)
        hours_remaining = FREE_TIER_LIMIT - hours_used
        
        logger.info(f"📊 Render Usage: {hours_used:.1f}h / {FREE_TIER_LIMIT}h ({hours_remaining:.1f}h remaining)")
        
        if status == "switch":
            self.send_alert(
                f"Usage at {hours_used:.1f}h, triggering failover to Cloud Run",
                "critical"
            )
            self.trigger_failover()
        elif status == "warning":
            self.send_alert(
                f"Usage at {hours_used:.1f}h ({hours_remaining:.1f}h remaining). Will switch at {SWITCH_THRESHOLD}h",
                "warning"
            )
        
        self.save_state()
        return status
    
    def run_continuous(self):
        """Run continuous monitoring loop"""
        logger.info("🚀 Render Usage Monitor starting (continuous mode)")
        logger.info(f"   Service ID: {self.service_id or 'Not configured'}")
        logger.info(f"   Warning threshold: {WARNING_THRESHOLD}h")
        logger.info(f"   Switch threshold: {SWITCH_THRESHOLD}h")
        logger.info(f"   Free tier limit: {FREE_TIER_LIMIT}h")
        logger.info(f"   Check interval: {CHECK_INTERVAL}s")
        
        while True:
            try:
                self.run_check()
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                logger.info("🛑 Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}", exc_info=True)
                time.sleep(60)  # Wait 1 minute before retry


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Single check mode
        monitor = RenderUsageMonitor()
        monitor.run_check()
    else:
        # Continuous mode
        monitor = RenderUsageMonitor()
        monitor.run_continuous()


if __name__ == "__main__":
    main()



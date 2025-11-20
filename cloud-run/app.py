#!/usr/bin/env python3
"""
NeoLight Cloud Run Supervisor - Hybrid Production Edition
==========================================================
Combines Claude's security + Auto's reliability
- API key authentication (Claude)
- Circuit breaker pattern (Claude)
- Multi-endpoint health checks (Auto)
- Process output streaming (Auto)
- Graceful shutdown (Both)
"""

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# ── Configuration ───────────────────────────────────────────────────
APP_ROOT = Path("/app")
STATE_DIR = APP_ROOT / "state"
RUNTIME_DIR = APP_ROOT / "runtime"
LOG_DIR = APP_ROOT / "logs"
RUN_LOG = LOG_DIR / "cloud_run_supervisor.log"

for d in [STATE_DIR, RUNTIME_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Security Configuration (Claude's) ──────────────────────────────
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
EXPECTED_API_KEY = os.getenv("CLOUD_RUN_API_KEY", "")

# ── Circuit Breaker (Claude's) ─────────────────────────────────────
circuit_breaker_state = {
    "open": False,
    "failures": 0,
    "threshold": 3,
    "reset_after_sec": 300,
    "last_failure": None,
}
circuit_breaker_lock = threading.Lock()

# ── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(RUN_LOG), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("cloud_supervisor")

# ── FastAPI App ─────────────────────────────────────────────────────
app = FastAPI(
    title="NeoLight Cloud Failover Supervisor",
    version="2.1.0-hybrid",
    description="Production-grade hybrid failover with security + reliability",
)

# ── Global State ────────────────────────────────────────────────────
smarttrader_proc: subprocess.Popen | None = None
proc_lock = threading.RLock()
activation_timestamp: datetime | None = None
last_state_sync: datetime | None = None
startup_time = datetime.now(UTC)
metrics = {
    "activations": 0,
    "deactivations": 0,
    "state_syncs": 0,
    "state_sync_failures": 0,
    "smarttrader_crashes": 0,
}


# ── Security Functions (Claude's) ─────────────────────────────────
def verify_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> bool:
    """Verify API key authentication"""
    if not REQUIRE_AUTH:
        return True
    if not api_key or api_key != EXPECTED_API_KEY:
        logger.warning("Invalid API key attempt")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


def check_circuit_breaker():
    """Circuit breaker to prevent activation spam (Claude's)"""
    with circuit_breaker_lock:
        if circuit_breaker_state["open"]:
            # Check if reset time has passed
            if circuit_breaker_state["last_failure"]:
                elapsed = (
                    datetime.now(UTC) - circuit_breaker_state["last_failure"]
                ).total_seconds()
                if elapsed >= circuit_breaker_state["reset_after_sec"]:
                    logger.info("Circuit breaker reset after cooldown period")
                    circuit_breaker_state["open"] = False
                    circuit_breaker_state["failures"] = 0
                else:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Circuit breaker open. Try again in {int(circuit_breaker_state['reset_after_sec'] - elapsed)}s",
                    )
            else:
                raise HTTPException(status_code=429, detail="Circuit breaker open")


def record_circuit_breaker_failure():
    """Record failure and potentially open circuit breaker"""
    with circuit_breaker_lock:
        circuit_breaker_state["failures"] += 1
        circuit_breaker_state["last_failure"] = datetime.now(UTC)
        if circuit_breaker_state["failures"] >= circuit_breaker_state["threshold"]:
            circuit_breaker_state["open"] = True
            logger.warning(
                f"Circuit breaker opened after {circuit_breaker_state['failures']} failures"
            )


def reset_circuit_breaker():
    """Reset circuit breaker on success"""
    with circuit_breaker_lock:
        circuit_breaker_state["open"] = False
        circuit_breaker_state["failures"] = 0
        circuit_breaker_state["last_failure"] = None


# ── Models ───────────────────────────────────────────────────────────
class ActivateRequest(BaseModel):
    bucket: str = Field(..., description="GCS bucket path (gs://bucket-name)")
    ts: str | None = Field(None, description="Timestamp")
    source: str | None = Field(None, description="Activation source")
    hostname: str | None = Field(None, description="Source hostname")
    force: bool | None = Field(
        False, description="Force activation even if circuit breaker is open"
    )


# ── Helpers ─────────────────────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    """Thread-safe logging"""
    timestamp = datetime.now(UTC).isoformat()
    logger.log(getattr(logging, level.upper(), logging.INFO), msg)
    sys.stdout.flush()


def sync_from_google_drive() -> bool:
    """Sync state from Google Drive using rclone (for proactive failover)"""
    rclone_remote = os.getenv("RCLONE_REMOTE", "neo_remote")
    rclone_path = os.getenv("RCLONE_PATH", "NeoLight")
    
    if not rclone_remote:
        log("⚠️ RCLONE_REMOTE not set, skipping Google Drive sync", "WARNING")
        return False
    
    cmd = [
        "rclone", "copy",
        f"{rclone_remote}:{rclone_path}/state",
        str(STATE_DIR),
        "--create-empty-src-dirs",
        "--fast-list",
        "--transfers=4"
    ]
    
    log(f"☁️ Syncing state from Google Drive ({rclone_remote}:{rclone_path}/state)...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=True)
        log("✅ State synced from Google Drive successfully")
        global last_state_sync, metrics
        last_state_sync = datetime.now(UTC)
        metrics["state_syncs"] += 1
        return True
    except subprocess.TimeoutExpired:
        log("⚠️ Google Drive sync timeout", "WARNING")
    except subprocess.CalledProcessError as e:
        log(f"⚠️ Google Drive sync failed: {e.stderr}", "WARNING")
    except FileNotFoundError:
        log("⚠️ rclone not found, skipping Google Drive sync", "WARNING")
    
    metrics["state_sync_failures"] += 1
    return False


def gsutil_sync_from(bucket: str, max_retries: int = 3) -> bool:
    """Pull state from GCS with retries (Auto's improved version)"""
    if not bucket.startswith("gs://"):
        raise ValueError("bucket must start with gs://")

    cmd = ["gsutil", "-m", "rsync", "-r", "-d", f"{bucket}/state", str(STATE_DIR)]
    log(f"☁️ Pulling state from {bucket} ...")

    for attempt in range(1, max_retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=True)
            log(f"✅ State pulled successfully (attempt {attempt})")
            global last_state_sync, metrics
            last_state_sync = datetime.now(UTC)
            metrics["state_syncs"] += 1
            return True
        except subprocess.TimeoutExpired:
            log(f"⚠️ State pull timeout (attempt {attempt}/{max_retries})", "WARNING")
        except subprocess.CalledProcessError as e:
            log(f"⚠️ State pull failed (attempt {attempt}/{max_retries}): {e.stderr}", "WARNING")

        if attempt < max_retries:
            time.sleep(5)

    log("❌ State pull failed after all retries", "ERROR")
    metrics["state_sync_failures"] += 1
    return False


def start_smarttrader() -> bool:
    """Start SmartTrader subprocess with proper environment (Auto's version)"""
    global smarttrader_proc, activation_timestamp

    with proc_lock:
        if smarttrader_proc and smarttrader_proc.poll() is None:
            log(f"ℹ️ SmartTrader already running (PID: {smarttrader_proc.pid})")
            return True

        # Set environment
        env = os.environ.copy()
        env["TRADING_MODE"] = env.get("TRADING_MODE", "PAPER_TRADING_MODE")
        env["PYTHONPATH"] = str(APP_ROOT)
        env["HOME"] = "/app"

        # Command
        cmd = ["python3", "trader/smart_trader.py"]

        log(f"🚀 Launching SmartTrader: {' '.join(cmd)} (mode={env['TRADING_MODE']})")

        try:
            smarttrader_proc = subprocess.Popen(
                cmd,
                cwd=str(APP_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            activation_timestamp = datetime.now(UTC)
            metrics["activations"] += 1
            log(f"✅ SmartTrader started (PID: {smarttrader_proc.pid})")

            # Start output reader thread (Auto's improvement)
            threading.Thread(
                target=read_process_output, args=(smarttrader_proc,), daemon=True
            ).start()

            return True
        except Exception as e:
            log(f"❌ Failed to start SmartTrader: {e}", "ERROR")
            metrics["smarttrader_crashes"] += 1
            return False


def read_process_output(proc: subprocess.Popen):
    """Read process output and log it (Auto's threading improvement)"""
    try:
        for line in proc.stdout:
            if line:
                logger.info(f"[SmartTrader] {line.rstrip()}")
    except Exception as e:
        logger.error(f"Error reading process output: {e}")
    finally:
        # Check if process died unexpectedly
        if proc.poll() is not None:
            logger.warning(f"SmartTrader process exited with code {proc.poll()}")
            metrics["smarttrader_crashes"] += 1


def stop_smarttrader(graceful: bool = True) -> bool:
    """Stop SmartTrader with graceful shutdown (Both)"""
    global smarttrader_proc

    with proc_lock:
        if not smarttrader_proc or smarttrader_proc.poll() is not None:
            log("ℹ️ SmartTrader not running")
            return True

        pid = smarttrader_proc.pid
        log(f"🛑 Stopping SmartTrader (PID: {pid}, graceful={graceful})...")

        try:
            if graceful:
                smarttrader_proc.terminate()
                try:
                    smarttrader_proc.wait(timeout=20)
                    log("✅ SmartTrader stopped gracefully")
                    metrics["deactivations"] += 1
                    return True
                except subprocess.TimeoutExpired:
                    log("⚠️ Graceful shutdown timeout, forcing kill", "WARNING")

            smarttrader_proc.kill()
            smarttrader_proc.wait(timeout=10)
            log("✅ SmartTrader killed")
            metrics["deactivations"] += 1
            return True
        except Exception as e:
            log(f"❌ Error stopping SmartTrader: {e}", "ERROR")
            return False
        finally:
            smarttrader_proc = None


# ── Signal Handlers ──────────────────────────────────────────────────
def signal_handler(signum, frame):
    """Handle shutdown signals (Both)"""
    log(f"Received signal {signum}, shutting down gracefully...")
    stop_smarttrader(graceful=True)
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


# ── API Endpoints ───────────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, Any]:
    """Health check endpoint (no auth required)"""
    with proc_lock:
        smarttrader_status = "idle"
        smarttrader_pid = None

        if smarttrader_proc:
            if smarttrader_proc.poll() is None:
                smarttrader_status = "running"
                smarttrader_pid = smarttrader_proc.pid
            else:
                smarttrader_status = "stopped"
                smarttrader_pid = None

    uptime = (datetime.now(UTC) - startup_time).total_seconds()

    return {
        "service": "NeoLight Cloud Supervisor",
        "status": "healthy",
        "smarttrader_status": smarttrader_status,
        "trading_mode": os.getenv("TRADING_MODE", "PAPER_TRADING_MODE"),
        "uptime_seconds": uptime,
        "last_activation": activation_timestamp.isoformat() if activation_timestamp else None,
        "last_state_sync": last_state_sync.isoformat() if last_state_sync else None,
        "metrics": metrics.copy(),
        "state_info": {
            "state_dir_exists": STATE_DIR.exists(),
            "state_files_count": len(list(STATE_DIR.glob("*"))) if STATE_DIR.exists() else 0,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/activate")
def activate(
    req: ActivateRequest,
    background_tasks: BackgroundTasks,
    api_key: str | None = Security(verify_api_key),
) -> dict[str, Any]:
    """Activate SmartTrader with state sync (Claude's auth + Auto's reliability)"""
    # Check circuit breaker (unless forced)
    if not req.force:
        check_circuit_breaker()

    bucket = req.bucket

    if not bucket.startswith("gs://"):
        record_circuit_breaker_failure()
        raise HTTPException(status_code=400, detail="bucket must start with gs://")

    try:
        # Try Google Drive first (for proactive failover), then GCS
        sync_success = False
        if os.getenv("RCLONE_REMOTE"):
            sync_success = sync_from_google_drive()
        
        # Fallback to GCS if Google Drive sync failed or not configured
        if not sync_success:
            sync_success = gsutil_sync_from(bucket)
        
        if not sync_success:
            log("⚠️ State sync failed, but continuing activation", "WARNING")

        # Start SmartTrader (Auto's process management)
        if not start_smarttrader():
            record_circuit_breaker_failure()
            raise HTTPException(status_code=500, detail="Failed to start SmartTrader")

        # Reset circuit breaker on success
        reset_circuit_breaker()

        return {
            "status": "activated",
            "bucket": bucket,
            "smarttrader_pid": smarttrader_proc.pid if smarttrader_proc else None,
            "state_synced": sync_success,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        log(f"❌ Activation failed: {e}", "ERROR")
        record_circuit_breaker_failure()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/deactivate")
def deactivate(api_key: str | None = Security(verify_api_key)) -> dict[str, Any]:
    """Deactivate SmartTrader gracefully (Claude's auth)"""
    try:
        stopped = stop_smarttrader(graceful=True)
        return {
            "status": "deactivated",
            "stopped": stopped,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        log(f"❌ Deactivation error: {e}", "ERROR")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
def status() -> dict[str, Any]:
    """Detailed status endpoint (no auth)"""
    return health()


@app.get("/metrics")
def get_metrics(api_key: str | None = Security(verify_api_key)) -> dict[str, Any]:
    """Get detailed metrics (Claude's auth)"""
    return {
        "metrics": metrics.copy(),
        "circuit_breaker": circuit_breaker_state.copy(),
        "uptime_seconds": (datetime.now(UTC) - startup_time).total_seconds(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ── Startup ──────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    log("🌐 Cloud supervisor starting...")
    log(f"   App root: {APP_ROOT}")
    log(f"   State dir: {STATE_DIR}")
    log(f"   Log dir: {LOG_DIR}")
    log(f"   Auth required: {REQUIRE_AUTH}")
    log(f"   Circuit breaker threshold: {circuit_breaker_state['threshold']}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    log(f"Starting server on port {port}...")
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

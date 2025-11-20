#!/usr/bin/env python3
"""
Render Web Service Wrapper for NeoLight SmartTrader
Provides HTTP health endpoint while running smart_trader in background
"""
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Configuration
# Render uses /opt/render/project/src as the working directory
ROOT = Path("/opt/render/project/src")
if not ROOT.exists():
    # Fallback for local development
    ROOT = Path(os.path.expanduser("~/neolight"))

PORT = int(os.getenv("PORT", "8080"))
TRADER_SCRIPT = ROOT / "trader" / "smart_trader.py"

# FastAPI app
app = FastAPI(title="NeoLight Render Service", version="1.0.0")

# Global state
trader_process = None
trader_thread = None
start_time = time.time()


def run_trader():
    """Run smart_trader.py in background"""
    global trader_process

    if not TRADER_SCRIPT.exists():
        print(f"⚠️ Trader script not found: {TRADER_SCRIPT}", file=sys.stderr)
        return

    try:
        # Set environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["TRADING_MODE"] = "PAPER_TRADING_MODE"
        env["RENDER_MODE"] = "true"

        # Start trader process
        trader_process = subprocess.Popen(
            [sys.executable, str(TRADER_SCRIPT)],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print(f"✅ SmartTrader started (PID: {trader_process.pid})")

        # Monitor process
        while True:
            if trader_process.poll() is not None:
                print(f"⚠️ SmartTrader exited with code {trader_process.returncode}")
                # Restart after delay
                time.sleep(10)
                trader_process = subprocess.Popen(
                    [sys.executable, str(TRADER_SCRIPT)],
                    cwd=str(ROOT),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                print(f"🔄 SmartTrader restarted (PID: {trader_process.pid})")
            time.sleep(5)
    except Exception as e:
        print(f"❌ Error running trader: {e}", file=sys.stderr)


@app.on_event("startup")
async def startup_event():
    """Start trader in background thread"""
    global trader_thread

    print("🚀 Starting NeoLight Render Service...")
    print(f"📁 Root: {ROOT}")
    print(f"📄 Trader script: {TRADER_SCRIPT}")
    print(f"🌐 Port: {PORT}")

    # Start trader in background thread
    trader_thread = threading.Thread(target=run_trader, daemon=True)
    trader_thread.start()
    print("✅ Trader thread started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global trader_process

    if trader_process:
        print("🛑 Stopping SmartTrader...")
        trader_process.terminate()
        try:
            trader_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            trader_process.kill()
        print("✅ SmartTrader stopped")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NeoLight Render Service",
        "status": "running",
        "uptime_seconds": int(time.time() - start_time),
        "trader_running": trader_process is not None and trader_process.poll() is None,
    }


@app.get("/health")
async def health():
    """Health check endpoint for Render"""
    trader_status = "running" if (trader_process and trader_process.poll() is None) else "stopped"

    return JSONResponse(
        status_code=200 if trader_status == "running" else 503,
        content={
            "status": "healthy" if trader_status == "running" else "degraded",
            "service": "NeoLight SmartTrader",
            "trader_status": trader_status,
            "uptime_seconds": int(time.time() - start_time),
            "port": PORT,
        },
    )


# Note: Render uses uvicorn command directly, so this block is for local testing only
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)

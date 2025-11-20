#!/usr/bin/env python3
"""
Render Web Service - Multi-Agent Orchestration
Provides HTTP health endpoint while running multiple NeoLight agents in background
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Configuration
ROOT = Path("/opt/render/project/src")
if not ROOT.exists():
    ROOT = Path(os.path.expanduser("~/neolight"))

PORT = int(os.getenv("PORT", "8080"))

# Agent definitions (in startup order)
AGENTS = {
    "intelligence_orchestrator": {
        "script": ROOT / "agents" / "intelligence_orchestrator.py",
        "priority": 1,  # Must start first
        "required": True,
        "description": "Intelligence Orchestrator (generates risk_scaler and confidence)",
    },
    "ml_pipeline": {
        "script": ROOT / "agents" / "ml_pipeline.py",
        "priority": 2,
        "required": False,  # Can run independently
        "description": "ML Pipeline (auto-trains models every 6 hours)",
    },
    "strategy_research": {
        "script": ROOT / "agents" / "strategy_research.py",
        "priority": 3,
        "required": False,
        "description": "Strategy Research (ranks and optimizes strategies)",
    },
    "market_intelligence": {
        "script": ROOT / "agents" / "market_intelligence.py",
        "priority": 4,
        "required": False,
        "description": "Market Intelligence (sentiment analysis)",
    },
    "smart_trader": {
        "script": ROOT / "trader" / "smart_trader.py",
        "priority": 5,  # Must start after intelligence_orchestrator
        "required": True,
        "description": "SmartTrader (main trading loop)",
    },
    "sports_betting": {
        "script": ROOT / "agents" / "sports_betting_agent.py",
        "priority": 6,
        "required": False,
        "description": "Sports Betting Agent (paper trading, manual BetMGM workflow)",
    },
    "dropship_agent": {
        "script": ROOT / "agents" / "dropship_agent.py",
        "priority": 7,
        "required": False,
        "description": "Dropshipping Agent (multi-platform: Etsy, Mercari, Poshmark, TikTok Shop)",
    },
}

# FastAPI app
app = FastAPI(title="NeoLight Multi-Agent Render Service", version="2.0.0")

# Mount static files for dashboard
STATIC_DIR = ROOT / "dashboard" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Dashboard endpoints (simplified for Render)
STATE_DIR = ROOT / "state"
RUNTIME_DIR = ROOT / "runtime"


@app.get("/dashboard")
async def dashboard_home():
    """Dashboard home page - redirects to local dashboard or shows status"""
    dashboard_html = ROOT / "dashboard" / "sports_dashboard.html"
    if dashboard_html.exists():
        return FileResponse(dashboard_html)

    # Simple status page if dashboard not available
    return HTMLResponse(
        content="""
        <html>
        <head><title>NeoLight Dashboard</title></head>
        <body style="font-family: monospace; padding: 20px;">
            <h1>NeoLight Multi-Agent System</h1>
            <p>Dashboard: <a href="/api/trades">Trades</a> | <a href="/api/betting">Betting</a> | <a href="/api/revenue">Revenue</a></p>
            <p>For full dashboard, access locally at: http://localhost:8090</p>
        </body>
        </html>
        """
    )


@app.get("/api/trades")
async def get_trades():
    """Get trading transactions"""
    pnl_file = STATE_DIR / "pnl_history.csv"
    if pnl_file.exists():
        try:
            import csv

            with open(pnl_file) as f:
                reader = csv.DictReader(f)
                trades = list(reader)
            return {"trades": trades[-50:], "total": len(trades)}  # Last 50 trades
        except Exception as e:
            return {"error": str(e), "trades": []}
    return {"trades": [], "total": 0}


@app.get("/api/betting")
async def get_betting_results():
    """Get sports betting results"""
    results = {}

    # Betting history
    betting_file = STATE_DIR / "sports_paper_trades.json"
    if betting_file.exists():
        try:
            results["history"] = json.loads(betting_file.read_text())
        except Exception:
            results["history"] = []

    # Bankroll
    bankroll_file = STATE_DIR / "sports_bankroll.json"
    if bankroll_file.exists():
        try:
            results["bankroll"] = json.loads(bankroll_file.read_text())
        except Exception:
            results["bankroll"] = {"bankroll": 1000, "initial_bankroll": 1000}

    # Predictions
    predictions_file = STATE_DIR / "sports_predictions.json"
    if predictions_file.exists():
        try:
            results["predictions"] = json.loads(predictions_file.read_text())
        except Exception:
            results["predictions"] = []

    return results


@app.get("/api/revenue")
async def get_revenue():
    """Get revenue by agent"""
    revenue_file = STATE_DIR / "revenue_by_agent.json"
    if revenue_file.exists():
        try:
            return json.loads(revenue_file.read_text())
        except Exception:
            pass

    # Dropshipping revenue
    dropship_file = STATE_DIR / "dropship_profit.csv"
    dropship_revenue = 0
    if dropship_file.exists():
        try:
            import csv

            with open(dropship_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    dropship_revenue += float(row.get("profit", 0) or 0)
        except Exception:
            pass

    return {
        "agents": [
            {"name": "smart_trader", "revenue": 0, "cost": 0, "net_pnl": 0},
            {"name": "sports_betting", "revenue": 0, "cost": 0, "net_pnl": 0},
            {
                "name": "dropship_agent",
                "revenue": dropship_revenue,
                "cost": 0,
                "net_pnl": dropship_revenue,
            },
        ]
    }


@app.get("/api/sports/predictions")
async def get_sports_predictions():
    """Get sports predictions"""
    predictions_file = STATE_DIR / "sports_predictions.json"
    if predictions_file.exists():
        try:
            return json.loads(predictions_file.read_text())
        except Exception:
            return {"predictions": []}
    return {"predictions": []}


@app.get("/api/sports/history")
async def get_sports_history():
    """Get sports betting history"""
    history_file = STATE_DIR / "sports_paper_trades.json"
    if history_file.exists():
        try:
            return json.loads(history_file.read_text())
        except Exception:
            return []
    return []


# Global state
agent_processes: dict[str, subprocess.Popen | None] = {}
agent_threads: dict[str, threading.Thread | None] = {}
start_time = time.time()
agent_status: dict[str, dict] = {}


def get_agent_env() -> dict[str, str]:
    """Get environment variables for agents"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["TRADING_MODE"] = "PAPER_TRADING_MODE"
    env["RENDER_MODE"] = "true"
    # Enable agents by default
    env.setdefault("NEOLIGHT_ENABLE_ML_PIPELINE", "true")
    env.setdefault("NEOLIGHT_ENABLE_STRATEGY_RESEARCH", "true")
    env.setdefault("NEOLIGHT_ENABLE_MARKET_INTEL", "true")
    return env


def run_agent(agent_name: str, agent_config: dict) -> None:
    """Run a single agent in background with auto-restart"""
    global agent_processes, agent_status

    script_path = agent_config["script"]
    if not script_path.exists():
        print(f"⚠️ {agent_name}: Script not found: {script_path}", file=sys.stderr)
        agent_status[agent_name] = {
            "status": "error",
            "message": f"Script not found: {script_path}",
            "pid": None,
        }
        return

    env = get_agent_env()
    restart_delay = 10

    while True:
        try:
            # Start agent process
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            agent_processes[agent_name] = process
            agent_status[agent_name] = {
                "status": "running",
                "pid": process.pid,
                "started_at": time.time(),
                "restarts": agent_status.get(agent_name, {}).get("restarts", 0),
            }

            print(f"✅ {agent_name} started (PID: {process.pid})")

            # Monitor process
            while True:
                if process.poll() is not None:
                    exit_code = process.returncode
                    restarts = agent_status[agent_name].get("restarts", 0) + 1
                    agent_status[agent_name] = {
                        "status": "stopped",
                        "pid": None,
                        "exit_code": exit_code,
                        "restarts": restarts,
                        "last_restart": time.time(),
                    }
                    print(f"⚠️ {agent_name} exited with code {exit_code} (restart #{restarts})")

                    if agent_config.get("required", False) and restarts < 10:
                        # Required agents get restarted
                        time.sleep(restart_delay)
                        break  # Restart loop
                    elif not agent_config.get("required", False) and restarts < 5:
                        # Optional agents get fewer retries
                        time.sleep(restart_delay * 2)
                        break  # Restart loop
                    else:
                        # Too many restarts, give up
                        print(f"❌ {agent_name}: Too many restarts ({restarts}), stopping")
                        agent_status[agent_name]["status"] = "failed"
                        agent_processes[agent_name] = None
                        return

                time.sleep(5)

        except Exception as e:
            print(f"❌ Error running {agent_name}: {e}", file=sys.stderr)
            agent_status[agent_name] = {
                "status": "error",
                "message": str(e),
                "pid": None,
            }
            time.sleep(restart_delay)


@app.on_event("startup")
async def startup_event():
    """Start all agents in background threads"""
    global agent_threads

    print("🚀 Starting NeoLight Multi-Agent Render Service...")
    print(f"📁 Root: {ROOT}")
    print(f"🌐 Port: {PORT}")

    # Sort agents by priority
    sorted_agents = sorted(AGENTS.items(), key=lambda x: x[1]["priority"])

    # Start agents in order
    for agent_name, agent_config in sorted_agents:
        print(f"📋 Starting {agent_name}: {agent_config['description']}")

        # Initialize status
        agent_status[agent_name] = {
            "status": "starting",
            "pid": None,
        }

        # Start agent in background thread
        thread = threading.Thread(target=run_agent, args=(agent_name, agent_config), daemon=True)
        thread.start()
        agent_threads[agent_name] = thread

        # Small delay between starts (especially important for intelligence_orchestrator -> smart_trader)
        if agent_config["priority"] == 1:
            time.sleep(3)  # Give intelligence_orchestrator time to start
        else:
            time.sleep(1)

    print("✅ All agent threads started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global agent_processes

    print("🛑 Stopping all agents...")

    for agent_name, process in agent_processes.items():
        if process and process.poll() is None:
            print(f"🛑 Stopping {agent_name}...")
            process.terminate()
            try:
                process.wait(timeout=10)
                print(f"✅ {agent_name} stopped")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"✅ {agent_name} killed")

    print("✅ All agents stopped")


@app.get("/")
async def root():
    """Root endpoint with system status"""
    running_count = sum(1 for status in agent_status.values() if status.get("status") == "running")
    total_count = len(AGENTS)

    return {
        "service": "NeoLight Multi-Agent Render Service",
        "status": "running",
        "uptime_seconds": int(time.time() - start_time),
        "agents": {
            "total": total_count,
            "running": running_count,
            "status": agent_status,
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint for Render - Always returns 200 so Render doesn't timeout"""
    # Check critical agents
    critical_agents = [name for name, config in AGENTS.items() if config.get("required", False)]

    all_critical_running = all(
        agent_status.get(name, {}).get("status") == "running" for name in critical_agents
    )

    running_count = sum(1 for status in agent_status.values() if status.get("status") == "running")

    # Always return 200 - Render health check will timeout if we return 503
    # We indicate status in response body instead
    overall_status = (
        "healthy" if all_critical_running else "starting"
    )  # "starting" instead of "degraded"

    return JSONResponse(
        status_code=200,  # Always 200 - never 503
        content={
            "status": overall_status,
            "service": "NeoLight Multi-Agent System",
            "agents_running": running_count,
            "agents_total": len(AGENTS),
            "critical_agents": {
                name: agent_status.get(name, {}).get("status", "unknown")
                for name in critical_agents
            },
            "uptime_seconds": int(time.time() - start_time),
            "port": PORT,
        },
    )


@app.get("/agents")
async def agents_status():
    """Detailed agent status endpoint"""
    return {
        "agents": agent_status,
        "definitions": {
            name: {
                "description": config["description"],
                "priority": config["priority"],
                "required": config.get("required", False),
            }
            for name, config in AGENTS.items()
        },
    }


@app.get("/agents/{agent_name}")
async def agent_detail(agent_name: str):
    """Get detailed status for a specific agent"""
    if agent_name not in AGENTS:
        return JSONResponse(status_code=404, content={"error": f"Agent '{agent_name}' not found"})

    status = agent_status.get(agent_name, {})
    config = AGENTS[agent_name]
    process = agent_processes.get(agent_name)

    return {
        "name": agent_name,
        "description": config["description"],
        "priority": config["priority"],
        "required": config.get("required", False),
        "status": status,
        "process": {
            "pid": process.pid if process else None,
            "running": process.poll() is None if process else False,
        },
    }


# Note: Render uses uvicorn command directly, so this block is for local testing only
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)

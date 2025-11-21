#!/usr/bin/env python3
"""
Check which phases are currently running and enable missing ones.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
LOGS = ROOT / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

# Phase definitions
PHASES = {
    "Phase 301-340: Equity Replay": {
        "script": "phases/phase_301_340_equity_replay.py",
        "log": "equity_replay.log",
        "pattern": "phase_301_340_equity_replay",
        "env_var": "NEOLIGHT_ENABLE_EQUITY_REPLAY",
        "default": "true",
    },
    "Phase 900-1100: Atlas Integration": {
        "script": "agents/intelligence_orchestrator.py",
        "log": "intelligence_orchestrator.log",
        "pattern": "intelligence_orchestrator",
        "env_var": None,  # Always enabled
    },
    "Phase 1100-1300: AI Learning & Backtesting": {
        "script": "analytics/strategy_backtesting.py",
        "log": "strategy_backtesting.log",
        "pattern": "strategy_backtesting",
        "env_var": "NEOLIGHT_ENABLE_BACKTESTING",
        "default": "true",
    },
    "Phase 1500-1800: ML Pipeline": {
        "script": "agents/ml_pipeline.py",
        "log": "ml_pipeline.log",
        "pattern": "ml_pipeline",
        "env_var": "NEOLIGHT_ENABLE_ML_PIPELINE",
        "default": "true",
    },
    "Phase 1800-2000: Performance Attribution": {
        "script": "agents/performance_attribution.py",
        "log": "performance_attribution.log",
        "pattern": "performance_attribution",
        "env_var": "NEOLIGHT_ENABLE_ATTRIBUTION",
        "default": "true",
    },
    "Phase 2000-2300: Regime Detection": {
        "script": "agents/regime_detector.py",
        "log": "regime_detector.log",
        "pattern": "regime_detector",
        "env_var": "NEOLIGHT_ENABLE_REGIME",
        "default": "true",
    },
    "Phase 2300-2500: Meta-Metrics Dashboard": {
        "script": "dashboard/app.py",
        "log": "dashboard.log",
        "pattern": "dashboard|uvicorn.*dashboard",
        "env_var": None,  # Always enabled
    },
    "Phase 2500-2700: Portfolio Optimization": {
        "script": "phases/phase_2500_2700_portfolio_optimization.py",
        "log": "portfolio_optimization.log",
        "pattern": "phase_2500_2700_portfolio_optimization",
        "env_var": "NEOLIGHT_ENABLE_PORTFOLIO_OPTIMIZATION",
        "default": "true",
    },
    "Phase 2700-2900: Advanced Risk Management": {
        "script": "phases/phase_2700_2900_risk_management.py",
        "log": "risk_management.log",
        "pattern": "phase_2700_2900_risk_management",
        "env_var": "NEOLIGHT_ENABLE_RISK_MANAGEMENT",
        "default": "true",
    },
    "Phase 3100-3300: Enhanced Signal Generation": {
        "script": "trader/smart_trader.py",
        "log": "smart_trader.log",
        "pattern": "smart_trader",
        "env_var": None,  # Always enabled
    },
    "Phase 3300-3500: Kelly Criterion": {
        "script": "phases/phase_3300_3500_kelly.py",
        "log": "kelly_sizing.log",
        "pattern": "phase_3300_3500_kelly",
        "env_var": "NEOLIGHT_ENABLE_KELLY_SIZING",
        "default": "true",
    },
    "Phase 3500-3700: Multi-Strategy Framework": {
        "script": "agents/strategy_manager.py",
        "log": "strategy_manager.log",
        "pattern": "strategy_manager",
        "env_var": None,  # Always enabled
    },
    "Phase 3700-3900: Reinforcement Learning": {
        "script": "phases/phase_3700_3900_rl.py",
        "log": "rl_enhanced.log",
        "pattern": "phase_3700_3900_rl|rl_enhanced",
        "env_var": "NEOLIGHT_ENABLE_RL_ENHANCED",
        "default": "true",
    },
    "Phase 3900-4100: Event-Driven Architecture": {
        "script": "phases/phase_3900_4100_events.py",
        "log": "event_driven.log",
        "pattern": "phase_3900_4100_events|event_driven",
        "env_var": "NEOLIGHT_ENABLE_EVENTS",
        "default": "true",
    },
    "Phase 4100-4300: Advanced Execution Algorithms": {
        "script": "phases/phase_4100_4300_execution.py",
        "log": "execution_algorithms.log",
        "pattern": "phase_4100_4300_execution|execution_algorithms",
        "env_var": "NEOLIGHT_ENABLE_EXECUTION_ALGORITHMS",
        "default": "true",
    },
    "Phase 4300-4500: Portfolio Analytics": {
        "script": "phases/phase_4300_4500_analytics.py",
        "log": "portfolio_analytics.log",
        "pattern": "phase_4300_4500_analytics|portfolio_analytics",
        "env_var": "NEOLIGHT_ENABLE_PORTFOLIO_ANALYTICS",
        "default": "true",
    },
    "Phase 4500-4700: Alternative Data Integration": {
        "script": "phases/phase_4500_4700_alt_data.py",
        "log": "alt_data.log",
        "pattern": "phase_4500_4700_alt_data|alt_data",
        "env_var": "NEOLIGHT_ENABLE_ALT_DATA",
        "default": "true",
    },
}


def check_running(pattern):
    """Check if a process matching pattern is running."""
    try:
        result = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and result.stdout.strip()
    except Exception:
        return False


def check_log_recent(log_file):
    """Check if log file exists and was updated recently (within 1 hour)."""
    log_path = LOGS / log_file
    if not log_path.exists():
        return False, "No log file"

    try:
        mtime = log_path.stat().st_mtime
        age = time.time() - mtime
        if age < 3600:
            return True, f"Active ({int(age / 60)} min ago)"
        else:
            return False, f"Stale ({int(age / 3600)} hours ago)"
    except Exception as e:
        return False, f"Error: {e}"


def get_env_var(name, default=None):
    """Get environment variable value."""
    return os.getenv(name, default)


def start_phase(phase_info):
    """Start a phase directly."""
    script = phase_info["script"]
    log = phase_info["log"]
    pattern = phase_info["pattern"]

    script_path = ROOT / script
    if not script_path.exists():
        print(f"   ❌ Script not found: {script}")
        return False

    try:
        # Start the phase in background
        log_path = LOGS / log
        cmd = f"cd {ROOT} && PYTHONPATH={ROOT} python3 {script_path} >> {log_path} 2>&1 &"
        subprocess.run(cmd, shell=True, timeout=10)
        time.sleep(2)  # Give it time to start

        # Verify it's running
        if check_running(pattern):
            print("   ✅ Started successfully")
            return True
        else:
            print(f"   ⚠️  Started but not verified (check {log_path})")
            return False
    except Exception as e:
        print(f"   ❌ Failed to start: {e}")
        return False


def main():
    """Main function to check and enable phases."""
    print("=" * 70)
    print("🔍 Checking Phase Status")
    print("=" * 70)
    print()

    running_phases = []
    not_running_phases = []

    for phase_name, phase_info in PHASES.items():
        script = phase_info["script"]
        log = phase_info["log"]
        pattern = phase_info["pattern"]
        env_var = phase_info.get("env_var")

        print(f"📊 {phase_name}")

        # Check if process is running
        is_running = check_running(pattern)
        log_exists, log_status = check_log_recent(log)

        # Check environment variable if applicable
        env_status = ""
        if env_var:
            env_value = get_env_var(env_var, phase_info.get("default", "true"))
            env_status = f" ({env_var}={env_value})"

        if is_running:
            print(f"   ✅ RUNNING{env_status}")
            running_phases.append(phase_name)
        else:
            print(f"   ❌ NOT RUNNING{env_status}")
            not_running_phases.append((phase_name, phase_info))

        print(f"   📝 Log: {log_status}")
        print()

    print("=" * 70)
    print("📋 Summary")
    print("=" * 70)
    print(f"✅ Running: {len(running_phases)} phases")
    print(f"❌ Not Running: {len(not_running_phases)} phases")
    print()

    if not_running_phases:
        print("Phases that need to be enabled:")
        for phase_name, phase_info in not_running_phases:
            print(f"  - {phase_name}")
            print(f"    Script: {phase_info['script']}")
            if phase_info.get("env_var"):
                print(
                    f"    Env Var: {phase_info['env_var']} (default: {phase_info.get('default', 'true')})"
                )
        print()

        # Check if neo_light_fix.sh is running
        guardian_running = check_running("neo_light_fix.sh|guardian")
        if guardian_running:
            print("✅ Guardian is running - phases should auto-start based on env vars")
            print("   Missing phases may need their env vars set to 'true'")
        else:
            print("⚠️  Guardian is NOT running")
            print("   Run: bash neo_light_fix.sh")
            print()

        # Ask if user wants to start missing phases
        print("=" * 70)
        print("🚀 Start Missing Phases?")
        print("=" * 70)
        print("To start missing phases, run:")
        print("  bash enable_missing_phases.sh all")
        print("Or start individual phases:")
        for phase_name, phase_info in not_running_phases:
            phase_key = (
                phase_name.split(":")[0]
                .lower()
                .replace("phase ", "")
                .replace("-", "_")
                .replace(" ", "_")
            )
            print(f"  bash enable_missing_phases.sh {phase_key}")

    return not_running_phases


if __name__ == "__main__":
    missing = main()
    sys.exit(0 if not missing else 1)

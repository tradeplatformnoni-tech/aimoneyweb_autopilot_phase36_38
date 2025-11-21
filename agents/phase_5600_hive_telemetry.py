#!/usr/bin/env python3
"""
Phase 5600: Cross-Agent Hive Telemetry
Aggregates performance across trading + revenue agents
Unified metrics for Atlas dashboard and Capital Governor
"""

import json
import os
import time
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
DATA = ROOT / "data"
LOGS = ROOT / "logs"

# Detect Render environment - disable dashboard on Render (no localhost)
RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
DASHBOARD_URL = os.getenv(
    "NEOLIGHT_DASHBOARD_URL", "http://localhost:8100" if not RENDER_MODE else None
)
UPDATE_INTERVAL = int(os.getenv("NL_TELEMETRY_INTERVAL_SEC", "300"))  # 5 minutes


# Helper functions for metrics calculation
def calculate_sharpe(returns: list[float]) -> float:
    """Calculate Sharpe ratio (mean / std)."""
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
    std = variance**0.5
    return mean / std if std > 0 else 0.0


def calculate_max_drawdown(equity_series: list[float]) -> float:
    """Calculate maximum drawdown percentage."""
    if not equity_series or len(equity_series) < 2:
        return 0.0
    peak = equity_series[0]
    max_dd = 0.0
    for value in equity_series:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def calculate_win_rate(decisions: list[dict[str, Any]]) -> float:
    """Calculate win rate from decisions with P&L."""
    pnl_decisions = [d for d in decisions if d.get("pnl") is not None and d.get("pnl_attributed")]
    if not pnl_decisions:
        return 0.0
    wins = len([d for d in pnl_decisions if d.get("pnl", 0) > 0])
    return wins / len(pnl_decisions)


def calculate_pnl_1d(decisions: list[dict[str, Any]]) -> float:
    """Calculate 1-day P&L from decisions."""
    now = datetime.now(UTC)
    one_day_ago = now - timedelta(days=1)

    pnl_1d = 0.0
    for decision in decisions:
        ts_str = decision.get("timestamp")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts >= one_day_ago:
                pnl = decision.get("pnl")
                if pnl is not None:
                    pnl_1d += pnl
        except:
            continue
    return pnl_1d


def calculate_pnl_7d(decisions: list[dict[str, Any]]) -> float:
    """Calculate 7-day P&L from decisions."""
    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)

    pnl_7d = 0.0
    for decision in decisions:
        ts_str = decision.get("timestamp")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts >= seven_days_ago:
                pnl = decision.get("pnl")
                if pnl is not None:
                    pnl_7d += pnl
        except:
            continue
    return pnl_7d


def load_performance_attribution() -> dict[str, Any]:
    """Load performance attribution data."""
    attr_file = STATE / "performance_attribution.json"
    if attr_file.exists():
        try:
            return json.loads(attr_file.read_text())
        except:
            pass
    return {"decisions": []}


def load_strategy_scores() -> dict[str, Any]:
    """Load strategy scores."""
    scores_file = STATE / "strategy_scores.json"
    if scores_file.exists():
        try:
            return json.loads(scores_file.read_text())
        except:
            pass

    # Calculate from performance attribution if file doesn't exist
    try:
        from agents.performance_attribution import calculate_strategy_scores

        return calculate_strategy_scores()
    except:
        pass

    return {}


def load_revenue_by_agent() -> dict[str, Any]:
    """Load revenue by agent data."""
    revenue_file = STATE / "revenue_by_agent.json"
    if revenue_file.exists():
        try:
            return json.loads(revenue_file.read_text())
        except:
            pass
    return {}


def load_market_regime() -> dict[str, Any]:
    """Load market regime data."""
    regime_file = RUNTIME / "market_regime.json"
    if regime_file.exists():
        try:
            return json.loads(regime_file.read_text())
        except:
            pass
    return {}


def load_guardian_state() -> dict[str, Any]:
    """Load Guardian state (from SmartTrader telemetry or pause file)."""
    pause_file = STATE / "guardian_pause.json"
    guardian_state = {"is_paused": False, "drawdown": 0.0, "reason": "Normal operation"}

    if pause_file.exists():
        try:
            pause_data = json.loads(pause_file.read_text())
            if pause_data.get("paused", False):
                guardian_state["is_paused"] = True
                guardian_state["reason"] = pause_data.get("reason", "Guardian intervention")
        except:
            pass

    return guardian_state


def load_circuit_breaker_states() -> dict[str, Any]:
    """Load circuit breaker states (from SmartTrader telemetry or defaults)."""
    # Default states if not available
    return {"quote_state": "CLOSED", "trade_state": "CLOSED"}


def aggregate_per_agent_metrics() -> dict[str, dict[str, Any]]:
    """Aggregate metrics per agent."""
    attr_data = load_performance_attribution()
    decisions = attr_data.get("decisions", [])
    revenue_data = load_revenue_by_agent()

    # Group decisions by agent
    agent_decisions = {}
    for decision in decisions:
        agent = decision.get("agent", "unknown")
        if agent not in agent_decisions:
            agent_decisions[agent] = []
        agent_decisions[agent].append(decision)

    per_agent = {}

    # Process each agent
    for agent_name, agent_decs in agent_decisions.items():
        pnl_1d = calculate_pnl_1d(agent_decs)
        pnl_7d = calculate_pnl_7d(agent_decs)

        # Calculate win rate from decisions with P&L
        win_rate = calculate_win_rate(agent_decs)

        # Calculate Sharpe (from returns)
        returns = [d.get("pnl", 0) for d in agent_decs if d.get("pnl") is not None]
        sharpe_30d = (
            calculate_sharpe(returns[-30:]) if len(returns) >= 30 else calculate_sharpe(returns)
        )

        # Max drawdown (simplified - would need equity curve)
        # For now, use negative PnL as proxy
        max_dd_30d = abs(
            min([d.get("pnl", 0) for d in agent_decs if d.get("pnl") is not None] or [0])
        )

        # Add revenue data if available
        revenue_info = revenue_data.get(agent_name, {})

        per_agent[agent_name] = {
            "pnl_1d": round(pnl_1d, 2),
            "pnl_7d": round(pnl_7d, 2),
            "sharpe_30d": round(sharpe_30d, 3),
            "winrate_30d": round(win_rate, 3),
            "max_dd_30d": round(max_dd_30d, 2),
            "total_decisions": len(agent_decs),
            "revenue_24h": revenue_info.get("revenue_24h", 0.0),
            "revenue_total": revenue_info.get("revenue_total", 0.0),
        }

    return per_agent


def aggregate_per_strategy_metrics() -> dict[str, dict[str, Any]]:
    """Aggregate metrics per strategy."""
    strategy_scores = load_strategy_scores()
    strategy_perf = {}

    # Load strategy performance file
    perf_file = STATE / "strategy_performance.json"
    if perf_file.exists():
        try:
            perf_data = json.loads(perf_file.read_text())
            ranked = perf_data.get("ranked_strategies", [])
            active = perf_data.get("active_strategies", [])

            for strategy in ranked + active:
                strat_name = strategy.get("strategy", "unknown")
                strategy_perf[strat_name] = {
                    "pnl_1d": 0.0,  # Would need time-series data
                    "pnl_7d": 0.0,
                    "sharpe_30d": round(strategy.get("sharpe", 0.0), 3),
                    "winrate_30d": 0.0,  # Would need trade history
                    "max_dd_30d": round(strategy.get("drawdown", 0.0), 2),
                    "trade_count": 0,  # Would need trade history
                    "score": round(strategy.get("score", 0.0), 3),
                }
        except:
            pass

    return strategy_perf


def build_meta_metrics() -> dict[str, Any]:
    """Build complete meta-metrics payload."""
    per_agent = aggregate_per_agent_metrics()
    per_strategy = aggregate_per_strategy_metrics()
    market_regime = load_market_regime()
    guardian_state = load_guardian_state()
    circuit_breakers = load_circuit_breaker_states()

    # Determine trading mode (from SmartTrader state or default)
    trading_mode = "TEST_MODE"  # Default, should be updated from SmartTrader telemetry

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "per_agent": per_agent,
        "per_strategy": per_strategy,
        "guardian": guardian_state,
        "breakers": circuit_breakers,
        "mode": trading_mode,
        "market_regime": market_regime,
        "summary": {
            "total_agents": len(per_agent),
            "total_strategies": len(per_strategy),
            "top_agent": max(per_agent.items(), key=lambda x: x[1].get("pnl_7d", 0))[0]
            if per_agent
            else None,
            "top_strategy": max(per_strategy.items(), key=lambda x: x[1].get("score", 0))[0]
            if per_strategy
            else None,
        },
    }


def push_to_meta_metrics(data: dict[str, Any], max_retries: int = 3) -> bool:
    """
    Push meta-metrics to dashboard with retry logic.
    On Render, skip dashboard push (no localhost available).
    World-class: Exponential backoff, health checks, graceful degradation.
    """
    if not DASHBOARD_URL:
        # On Render, skip dashboard push (no localhost available)
        return True
    for attempt in range(max_retries):
        try:
            # Quick health check
            try:
                health = requests.get(f"{DASHBOARD_URL}/status", timeout=2)
                if health.status_code != 200:
                    if attempt < max_retries - 1:
                        wait_time = 5 * (2**attempt)
                        time.sleep(wait_time)
                        continue
            except:
                if attempt < max_retries - 1:
                    wait_time = 5 * (2**attempt)
                    time.sleep(wait_time)
                    continue

            # Push metrics
            response = requests.post(f"{DASHBOARD_URL}/meta/metrics", json=data, timeout=10)
            if response.status_code == 200:
                return True
            else:
                if attempt < max_retries - 1:
                    time.sleep(5 * (2**attempt))
                    continue
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                wait_time = 5 * (2**attempt)
                print(
                    f"[phase_5600] Dashboard not ready (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...",
                    flush=True,
                )
                time.sleep(wait_time)
            else:
                print(
                    f"[phase_5600] Dashboard connection failed after {max_retries} attempts",
                    flush=True,
                )
        except Exception as e:
            print(
                f"[phase_5600] Dashboard push failed (attempt {attempt + 1}/{max_retries}): {e}",
                flush=True,
            )
            if attempt < max_retries - 1:
                time.sleep(5 * (2**attempt))

    return False


def send_daily_summary() -> None:
    """Send daily Telegram summary at 09:00 local time."""
    try:
        from trader.smart_trader import send_telegram

        metrics = build_meta_metrics()
        summary = metrics.get("summary", {})
        per_agent = metrics.get("per_agent", {})
        per_strategy = metrics.get("per_strategy", {})
        guardian = metrics.get("guardian", {})
        market_regime = metrics.get("market_regime", {})

        # Calculate total 24h PnL
        total_pnl_24h = sum(agent.get("pnl_1d", 0) for agent in per_agent.values())

        # Top agent
        top_agent = summary.get("top_agent")
        top_agent_pnl = per_agent.get(top_agent, {}).get("pnl_7d", 0.0) if top_agent else 0.0

        # Top strategy
        top_strategy = summary.get("top_strategy")
        top_strategy_score = (
            per_strategy.get(top_strategy, {}).get("score", 0.0) if top_strategy else 0.0
        )

        # Regime
        regime = market_regime.get("regime", "UNKNOWN")

        # Drawdown
        drawdown = guardian.get("drawdown", 0.0)

        # Build summary message
        msg = "📊 Daily Summary:\n"
        msg += f"PnL 24h: ${total_pnl_24h:,.2f}\n"
        msg += f"Top Agent: {top_agent} (${top_agent_pnl:,.2f})\n"
        msg += f"Top Strategy: {top_strategy} (score: {top_strategy_score:.3f})\n"
        msg += f"Regime: {regime}\n"
        msg += f"Drawdown: {drawdown:.2f}%"

        send_telegram(msg)
        print(f"[phase_5600] Daily summary sent: {msg}", flush=True)
    except Exception as e:
        print(f"[phase_5600] Daily summary error: {e}", flush=True)
        traceback.print_exc()


def main() -> None:
    """Main Phase 5600 loop: aggregate metrics and push to dashboard."""
    print(
        f"[phase_5600] Starting Cross-Agent Hive Telemetry @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    last_summary_hour = -1

    while True:
        try:
            # Build meta-metrics
            metrics = build_meta_metrics()

            # Push to dashboard
            success = push_to_meta_metrics(metrics)
            if success:
                print("[phase_5600] Meta-metrics pushed to dashboard", flush=True)
            else:
                print("[phase_5600] Failed to push meta-metrics", flush=True)

            # Daily summary at 09:00 local time
            now = datetime.now()
            current_hour = now.hour
            if current_hour == 9 and last_summary_hour != 9:
                send_daily_summary()
                last_summary_hour = 9
            elif current_hour != 9:
                last_summary_hour = -1  # Reset when not 9 AM

            time.sleep(UPDATE_INTERVAL)

        except KeyboardInterrupt:
            print("[phase_5600] Shutting down gracefully...", flush=True)
            break
        except Exception as e:
            print(f"[phase_5600] Loop error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Performance Attribution - Phase 1800-2000 Enhanced
Real-time P&L tracking, decision attribution, strategy scoring
"""

import json
import os
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
DATA = ROOT / "data"
LOGS = ROOT / "logs"

ATTRIBUTION_FILE = STATE / "performance_attribution.json"
STRATEGY_SCORES = STATE / "strategy_scores.json"


def track_decision(
    agent_name: str, decision: str, reasoning: str, timestamp: str | None = None
) -> None:
    """Track a decision made by an agent."""
    if timestamp is None:
        timestamp = datetime.now(UTC).isoformat()

    decision_data = {
        "agent": agent_name,
        "decision": decision,  # "buy", "sell", "hold", "list_product", etc.
        "reasoning": reasoning,
        "timestamp": timestamp,
        "pnl": None,  # Will be updated later
        "pnl_attributed": False,
    }

    # Load existing attribution data
    if ATTRIBUTION_FILE.exists():
        try:
            data = json.loads(ATTRIBUTION_FILE.read_text())
            decisions = data.get("decisions", [])
        except:
            decisions = []
    else:
        decisions = []

    decisions.append(decision_data)

    # Keep last 1000 decisions
    if len(decisions) > 1000:
        decisions = decisions[-1000:]

    data = {"decisions": decisions, "last_update": datetime.now(UTC).isoformat()}

    ATTRIBUTION_FILE.write_text(json.dumps(data, indent=2))


def update_decision_pnl(decision_idx: int, pnl: float) -> None:
    """Update P&L for a tracked decision."""
    if not ATTRIBUTION_FILE.exists():
        return

    try:
        data = json.loads(ATTRIBUTION_FILE.read_text())
        decisions = data.get("decisions", [])

        if 0 <= decision_idx < len(decisions):
            decisions[decision_idx]["pnl"] = pnl
            decisions[decision_idx]["pnl_attributed"] = True
            data["last_update"] = datetime.now(UTC).isoformat()
            ATTRIBUTION_FILE.write_text(json.dumps(data, indent=2))
    except Exception as e:
        print(f"[performance_attribution] Error updating PnL: {e}", flush=True)


def calculate_strategy_scores() -> dict[str, Any]:
    """Calculate performance scores for each agent/strategy."""
    if not ATTRIBUTION_FILE.exists():
        return {}

    try:
        data = json.loads(ATTRIBUTION_FILE.read_text())
        decisions = data.get("decisions", [])

        # Group by agent
        agent_stats = {}
        for decision in decisions:
            agent = decision.get("agent", "unknown")
            if agent not in agent_stats:
                agent_stats[agent] = {
                    "total_decisions": 0,
                    "total_pnl": 0.0,
                    "winning_decisions": 0,
                    "losing_decisions": 0,
                    "avg_pnl": 0.0,
                    "win_rate": 0.0,
                }

            stats = agent_stats[agent]
            stats["total_decisions"] += 1

            pnl = decision.get("pnl")
            if pnl is not None and decision.get("pnl_attributed"):
                stats["total_pnl"] += pnl
                if pnl > 0:
                    stats["winning_decisions"] += 1
                elif pnl < 0:
                    stats["losing_decisions"] += 1

        # Calculate averages and win rates
        for agent, stats in agent_stats.items():
            if stats["total_decisions"] > 0:
                stats["avg_pnl"] = stats["total_pnl"] / stats["total_decisions"]
                wins = stats["winning_decisions"]
                losses = stats["losing_decisions"]
                if wins + losses > 0:
                    stats["win_rate"] = wins / (wins + losses)

        # Calculate scores (weighted by win rate and avg PnL)
        scores = {}
        for agent, stats in agent_stats.items():
            if stats["total_decisions"] > 10:  # Only score agents with enough data
                score = (stats["win_rate"] * 0.6) + (min(stats["avg_pnl"] / 100, 1.0) * 0.4)
                scores[agent] = {"score": round(score, 3), "stats": stats}

        # Save scores
        result = {"scores": scores, "timestamp": datetime.now(UTC).isoformat()}
        STRATEGY_SCORES.write_text(json.dumps(result, indent=2))

        return result

    except Exception as e:
        print(f"[performance_attribution] Error calculating scores: {e}", flush=True)
        return {}


def main():
    """Main attribution loop."""
    print(
        f"[performance_attribution] Starting performance attribution @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )

    while True:
        try:
            # Calculate strategy scores every hour
            scores = calculate_strategy_scores()
            if scores.get("scores"):
                print(
                    f"[performance_attribution] Calculated scores for {len(scores['scores'])} agents",
                    flush=True,
                )
                for agent, data in scores["scores"].items():
                    print(
                        f"  {agent}: score={data['score']:.3f}, win_rate={data['stats']['win_rate']:.2%}",
                        flush=True,
                    )

            time.sleep(3600)  # Run every hour

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[performance_attribution] Error: {e}", flush=True)
            traceback.print_exc()
            time.sleep(300)


if __name__ == "__main__":
    main()

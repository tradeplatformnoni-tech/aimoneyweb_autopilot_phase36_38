#!/usr/bin/env python3
"""
Intelligent Fix Selector - AI-Powered Fix Selection
====================================================
Uses RCA to select best fix and learn from outcomes.

Features:
- Use RCA to select best fix
- Rank fixes by success probability
- Learn which fixes work best
- Avoid fixes that failed before
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

for d in [STATE, RUNTIME, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

FIX_HISTORY_FILE = STATE / "fix_history.json"
FIX_SUCCESS_RATES_FILE = STATE / "fix_success_rates.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"


class IntelligentFixSelector:
    """Intelligent fix selection system."""

    def __init__(self):
        self.fix_history = self.load_fix_history()
        self.success_rates = self.load_success_rates()

    def load_fix_history(self) -> list[dict[str, Any]]:
        """Load fix history."""
        if FIX_HISTORY_FILE.exists():
            try:
                return json.loads(FIX_HISTORY_FILE.read_text())
            except Exception:
                return []
        return []

    def save_fix_history(self) -> None:
        """Save fix history."""
        try:
            # Keep only last 5000 fixes
            if len(self.fix_history) > 5000:
                self.fix_history = self.fix_history[-5000:]

            FIX_HISTORY_FILE.write_text(json.dumps(self.fix_history, indent=2))
        except Exception:
            pass

    def load_success_rates(self) -> dict[str, dict[str, float]]:
        """Load fix success rates."""
        if FIX_SUCCESS_RATES_FILE.exists():
            try:
                return json.loads(FIX_SUCCESS_RATES_FILE.read_text())
            except Exception:
                return {}
        return {}

    def save_success_rates(self) -> None:
        """Save fix success rates."""
        try:
            FIX_SUCCESS_RATES_FILE.write_text(json.dumps(self.success_rates, indent=2))
        except Exception:
            pass

    def select_best_fix(
        self,
        agent_name: str,
        error_type: str,
        root_cause: Optional[str] = None,
        available_fixes: list[str] = None,
    ) -> dict[str, Any]:
        """Select best fix based on history and success rates."""
        if available_fixes is None:
            available_fixes = [
                "restart_agent",
                "install_module",
                "create_file",
                "retry_with_backoff",
                "increase_timeout",
                "cleanup_resources",
            ]

        # Rank fixes by success probability
        ranked_fixes = []

        for fix_type in available_fixes:
            # Get success rate for this fix type
            success_rate = self._get_success_rate(agent_name, error_type, fix_type)

            # Adjust based on root cause if available
            if root_cause:
                root_cause_rate = self._get_root_cause_success_rate(root_cause, fix_type)
                success_rate = (success_rate + root_cause_rate) / 2.0

            ranked_fixes.append({
                "fix_type": fix_type,
                "success_rate": success_rate,
                "confidence": self._get_confidence(fix_type),
            })

        # Sort by success rate
        ranked_fixes.sort(key=lambda x: x["success_rate"], reverse=True)

        # Select best fix
        best_fix = ranked_fixes[0] if ranked_fixes else None

        return {
            "selected_fix": best_fix["fix_type"] if best_fix else "restart_agent",
            "success_rate": best_fix["success_rate"] if best_fix else 0.5,
            "confidence": best_fix["confidence"] if best_fix else 0.5,
            "alternatives": ranked_fixes[1:4] if len(ranked_fixes) > 1 else [],
        }

    def _get_success_rate(self, agent_name: str, error_type: str, fix_type: str) -> float:
        """Get success rate for fix type."""
        key = f"{agent_name}_{error_type}_{fix_type}"

        if key in self.success_rates:
            return self.success_rates[key].get("success_rate", 0.5)

        # Default success rates based on fix type
        defaults = {
            "restart_agent": 0.7,
            "install_module": 0.9,
            "create_file": 0.8,
            "retry_with_backoff": 0.6,
            "increase_timeout": 0.5,
            "cleanup_resources": 0.7,
        }

        return defaults.get(fix_type, 0.5)

    def _get_root_cause_success_rate(self, root_cause: str, fix_type: str) -> float:
        """Get success rate for fix type given root cause."""
        # Map root causes to best fixes
        root_cause_fixes = {
            "missing_dependency": {"install_module": 0.95, "restart_agent": 0.3},
            "network_issue": {"retry_with_backoff": 0.8, "restart_agent": 0.4},
            "resource_exhaustion": {"cleanup_resources": 0.9, "restart_agent": 0.8},
            "missing_file": {"create_file": 0.95, "restart_agent": 0.2},
            "timeout": {"increase_timeout": 0.7, "retry_with_backoff": 0.6},
        }

        if root_cause in root_cause_fixes:
            return root_cause_fixes[root_cause].get(fix_type, 0.5)

        return 0.5

    def _get_confidence(self, fix_type: str) -> float:
        """Get confidence in fix based on historical data."""
        # Confidence based on number of times fix was used
        total_uses = sum(
            1
            for fix in self.fix_history
            if fix.get("fix_type") == fix_type
        )

        if total_uses > 100:
            return 0.9
        elif total_uses > 50:
            return 0.7
        elif total_uses > 10:
            return 0.5
        else:
            return 0.3

    def record_fix_attempt(
        self,
        agent_name: str,
        error_type: str,
        fix_type: str,
        success: bool,
        root_cause: Optional[str] = None,
    ) -> None:
        """Record fix attempt and update success rates."""
        # Record in history
        self.fix_history.append({
            "agent": agent_name,
            "error_type": error_type,
            "fix_type": fix_type,
            "root_cause": root_cause,
            "success": success,
            "timestamp": datetime.now(UTC).isoformat(),
        })

        # Update success rate
        key = f"{agent_name}_{error_type}_{fix_type}"

        if key not in self.success_rates:
            self.success_rates[key] = {"attempts": 0, "successes": 0, "success_rate": 0.5}

        stats = self.success_rates[key]
        stats["attempts"] += 1
        if success:
            stats["successes"] += 1
        stats["success_rate"] = stats["successes"] / stats["attempts"]

        # Save
        self.save_fix_history()
        self.save_success_rates()


def select_fix(agent_name: str, error_type: str, root_cause: Optional[str] = None) -> dict[str, Any]:
    """Select best fix for error."""
    selector = IntelligentFixSelector()
    return selector.select_best_fix(agent_name, error_type, root_cause)


def record_fix_result(
    agent_name: str,
    error_type: str,
    fix_type: str,
    success: bool,
    root_cause: Optional[str] = None,
) -> None:
    """Record fix result."""
    selector = IntelligentFixSelector()
    selector.record_fix_attempt(agent_name, error_type, fix_type, success, root_cause)


def main() -> None:
    """Main fix selector (typically used by self-healing agent)."""
    print(
        f"[intelligent_fix_selector] 🧠 Intelligent Fix Selector ready @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )


if __name__ == "__main__":
    main()


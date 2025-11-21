#!/usr/bin/env python3
"""
Apply World-Class Utilities to All Agents
------------------------------------------
Systematically applies world-class stability improvements to all agent files.
Ensures paper-mode compatibility.
"""

import os
import sys
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
sys.path.insert(0, str(ROOT))

from utils.agent_wrapper import apply_to_agent_file


def main():
    """Apply world-class utilities to all agents."""
    agents_dir = ROOT / "agents"
    phases_dir = ROOT / "phases"

    applied = 0
    skipped = 0

    # Apply to agents
    for agent_file in agents_dir.glob("*.py"):
        if agent_file.name.startswith("__"):
            continue

        if apply_to_agent_file(agent_file):
            print(f"✅ Applied to: {agent_file.name}")
            applied += 1
        else:
            skipped += 1

    # Apply to phase files (only those with main functions)
    phase_files = [
        phases_dir / "phase_2700_2900_risk_management.py",
        phases_dir / "phase_301_340_equity_replay.py",
        phases_dir / "phase_4300_4500_analytics.py",
    ]

    for phase_file in phase_files:
        if phase_file.exists() and apply_to_agent_file(phase_file):
            print(f"✅ Applied to: {phase_file.name}")
            applied += 1

    print(f"\n✅ Applied to {applied} files")
    print(f"⏭️  Skipped {skipped} files (already have utilities or no main function)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

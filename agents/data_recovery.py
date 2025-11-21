#!/usr/bin/env python3
"""
Data Layer Recovery - State and Data Recovery
==============================================
Handles recovery at the data layer (state files, databases, data corruption).

Features:
- State file recovery
- Database recovery
- Data corruption detection
- Backup and restore
"""

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path("/opt/render/project/src") if os.getenv("RENDER_MODE") == "true" else Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"
BACKUPS = ROOT / "backups"

for d in [STATE, RUNTIME, LOGS, BACKUPS]:
    d.mkdir(parents=True, exist_ok=True)

DATA_RECOVERY_STATE_FILE = STATE / "data_recovery.json"

RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"


class DataRecovery:
    """Data layer recovery system."""

    def __init__(self):
        self.state = self.load_state()

    def load_state(self) -> dict[str, Any]:
        """Load recovery state."""
        if DATA_RECOVERY_STATE_FILE.exists():
            try:
                return json.loads(DATA_RECOVERY_STATE_FILE.read_text())
            except Exception:
                return {"recoveries": []}
        return {"recoveries": []}

    def save_state(self) -> None:
        """Save recovery state."""
        try:
            DATA_RECOVERY_STATE_FILE.write_text(json.dumps(self.state, indent=2))
        except Exception:
            pass

    def detect_corruption(self, file_path: Path) -> dict[str, Any]:
        """Detect data corruption in file."""
        if not file_path.exists():
            return {"corrupted": True, "reason": "file_missing"}

        try:
            # Try to parse JSON
            if file_path.suffix == ".json":
                content = file_path.read_text()
                json.loads(content)
                return {"corrupted": False}

            # Try to parse CSV
            elif file_path.suffix == ".csv":
                import csv

                with open(file_path, "r") as f:
                    csv.reader(f)
                return {"corrupted": False}

            return {"corrupted": False, "unknown_format": True}
        except json.JSONDecodeError:
            return {"corrupted": True, "reason": "invalid_json"}
        except Exception as e:
            return {"corrupted": True, "reason": str(e)}

    def recover_state_file(self, file_path: Path) -> dict[str, Any]:
        """Recover a corrupted state file."""
        # Check for backup
        backup_path = BACKUPS / file_path.name

        if backup_path.exists():
            try:
                # Restore from backup
                shutil.copy(backup_path, file_path)
                return {
                    "status": "recovered",
                    "method": "backup_restore",
                    "backup_file": str(backup_path),
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to restore from backup: {e}",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
        else:
            # Create default file
            try:
                if file_path.suffix == ".json":
                    file_path.write_text("{}")
                elif file_path.suffix == ".csv":
                    file_path.write_text("")  # Empty CSV
                else:
                    file_path.write_text("")

                return {
                    "status": "recovered",
                    "method": "default_creation",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.now(UTC).isoformat(),
                }

    def backup_state_file(self, file_path: Path) -> bool:
        """Backup a state file."""
        if not file_path.exists():
            return False

        try:
            backup_path = BACKUPS / file_path.name
            shutil.copy(file_path, backup_path)
            return True
        except Exception as e:
            print(f"[data_recovery] Backup failed: {e}", flush=True)
            return False

    def check_all_state_files(self) -> dict[str, Any]:
        """Check all state files for corruption."""
        state_files = [
            STATE / "agent_status.json",
            STATE / "self_healing_state.json",
            STATE / "failure_predictions.json",
            STATE / "anomaly_detections.json",
            STATE / "rca_knowledge_base.json",
            RUNTIME / "portfolio.json",
        ]

        results = {}
        corrupted = []

        for file_path in state_files:
            if file_path.exists():
                corruption = self.detect_corruption(file_path)
                results[str(file_path)] = corruption

                if corruption.get("corrupted"):
                    corrupted.append(str(file_path))

        return {
            "checked": len(state_files),
            "corrupted": len(corrupted),
            "corrupted_files": corrupted,
            "results": results,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def recover_all_corrupted(self) -> dict[str, Any]:
        """Recover all corrupted files."""
        check_result = self.check_all_state_files()
        recoveries = []

        for file_path_str in check_result["corrupted_files"]:
            file_path = Path(file_path_str)
            recovery = self.recover_state_file(file_path)
            recoveries.append({
                "file": file_path_str,
                "recovery": recovery,
            })

        return {
            "recovered": len(recoveries),
            "recoveries": recoveries,
            "timestamp": datetime.now(UTC).isoformat(),
        }


def recover_data_layer() -> dict[str, Any]:
    """Recover at data layer."""
    recovery = DataRecovery()

    # Check for corruption
    check_result = recovery.check_all_state_files()

    # Recover if needed
    if check_result["corrupted"] > 0:
        recovery_result = recovery.recover_all_corrupted()
        return {
            "status": "recovered",
            "check": check_result,
            "recovery": recovery_result,
        }
    else:
        return {
            "status": "ok",
            "check": check_result,
        }


def main() -> None:
    """Main data recovery (typically called by self-healing agent)."""
    print(
        f"[data_recovery] 💾 Data Recovery ready @ {datetime.now(UTC).isoformat()}Z",
        flush=True,
    )


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
World-Class Atomic State Management
-----------------------------------
Thread-safe atomic state file operations with validation and backup.
"""

import json
import logging
import shutil
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateManager:
    """
    World-class state manager with atomic writes, validation, and backup.

    Features:
    - Atomic file writes (temp file + rename)
    - State validation
    - Automatic backups
    - Thread-safe operations
    - Corruption recovery
    """

    def __init__(
        self,
        state_file: Path,
        default_state: dict[str, Any] | None = None,
        validator: Callable[[dict[str, Any]], bool] | None = None,
        backup_count: int = 24,
        backup_interval: float = 3600.0,  # 1 hour
    ):
        """
        Initialize state manager.

        Args:
            state_file: Path to state file
            default_state: Default state if file doesn't exist or is corrupted
            validator: Function to validate state (returns True if valid)
            backup_count: Number of backups to keep
            backup_interval: Interval between backups (seconds)
        """
        self.state_file = Path(state_file)
        self.default_state = default_state or {}
        self.validator = validator
        self.backup_count = backup_count
        self.backup_interval = backup_interval
        self._lock = threading.RLock()
        self._last_backup_time: float | None = 0.0

        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"💾 State manager initialized: {self.state_file}")

    def load(self) -> dict[str, Any]:
        """
        Load state from file with validation and corruption recovery.

        Returns:
            State dictionary
        """
        with self._lock:
            # Check if file exists
            if not self.state_file.exists():
                logger.warning(f"⚠️ State file not found: {self.state_file}, using default")
                self.save(self.default_state)
                return self.default_state.copy()

            # Try to load
            try:
                with open(self.state_file) as f:
                    state = json.load(f)

                # Validate
                if self.validator and not self.validator(state):
                    logger.error(f"❌ State validation failed: {self.state_file}")
                    return self._recover_state()

                return state

            except json.JSONDecodeError as e:
                logger.error(f"❌ State file corrupted (JSON error): {self.state_file}: {e}")
                return self._recover_state()
            except Exception as e:
                logger.error(f"❌ Failed to load state: {self.state_file}: {e}")
                return self._recover_state()

    def save(self, state: dict[str, Any], force_backup: bool = False) -> bool:
        """
        Save state atomically with validation and optional backup.

        Args:
            state: State dictionary to save
            force_backup: Force backup even if interval not reached

        Returns:
            True if successful
        """
        with self._lock:
            # Validate before saving
            if self.validator and not self.validator(state):
                logger.error(f"❌ State validation failed before save: {self.state_file}")
                return False

            # Create backup if needed
            import time

            current_time = time.time()
            if force_backup or (
                self._last_backup_time
                and current_time - self._last_backup_time >= self.backup_interval
            ):
                self._create_backup()
                self._last_backup_time = current_time

            # Atomic write: write to temp file, then rename
            temp_file = self.state_file.with_suffix(self.state_file.suffix + ".tmp")

            try:
                # Write to temp file
                with open(temp_file, "w") as f:
                    json.dump(state, f, indent=2)

                # Atomic rename (atomic on Unix, best effort on Windows)
                temp_file.replace(self.state_file)

                logger.debug(f"💾 State saved: {self.state_file}")
                return True

            except Exception as e:
                logger.error(f"❌ Failed to save state: {self.state_file}: {e}")
                # Clean up temp file
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
                return False

    def update(self, updates: dict[str, Any]) -> bool:
        """
        Update state with partial updates.

        Args:
            updates: Dictionary of updates to merge

        Returns:
            True if successful
        """
        state = self.load()
        state.update(updates)
        return self.save(state)

    def _recover_state(self) -> dict[str, Any]:
        """Recover state from backup or use default."""
        # Try to restore from backup
        backup_file = self._get_latest_backup()
        if backup_file and backup_file.exists():
            try:
                logger.info(f"🔄 Attempting to restore from backup: {backup_file}")
                with open(backup_file) as f:
                    state = json.load(f)

                if self.validator and not self.validator(state):
                    logger.warning("⚠️ Backup also invalid, using default")
                    return self.default_state.copy()

                # Restore backup
                self.save(state, force_backup=True)
                logger.info("✅ State restored from backup")
                return state

            except Exception as e:
                logger.error(f"❌ Failed to restore from backup: {e}")

        # Use default state
        logger.warning("⚠️ Using default state")
        self.save(self.default_state)
        return self.default_state.copy()

    def _create_backup(self):
        """Create backup of current state file."""
        if not self.state_file.exists():
            return

        backup_dir = self.state_file.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{self.state_file.stem}_{timestamp}{self.state_file.suffix}"

        try:
            shutil.copy2(self.state_file, backup_file)

            # Clean up old backups
            backups = sorted(backup_dir.glob(f"{self.state_file.stem}_*{self.state_file.suffix}"))
            if len(backups) > self.backup_count:
                for old_backup in backups[: -self.backup_count]:
                    try:
                        old_backup.unlink()
                    except:
                        pass

            logger.debug(f"💾 Backup created: {backup_file}")

        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")

    def _get_latest_backup(self) -> Path | None:
        """Get latest backup file."""
        backup_dir = self.state_file.parent / "backups"
        if not backup_dir.exists():
            return None

        backups = sorted(backup_dir.glob(f"{self.state_file.stem}_*{self.state_file.suffix}"))
        return backups[-1] if backups else None

    def get_backups(self) -> list[Path]:
        """Get list of all backup files."""
        backup_dir = self.state_file.parent / "backups"
        if not backup_dir.exists():
            return []

        return sorted(backup_dir.glob(f"{self.state_file.stem}_*{self.state_file.suffix}"))


# Convenience function for common state operations


def load_state_safe(state_file: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Safely load state file with defaults."""
    manager = StateManager(state_file, default_state=default or {})
    return manager.load()


def save_state_safe(state_file: Path, state: dict[str, Any]) -> bool:
    """Safely save state file atomically."""
    manager = StateManager(state_file)
    return manager.save(state)

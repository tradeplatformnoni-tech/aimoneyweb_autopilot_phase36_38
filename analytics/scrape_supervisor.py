from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

LOGS_DIR = Path("~/neolight/logs").expanduser()
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGER = logging.getLogger("scrape_supervisor")
if not LOGGER.handlers:
    handler = logging.FileHandler(LOGS_DIR / "data_ingestion.log")
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)


ValidationResult = dict[str, Iterable[str]]


@dataclass
class ScraperTask:
    """Definition of a single scraping job with fallbacks and validation."""

    name: str
    runner: Callable[[], dict[str, any]]
    validators: list[Callable[[dict[str, any]], ValidationResult | None]] = field(
        default_factory=list
    )
    fallbacks: list[Callable[[], dict[str, any]]] = field(default_factory=list)
    max_retries: int = 3
    cool_down_seconds: int = 2


class ScrapeSupervisor:
    """
    Coordinates data scraping jobs with retry, fallback, validation, and logging.

    The goal is to keep our ingestion resilient without depending on managed APIs.
    """

    def __init__(self) -> None:
        self.history_dir = Path("~/neolight/logs/data_runs").expanduser()
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def run_task(self, task: ScraperTask) -> dict[str, any] | None:
        attempts = 0
        runners = [task.runner] + task.fallbacks
        last_error: str | None = None

        for runner in runners:
            attempts = 0
            while attempts < task.max_retries:
                attempts += 1
                try:
                    LOGGER.info("Scraper %s attempt %s", task.name, attempts)
                    payload = runner()
                    if payload is None:
                        raise ValueError("Runner returned None payload")

                    validation = self._validate(task, payload)
                    if validation:
                        LOGGER.warning("Scraper %s validation warnings: %s", task.name, validation)
                        self._write_history(task.name, payload, validation)
                        # we treat warnings as soft failure to trigger fallback
                        break

                    LOGGER.info("Scraper %s succeeded", task.name)
                    self._write_history(task.name, payload)
                    return payload

                except Exception as exc:  # pragma: no cover - focused on resilience
                    last_error = str(exc)
                    LOGGER.exception("Scraper %s failed (attempt %s): %s", task.name, attempts, exc)
                    time.sleep(task.cool_down_seconds)
            # if we reach here we move to next fallback runner

        LOGGER.error("Scraper %s exhausted all retries. Last error: %s", task.name, last_error)
        return None

    def _validate(self, task: ScraperTask, payload: dict[str, any]) -> ValidationResult | None:
        warnings: ValidationResult = {}
        for validator in task.validators:
            try:
                result = validator(payload)
                if result:
                    warnings.update(result)
            except Exception as exc:
                LOGGER.exception("Validator failure for task %s: %s", task.name, exc)
        return warnings or None

    def _write_history(
        self,
        task_name: str,
        payload: dict[str, any],
        validation: ValidationResult | None = None,
    ) -> None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        entry = {
            "task": task_name,
            "timestamp": timestamp,
            "validation": validation,
        }
        try:
            history_file = self.history_dir / f"{task_name}_{timestamp}.json"
            history_file.write_text(json.dumps({"meta": entry, "data": payload}, indent=2))
        except Exception as exc:  # pragma: no cover
            LOGGER.error("Could not write scrape history for %s: %s", task_name, exc)


__all__ = ["ScraperTask", "ScrapeSupervisor"]

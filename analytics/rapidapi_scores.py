from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

LOGGER = logging.getLogger(__name__)


class RapidAPIScoresClient:
    """Fallback client to retrieve fixture scores from RapidAPI odds endpoints."""

    BASE_URL = "https://odds-api1.p.rapidapi.com"

    def __init__(self, api_key: str, timeout: int = 15) -> None:
        if not api_key:
            raise ValueError("RAPIDAPI_KEY is required for RapidAPIScoresClient")
        if requests is None:
            raise ImportError("requests must be installed to use RapidAPIScoresClient")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": "odds-api1.p.rapidapi.com",
            }
        )

    def fetch_scores(self, fixture_id: str) -> dict[str, Any] | None:
        """Return score payload for a specific fixture id."""

        if not fixture_id:
            return None
        url = f"{self.BASE_URL}/scores"
        try:
            response = self.session.get(url, params={"fixtureId": fixture_id}, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:  # type: ignore[attr-defined]
            LOGGER.warning(
                "RapidAPI scores request failed",
                extra={"fixture_id": fixture_id, "error": str(exc)},
            )
            return None

        payload: dict[str, Any] = response.json()
        payload["fetched_at"] = datetime.utcnow().isoformat()
        return payload


def persist_scores_snapshot(fixture_id: str, payload: dict[str, Any], destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{fixture_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(_to_json(payload))
    return path


def _to_json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, indent=2, ensure_ascii=False)


__all__ = ["RapidAPIScoresClient", "persist_scores_snapshot"]

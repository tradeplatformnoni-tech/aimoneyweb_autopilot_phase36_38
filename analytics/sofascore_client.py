from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Any

import requests

LOGGER = logging.getLogger("sofascore")

USER_AGENT = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    )
}


class SofaScoreClient:
    BASE_URL = "https://api.sofascore.com/api/v1"

    def __init__(self, sport: str) -> None:
        self.sport = sport
        self.session = requests.Session()
        self.session.headers.update(USER_AGENT)

    def _request(self, path: str) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response.json()

    def fetch_events(self, days: int = 2) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        today = date.today()
        for offset in range(days + 1):
            target_day = (today + timedelta(days=offset)).isoformat()
            endpoint = f"/sport/{self.sport}/scheduled-events/{target_day}"
            try:
                payload = self._request(endpoint)
            except requests.HTTPError as exc:
                LOGGER.warning(
                    "SofaScore events fetch failed",
                    extra={"sport": self.sport, "endpoint": endpoint, "error": str(exc)},
                )
                continue
            events.extend(payload.get("events") or [])
        return events

    def fetch_event_odds(self, event_id: int) -> dict[str, Any] | None:
        try:
            return self._request(f"/event/{event_id}/odds/1/all")
        except requests.HTTPError as exc:
            LOGGER.warning(
                "SofaScore odds fetch failed",
                extra={"sport": self.sport, "event_id": event_id, "error": str(exc)},
            )
            return None


def _normalise_label(label: str | None) -> str:
    return (label or "").strip().lower()


def select_moneyline_market(markets: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    primary_keywords = (
        "moneyline",
        "match winner",
        "match odds",
        "full time",
        "fulltime",
        "game winner",
        "1x2",
        "main result",
    )
    secondary_keywords = ("winner",)

    fallback: dict[str, Any] | None = None
    secondary_match: dict[str, Any] | None = None

    for market in markets:
        name = _normalise_label(market.get("marketName") or market.get("name"))
        if not fallback:
            fallback = market
        if any(keyword in name for keyword in primary_keywords):
            return market
        if not secondary_match and any(keyword in name for keyword in secondary_keywords):
            secondary_match = market

    return secondary_match or fallback


def extract_decimal_price(container: dict[str, Any]) -> float | None:
    candidate_keys = ("decimalOdds", "decimal", "value", "odds")
    for key in candidate_keys:
        if key in container:
            try:
                return float(container[key])
            except (TypeError, ValueError):
                continue
    for list_key in ("bookmakers", "odds", "values", "providers"):
        for entry in container.get(list_key, []) or []:
            price = extract_decimal_price(entry)
            if price is not None:
                return price
    return None


def infer_outcome_slot(
    labels: Iterable[str],
    home_name: str,
    away_name: str,
) -> str | None:
    home_name = _normalise_label(home_name)
    away_name = _normalise_label(away_name)

    for label in labels:
        if not label:
            continue
        normalised = _normalise_label(label)
        if normalised in {"1", "home"} or normalised == home_name:
            return "home"
        if normalised in {"2", "away"} or normalised == away_name:
            return "away"
        if normalised in {"x", "draw", "tie"}:
            return "draw"
    return None


def extract_moneyline_prices(
    market: dict[str, Any] | None,
    home_team: str,
    away_team: str,
) -> dict[str, float | None]:
    """Extract decimal odds for the provided market, favouring BetMGM when available."""

    prices = {"home": None, "away": None, "draw": None}
    if not market:
        return prices

    def _fractional_to_decimal(value: str | None) -> float | None:
        if not value or "/" not in value:
            return None
        try:
            numerator, denominator = value.split("/", 1)
            numerator_f = float(numerator)
            denominator_f = float(denominator)
            if denominator_f == 0:
                return None
            return 1.0 + numerator_f / denominator_f
        except (ValueError, ZeroDivisionError):
            return None

    bookmakers = market.get("bookmakers") or []
    choice_sources: Iterable[dict[str, Any]]

    if bookmakers:

        def bookmaker_priority(bookmaker: dict[str, Any]) -> tuple[int, str]:
            name = (bookmaker.get("name") or "").lower()
            # Prefer BetMGM, then other major books alphabetically.
            return (0 if "betmgm" in name else 1, name)

        bookmaker = sorted(bookmakers, key=bookmaker_priority)[0]
        choice_sources = bookmaker.get("odds") or bookmaker.get("choices") or []
    else:
        choice_sources = market.get("choices") or []

    for entry in choice_sources:
        label = (
            entry.get("label")
            or entry.get("name")
            or entry.get("choiceName")
            or entry.get("outcome")
            or entry.get("choice")
            or ""
        ).lower()
        target = None
        if label in ("1", "home", "h") or home_team.lower() in label:
            target = "home"
        elif label in ("2", "away", "a") or away_team.lower() in label:
            target = "away"
        elif label in ("x", "draw", "tie"):
            target = "draw"

        if not target:
            continue

        raw_value = entry.get("decimalOdds") or entry.get("value") or entry.get("odds")
        if raw_value is None:
            raw_value = _fractional_to_decimal(
                entry.get("fractionalValue") or entry.get("initialFractionalValue")
            )
        try:
            prices[target] = float(raw_value)
        except (TypeError, ValueError):
            continue

    return prices


def to_iso(timestamp: int | None) -> str | None:
    if not timestamp:
        return None
    try:
        return datetime.utcfromtimestamp(int(timestamp)).isoformat()
    except (TypeError, ValueError, OSError):
        return None


__all__ = [
    "SofaScoreClient",
    "select_moneyline_market",
    "extract_moneyline_prices",
    "to_iso",
]

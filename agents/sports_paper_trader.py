#!/usr/bin/env python3
"""Sports Paper Trading Agent - Simulate betting without real money.

Tracks predictions, simulates bet placement, records outcomes, and calculates
P&L to validate the system before risking real capital. Mirrors SmartTrader paper mode.
"""

from __future__ import annotations

import json
import math
import os
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"

PAPER_LOG = STATE / "sports_paper_trades.json"
PAPER_SUMMARY = STATE / "sports_paper_summary.json"

CLV_LOG = STATE / "sports_paper_clv.json"

PAPER_MODE = os.getenv("SPORTS_PAPER_MODE", "true").lower() == "true"
PAPER_BANKROLL = float(os.getenv("SPORTS_PAPER_BANKROLL", "10000"))
MIN_CONFIDENCE = float(os.getenv("SPORTS_PAPER_MIN_CONFIDENCE", "0.65"))
CLV_STEAM_THRESHOLD = float(os.getenv("SPORTS_CLV_STEAM_THRESHOLD", "0.02"))
CLV_NEGATIVE_ALERT = float(os.getenv("SPORTS_CLV_NEGATIVE_ALERT", "-0.01"))
CLV_TARGET_ALERT = float(os.getenv("SPORTS_CLV_TARGET_ALERT", "0.03"))
CLV_STEAM_ALERT_COUNT = int(os.getenv("SPORTS_CLV_STEAM_ALERT_COUNT", "5"))

DATA = ROOT / "data"
ODDS_SNAPSHOT_DIR = DATA / "odds_snapshots"

for directory in (STATE, LOGS, DATA, ODDS_SNAPSHOT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

LEAGUE_ALIASES = {
    "seriea": "Serie A",
    "laliga": "La Liga",
    "bundesliga": "Bundesliga",
    "epl": "Premier League",
    "premierleague": "Premier League",
    "ligue1": "Ligue 1",
    "championsleague": "Champions League",
    "nba": "NBA",
    "wnba": "WNBA",
    "nfl": "NFL",
    "mlb": "MLB",
}

_ODDS_CACHE: dict[str, dict[str, list[Any]]] = {}


def log(message: str) -> None:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def load_paper_trades() -> list[dict[str, Any]]:
    """Load paper trading history."""
    if not PAPER_LOG.exists():
        return []
    try:
        with PAPER_LOG.open() as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_paper_trade(trade: dict[str, Any]) -> None:
    """Save a paper trade."""
    trades = load_paper_trades()
    trades.append(trade)
    PAPER_LOG.write_text(json.dumps(trades, indent=2))
    update_clv_log(trades)


def load_predictions() -> dict[str, Any]:
    """Load Einstein queue (top-ranked opportunities)."""
    einstein_file = STATE / "sports_einstein_queue.json"
    if not einstein_file.exists():
        return {}

    try:
        with einstein_file.open() as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def simulate_bet_placement(opportunity: dict[str, Any]) -> dict[str, Any]:
    """
    Simulate placing a bet and record it for later settlement.

    Returns a paper trade record.
    """
    sport = opportunity.get("sport")
    scheduled_raw = opportunity.get("scheduled")
    league = extract_league(opportunity.get("game_id"), sport)
    regime = infer_regime(opportunity.get("game_id"), sport, scheduled_raw)
    scheduled_iso = normalize_scheduled(opportunity.get("game_id"), scheduled_raw)

    decimal_odds = opportunity.get("decimal_odds")
    try:
        bet_implied_prob = round(1.0 / float(decimal_odds), 6) if decimal_odds else None
    except (TypeError, ValueError):
        bet_implied_prob = None

    return {
        "id": f"paper_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{opportunity['game_id']}",
        "game_id": opportunity["game_id"],
        "sport": sport,
        "league": league,
        "regime": regime,
        "scheduled": scheduled_iso,
        "home_team": opportunity["home_team"],
        "away_team": opportunity["away_team"],
        "recommended_side": opportunity["recommended_side"],
        "stake": opportunity["recommended_stake"],
        "decimal_odds": decimal_odds,
        "bet_implied_prob": bet_implied_prob,
        "confidence": opportunity.get("confidence"),
        "edge": opportunity.get("edge"),
        "expected_value": opportunity.get("expected_value"),
        "implied_home_prob": opportunity.get("implied_home_prob"),
        "implied_away_prob": opportunity.get("implied_away_prob"),
        "einstein_score": opportunity.get("einstein_score"),
        "placed_at": datetime.now(UTC).isoformat(),
        "status": "pending",
        "result": None,
        "pnl": 0.0,
    }


def american_to_prob(odds: float | None) -> float | None:
    if odds is None:
        return None
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return None
    if odds > 0:
        return 100.0 / (odds + 100.0)
    if odds < 0:
        return -odds / (-odds + 100.0)
    return 0.5


def american_to_decimal(odds: float | None) -> float | None:
    if odds is None:
        return None
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return None
    if odds > 0:
        return round(1.0 + odds / 100.0, 4)
    if odds < 0:
        return round(1.0 + 100.0 / -odds, 4)
    return 2.0


def parse_iso(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_league(game_id: str | None, sport: str | None = None) -> str:
    if game_id:
        prefix = game_id.split("_")[0]
        if prefix:
            normalized = prefix.lower()
            alias = LEAGUE_ALIASES.get(normalized)
            if alias:
                return alias
            return prefix.replace("-", " ").title()
    sport = (sport or "").lower()
    if sport in {"nba", "wnba"}:
        return sport.upper()
    if sport == "soccer":
        return "Soccer"
    if sport == "nfl":
        return "NFL"
    return sport.title() if sport else "Unknown"


def _parse_game_date(game_id: str | None, scheduled: str | None = None) -> datetime | None:
    candidates: list[str] = []
    if scheduled:
        candidates.append(str(scheduled))
    if game_id:
        candidates.extend(game_id.split("_"))
    for token in candidates:
        token = token.strip()
        if not token:
            continue
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
            try:
                return datetime.strptime(token, fmt)
            except ValueError:
                continue
    return None


def normalize_scheduled(game_id: str | None, scheduled: str | None) -> str | None:
    parsed = _parse_game_date(game_id, scheduled)
    if parsed:
        return parsed.date().isoformat()
    return scheduled


def infer_regime(game_id: str | None, sport: str | None, scheduled: str | None = None) -> str:
    sport = (sport or "").lower()
    game_date = _parse_game_date(game_id, scheduled)
    if not game_date:
        return "regular"
    month = game_date.month
    if sport == "nba":
        if month in {4, 5, 6}:
            return "playoffs"
        if month in {10, 11, 12}:
            return "early_season"
        return "regular"
    if sport == "soccer":
        if month in {8, 9}:
            return "season_start"
        if month in {4, 5}:
            return "title_run_in"
        return "regular"
    return "regular"


def _load_odds_cache(sport: str) -> dict[str, list[Any]]:
    sport = sport.lower()
    if sport in _ODDS_CACHE:
        return _ODDS_CACHE[sport]
    try:
        if sport == "nba":
            from analytics.sports_data_manager import load_local_nba_odds

            odds_records = load_local_nba_odds()
        elif sport == "soccer":
            from analytics.sports_data_manager import load_local_soccer_odds

            odds_records = load_local_soccer_odds()
        else:
            odds_records = []
    except Exception as exc:
        log(f"[paper] Failed to load odds cache for {sport}: {exc}")
        odds_records = []

    lookup: dict[str, list[Any]] = defaultdict(list)
    for record in odds_records:
        lookup[record.game_id].append(record)
    for series in lookup.values():
        series.sort(
            key=lambda r: parse_iso(getattr(r, "collected_at", ""))
            or datetime.min.replace(tzinfo=UTC)
        )
    _ODDS_CACHE[sport] = lookup
    return lookup


def get_closing_odds(game_id: str, sport: str) -> dict[str, float | None]:
    series = _load_odds_cache(sport).get(game_id, [])
    if not series:
        return {
            "home_prob": None,
            "away_prob": None,
            "home_decimal": None,
            "away_decimal": None,
            "collected_at": None,
        }
    try:
        snapshot_dir = ODDS_SNAPSHOT_DIR / sport
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / f"{game_id}.json"
        snapshot_payload = []
        for record in series:
            if hasattr(record, "to_dict"):
                snapshot_payload.append(record.to_dict())
            else:
                snapshot_payload.append(record.__dict__)
        snapshot_path.write_text(json.dumps(snapshot_payload, indent=2))
    except Exception:
        pass
    latest = series[-1]
    return {
        "home_prob": american_to_prob(getattr(latest, "home_price", None)),
        "away_prob": american_to_prob(getattr(latest, "away_price", None)),
        "home_decimal": american_to_decimal(getattr(latest, "home_price", None)),
        "away_decimal": american_to_decimal(getattr(latest, "away_price", None)),
        "collected_at": getattr(latest, "collected_at", None),
    }


def classify_steam(open_prob: float | None, closing_prob: float | None) -> str:
    if open_prob is None or closing_prob is None:
        return "unknown"
    delta = closing_prob - open_prob
    if delta >= CLV_STEAM_THRESHOLD:
        return "toward_model"
    if delta <= -CLV_STEAM_THRESHOLD:
        return "against_model"
    return "flat"


def calculate_clv(open_prob: float | None, closing_prob: float | None) -> float | None:
    if open_prob in (None, 0) or closing_prob is None:
        return None
    return (closing_prob - open_prob) / open_prob


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 4)
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * pct
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(sorted_vals[int(k)], 4)
    lower = sorted_vals[f]
    upper = sorted_vals[c]
    return round(lower + (upper - lower) * (k - f), 4)


def summarize_periods(records: dict[str, list[float]], top_n: int = 3) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for period, values in records.items():
        clean = [v for v in values if v is not None]
        if not clean:
            continue
        summary.append(
            {
                "period": period,
                "avg_clv": round(sum(clean) / len(clean), 4),
                "samples": len(clean),
            }
        )
    summary.sort(key=lambda item: item["avg_clv"], reverse=True)
    return summary[:top_n]


def aggregate_breakdown(trades: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        label = str(trade.get(key) or "unknown").strip() or "unknown"
        buckets[label].append(trade)

    breakdown: list[dict[str, Any]] = []
    for label, items in buckets.items():
        clv_values = [float(t.get("clv")) for t in items if isinstance(t.get("clv"), (int, float))]
        total_stake = 0.0
        total_pnl = 0.0
        roi_values: list[float] = []
        pnl_series: list[float] = []
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0

        sorted_items = sorted(
            items,
            key=lambda t: (
                t.get("settled_at") or t.get("placed_at") or "",
                t.get("id") or "",
            ),
        )

        for trade in sorted_items:
            stake = trade.get("stake")
            pnl = trade.get("pnl")
            if isinstance(stake, (int, float)) and stake > 0:
                stake_float = float(stake)
                total_stake += stake_float
                if isinstance(pnl, (int, float)):
                    pnl_float = float(pnl)
                    total_pnl += pnl_float
                    roi_values.append(pnl_float / stake_float)
                    pnl_series.append(pnl_float)
                    cumulative += pnl_float
                    peak = max(peak, cumulative)
                    drawdown = peak - cumulative
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
            elif isinstance(pnl, (int, float)):
                pnl_float = float(pnl)
                total_pnl += pnl_float
                pnl_series.append(pnl_float)
                cumulative += pnl_float
                peak = max(peak, cumulative)
                drawdown = peak - cumulative
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        avg_clv = sum(clv_values) / len(clv_values) if clv_values else None
        positive_rate = (
            sum(1 for value in clv_values if value > 0) / len(clv_values) if clv_values else None
        )
        avg_roi = sum(roi_values) / len(roi_values) if roi_values else None
        roi_std = statistics.pstdev(roi_values) if len(roi_values) >= 2 else None
        roi_var = statistics.pvariance(roi_values) if len(roi_values) >= 2 else None
        pnl_var = statistics.pvariance(pnl_series) if len(pnl_series) >= 2 else None

        breakdown.append(
            {
                key: label,
                "count": len(items),
                "avg_clv": round(avg_clv, 4) if avg_clv is not None else None,
                "positive_rate": round(positive_rate, 4) if positive_rate is not None else None,
                "avg_roi": round(avg_roi, 4) if avg_roi is not None else None,
                "roi_std": round(roi_std, 4) if roi_std is not None else None,
                "roi_var": round(roi_var, 4) if roi_var is not None else None,
                "pnl_variance": round(pnl_var, 4) if pnl_var is not None else None,
                "max_drawdown": round(max_drawdown, 2) if max_drawdown else 0.0,
                "total_staked": round(total_stake, 2),
                "total_pnl": round(total_pnl, 2),
            }
        )
    breakdown.sort(key=lambda entry: entry.get("avg_clv") or 0.0, reverse=True)
    return breakdown


def build_postgame_reviews(trades: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    settled = [
        trade
        for trade in trades
        if trade.get("result") is not None and isinstance(trade.get("stake"), (int, float))
    ]
    settled.sort(key=lambda t: t.get("settled_at") or "", reverse=True)
    reviews: list[dict[str, Any]] = []
    for trade in settled[:limit]:
        stake = float(trade.get("stake") or 0.0)
        pnl = float(trade.get("pnl") or 0.0)
        roi = (pnl / stake) if stake else None
        clv = trade.get("clv")
        notes = []
        if isinstance(clv, (int, float)):
            notes.append(f"CLV {clv * 100:.2f}%")
        edge = trade.get("edge")
        if isinstance(edge, (int, float)):
            notes.append(f"Edge {edge * 100:.2f}%")
        steam = trade.get("steam_direction", "unknown")
        if steam:
            notes.append(f"Steam {steam}")
        closing_prob = trade.get("closing_implied_prob")
        if isinstance(closing_prob, (int, float)):
            notes.append(f"Close {closing_prob * 100:.1f}%")
        reviews.append(
            {
                "game_id": trade.get("game_id"),
                "sport": trade.get("sport"),
                "league": trade.get("league"),
                "regime": trade.get("regime"),
                "result": trade.get("result"),
                "clv": clv,
                "roi": roi,
                "steam_direction": steam,
                "edge": edge,
                "confidence": trade.get("confidence"),
                "closing_implied_prob": closing_prob,
                "notes": "; ".join(notes),
                "settled_at": trade.get("settled_at"),
            }
        )
    return reviews


def build_learning_insights(by_regime: list[dict[str, Any]]) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    for entry in by_regime:
        regime = entry.get("regime", "unknown")
        avg_clv = entry.get("avg_clv")
        avg_roi = entry.get("avg_roi")
        if avg_clv is None or avg_roi is None:
            continue
        if avg_clv > 0 and avg_roi < 0:
            insights.append(
                {
                    "regime": regime,
                    "action": "review_execution",
                    "reason": "Positive CLV but negative ROI — investigate pricing drift or bet sizing.",
                }
            )
        elif avg_clv < 0:
            insights.append(
                {
                    "regime": regime,
                    "action": "retrain_models",
                    "reason": "Negative CLV suggests the model is losing edge in this regime.",
                }
            )
    return insights


def update_clv_log(trades: list[dict[str, Any]]) -> dict[str, Any] | None:
    enriched: list[dict[str, Any]] = []
    weekly: dict[str, list[float]] = defaultdict(list)
    monthly: dict[str, list[float]] = defaultdict(list)
    steam_counter: Counter = Counter()
    positive_clv_pnl = 0.0
    negative_clv_pnl = 0.0
    positive_clv_stake = 0.0
    negative_clv_stake = 0.0
    pnl_samples: list[float] = []

    for trade in trades:
        sport = trade.get("sport")
        league = trade.get("league") or extract_league(trade.get("game_id"), sport)
        scheduled = normalize_scheduled(trade.get("game_id"), trade.get("scheduled"))
        regime = trade.get("regime") or infer_regime(trade.get("game_id"), sport, scheduled)
        steam_direction = (trade.get("steam_direction") or "unknown").lower()

        record: dict[str, Any] = {
            "id": trade.get("id"),
            "game_id": trade.get("game_id"),
            "sport": sport,
            "league": league,
            "regime": regime,
            "scheduled": scheduled,
            "recommended_side": trade.get("recommended_side"),
            "stake": trade.get("stake"),
            "decimal_odds": trade.get("decimal_odds"),
            "bet_implied_prob": trade.get("bet_implied_prob"),
            "edge": trade.get("edge"),
            "confidence": trade.get("confidence"),
            "placed_at": trade.get("placed_at"),
            "status": trade.get("status"),
        }
        record["implied_home_prob"] = trade.get("implied_home_prob")
        record["implied_away_prob"] = trade.get("implied_away_prob")
        record["einstein_score"] = trade.get("einstein_score")
        record["closing_decimal_odds"] = trade.get("closing_decimal_odds")
        record["closing_implied_prob"] = trade.get("closing_implied_prob")
        record["closing_timestamp"] = trade.get("closing_timestamp")
        record["clv"] = trade.get("clv")
        record["steam_direction"] = steam_direction
        record["result"] = trade.get("result")
        record["pnl"] = trade.get("pnl")
        record["settled_at"] = trade.get("settled_at")
        enriched.append(record)

        placed_dt = parse_iso(trade.get("placed_at"))
        clv_value = record.get("clv")
        if placed_dt and clv_value is not None:
            iso_week = placed_dt.isocalendar()
            weekly[f"{iso_week.year}-W{iso_week.week:02d}"].append(clv_value)
            monthly[f"{placed_dt.year}-{placed_dt.month:02d}"].append(clv_value)

        steam_counter[steam_direction] += 1

        stake = record.get("stake")
        pnl = record.get("pnl")
        if isinstance(clv_value, (int, float)) and isinstance(stake, (int, float)) and stake:
            if clv_value > 0:
                positive_clv_pnl += pnl or 0.0
                positive_clv_stake += stake or 0.0
            else:
                negative_clv_pnl += pnl or 0.0
                negative_clv_stake += stake or 0.0
        if isinstance(pnl, (int, float)):
            pnl_samples.append(pnl)

    clv_values = [rec["clv"] for rec in enriched if rec.get("clv") is not None]
    total = len(clv_values)
    positive = len([v for v in clv_values if v > 0])
    distribution = {
        "count": total,
        "average": round(sum(clv_values) / total, 4) if total else None,
        "median": percentile(clv_values, 0.5),
        "p75": percentile(clv_values, 0.75),
        "p90": percentile(clv_values, 0.9),
        "positive_rate": round(positive / total, 4) if total else None,
    }

    def compute_cvar(samples: list[float], alpha: float) -> float | None:
        if not samples:
            return None
        sorted_vals = sorted(samples)
        tail_len = max(1, int(round(len(sorted_vals) * (1 - alpha))))
        tail = sorted_vals[:tail_len]
        return round(sum(tail) / len(tail), 2)

    settled_trades = [record for record in enriched if record.get("result") is not None]

    def build_curve(label: str, predicate) -> dict[str, Any]:
        filtered = [trade for trade in settled_trades if predicate(trade)]
        filtered.sort(
            key=lambda t: (
                t.get("settled_at") or t.get("placed_at") or "",
                t.get("id") or "",
            )
        )
        bankroll = PAPER_BANKROLL
        max_bankroll = bankroll
        max_drawdown = 0.0
        pnl_series: list[float] = []
        roi_series: list[float] = []
        points: list[dict[str, Any]] = []

        for trade in filtered:
            pnl = float(trade.get("pnl") or 0.0)
            stake = trade.get("stake")
            bankroll = round(bankroll + pnl, 2)
            timestamp = trade.get("settled_at") or trade.get("placed_at")
            points.append({"time": timestamp, "bankroll": bankroll})
            max_bankroll = max(max_bankroll, bankroll)
            drawdown = max_bankroll - bankroll
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            pnl_series.append(pnl)
            if isinstance(stake, (int, float)) and stake:
                roi_series.append(pnl / float(stake))

        final_pnl = bankroll - PAPER_BANKROLL
        roi_mean = statistics.mean(roi_series) if roi_series else None
        roi_std = statistics.pstdev(roi_series) if len(roi_series) >= 2 else None
        roi_var = statistics.pvariance(roi_series) if len(roi_series) >= 2 else None
        pnl_var = statistics.pvariance(pnl_series) if len(pnl_series) >= 2 else None

        return {
            "label": label,
            "trade_count": len(filtered),
            "points": points,
            "final_bankroll": round(bankroll, 2),
            "final_pnl": round(final_pnl, 2),
            "max_drawdown": round(max_drawdown, 2) if max_drawdown else 0.0,
            "roi_mean": round(roi_mean, 4) if roi_mean is not None else None,
            "roi_std": round(roi_std, 4) if roi_std is not None else None,
            "roi_var": round(roi_var, 4) if roi_var is not None else None,
            "pnl_variance": round(pnl_var, 4) if pnl_var is not None else None,
            "cvar_95": compute_cvar(pnl_series, 0.95),
            "cvar_99": compute_cvar(pnl_series, 0.99),
        }

    portfolio_curves = [
        build_curve("All Trades", lambda _: True),
        build_curve(
            "Positive CLV",
            lambda trade: isinstance(trade.get("clv"), (int, float)) and trade["clv"] > 0,
        ),
        build_curve(
            "Steam Toward Model",
            lambda trade: (trade.get("steam_direction") or "").lower() == "toward_model",
        ),
        build_curve(
            "Steam Against Model",
            lambda trade: (trade.get("steam_direction") or "").lower() == "against_model",
        ),
    ]

    portfolio_scenarios = [
        {
            "label": curve["label"],
            "trade_count": curve["trade_count"],
            "final_bankroll": curve["final_bankroll"],
            "final_pnl": curve["final_pnl"],
            "max_drawdown": curve["max_drawdown"],
            "roi_mean": curve["roi_mean"],
            "roi_std": curve["roi_std"],
            "cvar_95": curve["cvar_95"],
            "cvar_99": curve["cvar_99"],
        }
        for curve in portfolio_curves
    ]

    portfolio_metrics = {
        "positive_clv": {
            "pnl": round(positive_clv_pnl, 2),
            "roi": round(
                (positive_clv_pnl / positive_clv_stake * 100) if positive_clv_stake else 0.0, 2
            ),
        },
        "negative_clv": {
            "pnl": round(negative_clv_pnl, 2),
            "roi": round(
                (negative_clv_pnl / negative_clv_stake * 100) if negative_clv_stake else 0.0, 2
            ),
        },
        "cvar": {
            "cvar_95": compute_cvar(pnl_samples, 0.95),
            "cvar_99": compute_cvar(pnl_samples, 0.99),
        },
        "curves": portfolio_curves,
        "scenarios": portfolio_scenarios,
    }

    by_sport = aggregate_breakdown(enriched, "sport")
    by_league = aggregate_breakdown(enriched, "league")
    by_regime = aggregate_breakdown(enriched, "regime")
    by_steam = aggregate_breakdown(enriched, "steam_direction")
    postgame_reviews = build_postgame_reviews(enriched)
    learning_insights = build_learning_insights(by_regime)

    summary_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "distribution": distribution,
        "weekly_leaders": summarize_periods(weekly),
        "monthly_leaders": summarize_periods(monthly),
        "steam_summary": dict(steam_counter),
        "portfolio": portfolio_metrics,
        "by_sport": by_sport,
        "by_league": by_league,
        "by_regime": by_regime,
        "by_steam": by_steam,
        "postgame_reviews": postgame_reviews,
        "learning_insights": learning_insights,
        "flags": {
            "steam_against": [
                rec["id"]
                for rec in enriched
                if rec.get("steam_direction") == "against_model" and (rec.get("clv") or 0.0) < 0
            ],
            "steam_toward": [
                rec["id"]
                for rec in enriched
                if rec.get("steam_direction") == "toward_model" and (rec.get("clv") or 0.0) > 0
            ],
        },
    }

    summary_payload["league_breakdown"] = {
        entry.get("league", "unknown"): {
            "count": entry.get("count", 0),
            "avg_clv": entry.get("avg_clv"),
            "pnl": entry.get("total_pnl"),
            "roi": round((entry.get("avg_roi") or 0.0) * 100, 2)
            if entry.get("avg_roi") is not None
            else None,
        }
        for entry in by_league
    }
    summary_payload["regime_breakdown"] = {
        entry.get("regime", "unknown"): {
            "count": entry.get("count", 0),
            "avg_clv": entry.get("avg_clv"),
            "pnl": entry.get("total_pnl"),
            "roi": round((entry.get("avg_roi") or 0.0) * 100, 2)
            if entry.get("avg_roi") is not None
            else None,
        }
        for entry in by_regime
    }

    CLV_LOG.write_text(json.dumps({"trades": enriched, "summary": summary_payload}, indent=2))
    return summary_payload


def maybe_send_clv_alerts(clv_summary: dict[str, Any] | None) -> None:
    if not clv_summary:
        return
    try:
        from analytics.telegram_notifier import send_alert
    except Exception:
        send_alert = None

    distribution = clv_summary.get("distribution", {})
    avg_clv = distribution.get("average")
    steam_against = clv_summary.get("steam_summary", {}).get("against_model", 0)
    weekly_leaders = clv_summary.get("weekly_leaders", [])
    monthly_leaders = clv_summary.get("monthly_leaders", [])

    messages: list[str] = []
    if avg_clv is not None and avg_clv <= CLV_NEGATIVE_ALERT:
        messages.append(
            f"⚠️ Average CLV dropped to {avg_clv:.2%}. Review recent edges before going live."
        )
    if steam_against >= CLV_STEAM_ALERT_COUNT:
        messages.append(
            f"⚠️ Steam against the model detected {steam_against} times this cycle. Consider tightening filters."
        )
    top_week = weekly_leaders[0] if weekly_leaders else None
    if top_week and top_week.get("avg_clv") is not None and top_week["avg_clv"] >= CLV_TARGET_ALERT:
        messages.append(
            f"✅ Weekly leader {top_week['period']} hitting {top_week['avg_clv']:.2%} CLV."
        )
    top_month = monthly_leaders[0] if monthly_leaders else None
    if (
        top_month
        and top_month.get("avg_clv") is not None
        and top_month["avg_clv"] >= CLV_TARGET_ALERT
    ):
        messages.append(
            f"✅ Monthly leader {top_month['period']} delivering {top_month['avg_clv']:.2%} CLV."
        )

    if messages and send_alert:
        summary = "\n".join(messages)
        try:
            send_alert(f"📈 **CLV Intelligence Alert**\n\n{summary}")
        except Exception:
            pass


def settle_paper_trades(trades: list[dict[str, Any]]) -> None:
    """
    Check for completed games and settle paper trades.

    Uses local game history to determine winners.
    """
    updated = False

    for trade in trades:
        if trade["status"] != "pending":
            continue

        game_id = trade["game_id"]
        sport = trade["sport"]

        # Try to find the game result in history
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).parent.parent))
        try:
            from analytics.sports_data_manager import (
                load_local_nba_history,
                load_local_soccer_history,
            )
        except ImportError as e:
            log(f"⚠️ Could not import sports_data_manager for {game_id}: {e}")
            continue

        if sport == "nba":
            history = load_local_nba_history()
        elif sport == "soccer":
            history = load_local_soccer_history()
        else:
            continue

        if not trade.get("league"):
            trade["league"] = extract_league(game_id, sport)
        normalized_scheduled = normalize_scheduled(game_id, trade.get("scheduled"))
        if normalized_scheduled:
            trade["scheduled"] = normalized_scheduled
        if not trade.get("regime"):
            trade["regime"] = infer_regime(game_id, sport, trade.get("scheduled"))

        # Find matching game
        game = next((g for g in history if g.game_id == game_id), None)
        if not game or game.home_score is None or game.away_score is None:
            continue

        # Determine winner
        if game.home_score > game.away_score:
            winner = game.home_team
        elif game.away_score > game.home_score:
            winner = game.away_team
        else:
            winner = "draw"

        # Calculate P&L
        stake = trade["stake"]
        decimal_odds = trade.get("decimal_odds")
        try:
            decimal_odds = float(decimal_odds)
        except (TypeError, ValueError):
            decimal_odds = 0.0
        recommended_side = trade["recommended_side"]

        if winner == recommended_side:
            # Win
            payout = stake * decimal_odds
            pnl = payout - stake
            result = "win"
        elif winner == "draw" and sport == "soccer":
            # Push (rare in 2-way markets)
            pnl = 0.0
            result = "push"
        else:
            # Loss
            pnl = -stake
            result = "loss"

        # Update trade
        trade["status"] = "settled"
        trade["result"] = result
        trade["pnl"] = round(pnl, 2)
        trade["settled_at"] = datetime.now(UTC).isoformat()
        trade["actual_winner"] = winner
        trade["home_score"] = game.home_score
        trade["away_score"] = game.away_score

        closing = get_closing_odds(game_id, sport)
        if recommended_side == trade.get("home_team"):
            closing_prob = closing.get("home_prob")
            closing_decimal = closing.get("home_decimal")
        elif recommended_side == trade.get("away_team"):
            closing_prob = closing.get("away_prob")
            closing_decimal = closing.get("away_decimal")
        else:
            closing_prob = None
            closing_decimal = None

        trade["closing_implied_prob"] = closing_prob
        trade["closing_decimal_odds"] = closing_decimal
        trade["closing_timestamp"] = closing.get("collected_at")

        open_prob = trade.get("bet_implied_prob")
        clv_value = calculate_clv(open_prob, closing_prob)
        trade["clv"] = round(clv_value, 4) if clv_value is not None else None
        trade["steam_direction"] = classify_steam(open_prob, closing_prob)
        updated = True

    if updated:
        PAPER_LOG.write_text(json.dumps(trades, indent=2))
        update_clv_log(trades)


def generate_paper_summary(trades: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate paper trading performance summary."""
    settled = [t for t in trades if t["status"] == "settled"]

    if not settled:
        return {
            "total_trades": 0,
            "bankroll": PAPER_BANKROLL,
            "current_bankroll": PAPER_BANKROLL,
            "roi": 0.0,
        }

    wins = [t for t in settled if t["result"] == "win"]
    losses = [t for t in settled if t["result"] == "loss"]
    pushes = [t for t in settled if t["result"] == "push"]

    total_pnl = sum(t["pnl"] for t in settled)
    total_staked = sum(t["stake"] for t in settled)

    win_rate = len(wins) / len(settled) if settled else 0.0
    roi = (total_pnl / total_staked * 100) if total_staked > 0 else 0.0

    current_bankroll = PAPER_BANKROLL + total_pnl

    clv_values = [t.get("clv") for t in settled if t.get("clv") is not None]
    avg_clv = sum(clv_values) / len(clv_values) if clv_values else None
    clv_positive_rate = (
        len([v for v in clv_values if v > 0]) / len(clv_values) if clv_values else None
    )
    steam_summary = Counter(t.get("steam_direction", "unknown") for t in settled)

    # Performance by sport
    by_sport: dict[str, dict] = {}
    for sport in ("nba", "soccer"):
        sport_trades = [t for t in settled if t["sport"] == sport]
        if not sport_trades:
            continue

        sport_wins = [t for t in sport_trades if t["result"] == "win"]
        sport_pnl = sum(t["pnl"] for t in sport_trades)
        sport_staked = sum(t["stake"] for t in sport_trades)

        by_sport[sport] = {
            "total_trades": len(sport_trades),
            "wins": len(sport_wins),
            "win_rate": len(sport_wins) / len(sport_trades) if sport_trades else 0.0,
            "pnl": round(sport_pnl, 2),
            "roi": round((sport_pnl / sport_staked * 100) if sport_staked > 0 else 0.0, 2),
        }

    summary = {
        "paper_mode": True,
        "timestamp": datetime.now(UTC).isoformat(),
        "initial_bankroll": PAPER_BANKROLL,
        "current_bankroll": round(current_bankroll, 2),
        "total_trades": len(settled),
        "wins": len(wins),
        "losses": len(losses),
        "pushes": len(pushes),
        "win_rate": round(win_rate * 100, 2),
        "total_pnl": round(total_pnl, 2),
        "total_staked": round(total_staked, 2),
        "roi": round(roi, 2),
        "by_sport": by_sport,
        "pending_trades": len([t for t in trades if t["status"] == "pending"]),
        "avg_clv": round(avg_clv, 4) if avg_clv is not None else None,
        "clv_positive_rate": round(clv_positive_rate, 4) if clv_positive_rate is not None else None,
        "steam_summary": dict(steam_summary),
    }

    PAPER_SUMMARY.write_text(json.dumps(summary, indent=2))
    return summary


def run_paper_trader() -> None:
    """Main paper trading loop."""
    if not PAPER_MODE:
        log("[paper] Paper mode disabled (set SPORTS_PAPER_MODE=true to enable)")
        return

    log(f"[paper] Starting paper trader (bankroll: ${PAPER_BANKROLL:,.2f})")

    while True:
        try:
            # Load Einstein queue
            einstein_data = load_predictions()
            opportunities = einstein_data.get("opportunities", [])

            if not opportunities:
                log("[paper] No opportunities in Einstein queue")
            else:
                log(f"[paper] Found {len(opportunities)} opportunities")

                # Filter by confidence
                high_conf = [o for o in opportunities if o.get("confidence", 0) >= MIN_CONFIDENCE]
                log(
                    f"[paper] {len(high_conf)} opportunities meet confidence threshold ({MIN_CONFIDENCE})"
                )

                # Simulate placing top bets
                trades = load_paper_trades()
                existing_ids = {t["game_id"] for t in trades}

                for opp in high_conf[:10]:  # Top 10 per cycle
                    if opp["game_id"] in existing_ids:
                        continue

                    paper_trade = simulate_bet_placement(opp)
                    save_paper_trade(paper_trade)
                    log(
                        f"[paper] Placed: {opp['sport']} {opp['recommended_side']} ${opp['recommended_stake']} @ {opp['decimal_odds']}"
                    )

            # Settle completed trades
            trades = load_paper_trades()
            settle_paper_trades(trades)
            clv_summary = update_clv_log(trades)

            # Generate summary
            summary = generate_paper_summary(trades)
            clv_text = (
                f" | Avg CLV: {summary['avg_clv']}" if summary.get("avg_clv") is not None else ""
            )
            log(
                "[paper] Summary: "
                f"{summary['total_trades']} trades | Win Rate: {summary['win_rate']}% | "
                f"ROI: {summary['roi']}% | Bankroll: ${summary['current_bankroll']:,.2f}{clv_text}"
            )

            maybe_send_clv_alerts(clv_summary)

            # Alert if profitable
            if summary["total_trades"] >= 10 and summary["roi"] > 5:
                try:
                    from analytics.telegram_notifier import send_alert

                    msg = f"""📊 **Paper Trading Update**

**Trades**: {summary["total_trades"]}
**Win Rate**: {summary["win_rate"]}%
**ROI**: {summary["roi"]}%
**P&L**: ${summary["total_pnl"]:,.2f}
**Bankroll**: ${summary["current_bankroll"]:,.2f}

System is profitable - ready for live trading!
"""
                    send_alert(msg)
                except Exception:
                    pass

            # Check every 30 minutes
            import time

            time.sleep(1800)

        except KeyboardInterrupt:
            log("[paper] Stopped by user")
            break
        except Exception as exc:
            log(f"[paper] Error: {exc}")
            import traceback

            traceback.print_exc()
            import time

            time.sleep(300)


if __name__ == "__main__":
    run_paper_trader()

#!/usr/bin/env python3
"""Sports analytics agent with seven-year history, ensemble modeling, and odds integration.

The agent assembles multi-season datasets, trains multiple models, and produces
bet-ready predictions stored under `state/`. Downstream, the sports betting
agent consumes the predictions to send manual BetMGM instructions.
"""

from __future__ import annotations

import json
import os
import warnings

# Force CPU execution for TensorFlow to avoid missing GPU kernels on macOS/LibreSSL builds.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import time
import traceback
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

# Python 3.9 compatibility: UTC is not available, use timezone.utc
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from pathlib import Path
from typing import Any

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:  # pragma: no cover - optional dependency warning at runtime
    HAS_NUMPY = False
    print("[sports_analytics] Install numpy: pip install numpy", flush=True)

try:
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, log_loss
    from sklearn.model_selection import train_test_split
    from sklearn.neural_network import MLPClassifier

    HAS_SKLEARN = True
except ImportError:  # pragma: no cover - optional dependency warning at runtime
    HAS_SKLEARN = False
    print("[sports_analytics] Install scikit-learn: pip install scikit-learn", flush=True)

try:
    import xgboost as xgb

    HAS_XGBOOST = True
except ImportError:  # pragma: no cover - optional dependency warning at runtime
    HAS_XGBOOST = False
    print("[sports_analytics] Install xgboost: pip install xgboost", flush=True)

try:
    import lightgbm as lgb
    from lightgbm.basic import LightGBMWarning

    HAS_LIGHTGBM = True
    warnings.filterwarnings("ignore", category=LightGBMWarning)
    warnings.filterwarnings("ignore", category=UserWarning, module="lightgbm")
except ImportError:  # pragma: no cover - optional dependency warning at runtime
    HAS_LIGHTGBM = False

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:  # pragma: no cover
    HAS_PANDAS = False
    print("[sports_analytics] Install pandas: pip install pandas", flush=True)

try:
    import tensorflow as tf

    HAS_TENSORFLOW = True
    # Force CPU execution; Apple Silicon GPU lacks required kernels for attention/GRU masks.
    try:
        tf.config.set_visible_devices([], "GPU")
    except Exception:
        pass
    try:
        tf.config.experimental.set_visible_devices([], "GPU")  # type: ignore[attr-defined]
    except Exception:
        pass
except ImportError:  # pragma: no cover - optional deep learning dependency
    HAS_TENSORFLOW = False

try:
    import optuna

    HAS_OPTUNA = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_OPTUNA = False

from analytics import sports_data_manager as data_mgr
from analytics.sports_advanced_features import (
    EloRatingSystem,
    InjuryTracker,
    calculate_home_advantage_score,
)
from analytics.sports_data_manager import (
    GameRecord,
    OddsRecord,
    backfill_odds_history,
    backfill_soccer_history,
    backfill_sportradar_history,
    generate_season_list,
    load_records,
)

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
DATA = ROOT / "data"
MODELS_DIR = DATA / "sports_models"
PREDICTIONS_LOG = ROOT / "logs" / "sports_predictions.log"
MULTITASK_DATA_PATH = MODELS_DIR / "multitask_dataset.npz"
MULTITASK_MODEL_PATH = MODELS_DIR / "multitask_model.keras"
OPTUNA_DIR = MODELS_DIR / "optuna"

for directory in (STATE, DATA, MODELS_DIR, PREDICTIONS_LOG.parent, OPTUNA_DIR):
    directory.mkdir(parents=True, exist_ok=True)


YEARS_OF_HISTORY = int(os.getenv("SPORTS_HISTORY_YEARS", "7"))
ROLLING_WINDOW = int(os.getenv("SPORTS_FEATURE_WINDOW", "10"))
CONFIDENCE_THRESHOLD = float(os.getenv("SPORTS_CONFIDENCE_THRESHOLD", "0.6"))

SPORTS = [
    sport.strip()
    for sport in os.getenv("SPORTS_ENABLED", "nfl,nba,mlb").split(",")
    if sport.strip()
]

# Advanced features toggles
USE_ELO = os.getenv("SPORTS_USE_ELO", "true").lower() == "true"
USE_INJURIES = os.getenv("SPORTS_USE_INJURIES", "true").lower() == "true"
USE_WEATHER = os.getenv("SPORTS_USE_WEATHER", "true").lower() == "true"
USE_REST_DAYS = os.getenv("SPORTS_USE_REST_DAYS", "true").lower() == "true"

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

EDGE_THRESHOLD = float(os.getenv("SPORTS_EDGE_THRESHOLD", "0.02"))
MAX_RISK_PER_BET = float(os.getenv("SPORTS_MAX_RISK", "100"))

SHARP_MOVEMENT_THRESHOLD = float(os.getenv("SPORTS_SHARP_MOVEMENT_THRESHOLD", "0.03"))
MIN_REGIME_SAMPLES = int(os.getenv("SPORTS_MIN_REGIME_SAMPLES", "120"))
SEQUENCE_WINDOW = int(os.getenv("SPORTS_SEQUENCE_WINDOW", "5"))
SEQUENCE_EPOCHS = int(os.getenv("SPORTS_SEQUENCE_EPOCHS", "3"))
OPTUNA_TRIALS = int(os.getenv("SPORTS_OPTUNA_TRIALS", "20"))
OPTUNA_TIMEOUT = int(os.getenv("SPORTS_OPTUNA_TIMEOUT", "180"))
OPTUNA_MIN_SAMPLES = int(os.getenv("SPORTS_OPTUNA_MIN_SAMPLES", "150"))
OPTUNA_SEED = int(os.getenv("SPORTS_OPTUNA_SEED", "42"))
# Default to False if TensorFlow not available or unreliable
USE_TRANSFORMER_SEQUENCE = (
    HAS_TENSORFLOW and os.getenv("SPORTS_USE_TRANSFORMER", "false").lower() == "true"
)
TRANSFORMER_HEADS = int(os.getenv("SPORTS_TRANSFORMER_HEADS", "4"))
TRANSFORMER_DFF = int(os.getenv("SPORTS_TRANSFORMER_DFF", "64"))
TRANSFORMER_DROPOUT = float(os.getenv("SPORTS_TRANSFORMER_DROPOUT", "0.2"))
TRANSFORMER_EPOCHS = int(os.getenv("SPORTS_TRANSFORMER_EPOCHS", str(max(3, SEQUENCE_EPOCHS + 1))))
TRANSFORMER_BATCH_FRACTION = float(os.getenv("SPORTS_TRANSFORMER_BATCH_FRAC", "0.25"))

if USE_TRANSFORMER_SEQUENCE and not HAS_TENSORFLOW:
    warnings.warn(
        "[sports_analytics] Transformer sequence modeling requested but TensorFlow is unavailable; "
        "set SPORTS_USE_TRANSFORMER=false or install tensorflow.",
        RuntimeWarning,
    )

if OPTUNA_TRIALS > 0 and not HAS_OPTUNA:
    warnings.warn(
        "[sports_analytics] Optuna tuning requested but Optuna is unavailable; "
        "set SPORTS_OPTUNA_TRIALS=0 or install optuna.",
        RuntimeWarning,
    )


def load_local_nba_injuries() -> dict[str, float]:
    injuries_file = DATA / "sports_injuries" / "nba_injuries.json"
    if not injuries_file.exists():
        return {}
    try:
        payload = json.loads(injuries_file.read_text())
    except json.JSONDecodeError:
        return {}
    impacts: dict[str, float] = {}
    for entry in payload.get("teams", []):
        team = str(entry.get("team", "")).strip().lower()
        impact = float(entry.get("impact", 0.0))
        if team:
            impacts[team] = impact
    return impacts


SOCCER_LEAGUES = [
    league.strip()
    for league in os.getenv("SOCCER_LEAGUE_IDS", "39,140,135,78,61,2,253").split(",")
    if league.strip()
]


@dataclass
class ModelMetadata:
    name: str
    accuracy: float
    log_loss: float | None


def compute_bayesian_stats(
    weights: Iterable[float],
    probs: Iterable[float],
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> tuple[float, float, float, float]:
    weights_np = np.asarray(list(weights), dtype=float)
    probs_np = np.asarray(list(probs), dtype=float)
    if weights_np.size == 0 or probs_np.size == 0:
        return prior_alpha, prior_beta, 0.5, 0.25
    weighted_probs = weights_np * probs_np
    alpha = prior_alpha + float(np.sum(weighted_probs))
    beta = prior_beta + float(np.sum(weights_np * (1.0 - probs_np)))
    denom = alpha + beta
    if denom <= 0:
        return prior_alpha, prior_beta, 0.5, 0.25
    mean = alpha / denom
    variance = (
        (alpha * beta) / ((denom**2) * (denom + 1.0))
        if denom > 1.0
        else mean * (1.0 - mean) / max(denom + 1.0, 2.0)
    )
    return alpha, beta, mean, variance


def calculate_clv(open_prob: float | None, closing_prob: float | None) -> float | None:
    if open_prob in (None, 0) or closing_prob is None:
        return None
    return (closing_prob - open_prob) / open_prob


def detect_regime(game: GameRecord) -> str:
    sport = (game.sport or "").lower()
    scheduled_dt = parse_datetime(game.scheduled)
    if sport == "nba" and scheduled_dt:
        if scheduled_dt.month in {4, 5, 6}:
            return "playoffs"
        if scheduled_dt.month in {10, 11, 12}:
            return "early_season"
        return "regular"
    if sport == "soccer" and scheduled_dt:
        if scheduled_dt.month in {4, 5}:
            return "title_run_in"
        if scheduled_dt.month in {8, 9}:
            return "season_start"
    return "default"


def detect_sharp_movement(odds_history: list[OddsRecord]) -> str:
    if len(odds_history) < 2:
        return "neutral"
    sorted_history = sorted(
        odds_history,
        key=lambda record: parse_datetime(record.collected_at) or datetime.min.replace(tzinfo=UTC),
    )
    opening = sorted_history[0]
    latest = sorted_history[-1]
    open_prob = american_to_prob(opening.home_price)
    latest_prob = american_to_prob(latest.home_price)
    if open_prob is None or latest_prob is None:
        return "neutral"
    movement = latest_prob - open_prob
    if movement <= -SHARP_MOVEMENT_THRESHOLD:
        return "sharp_away"
    if movement >= SHARP_MOVEMENT_THRESHOLD:
        return "sharp_home"
    return "neutral"


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


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_game_history(sport: str, seasons: Iterable[str]) -> list[GameRecord]:
    games: list[GameRecord] = []
    for season in seasons:
        if sport == "soccer":
            base_dir = data_mgr.HISTORY_DIR / sport
            if not base_dir.exists():
                continue
            for path in base_dir.glob(f"{season}_*.json"):
                for payload in load_records(path):
                    try:
                        games.append(GameRecord(**payload))
                    except TypeError:
                        continue
        else:
            path = data_mgr.HISTORY_DIR / sport / f"{season}.json"
            for payload in load_records(path):
                try:
                    games.append(GameRecord(**payload))
                except TypeError:
                    continue
    return games


def load_odds_history(sport: str, seasons: Iterable[str]) -> list[OddsRecord]:
    if sport == "soccer":
        return data_mgr.load_local_soccer_odds()
    if sport == "nba":
        return data_mgr.load_local_nba_odds()

    odds: list[OddsRecord] = []
    for season in seasons:
        pattern = data_mgr.ODDS_DIR / sport
        if not pattern.exists():
            continue
        for file in pattern.glob(f"{season}_*.json"):
            for payload in load_records(file):
                try:
                    odds.append(OddsRecord(**payload))
                except TypeError:
                    continue
    return odds


class FeatureBuilder:
    def __init__(self, sport: str, games: list[GameRecord], odds: list[OddsRecord]):
        self.sport = sport
        self.games = sorted(games, key=lambda g: g.scheduled)
        self.odds_lookup = self._build_odds_lookup(odds)
        self.team_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.team_feature_history: dict[str, list[list[float]]] = defaultdict(list)
        self.team_feature_history: dict[str, list[list[float]]] = defaultdict(list)

        # Advanced features
        self.elo_system = EloRatingSystem.load(sport) if USE_ELO else None
        self.injury_tracker = InjuryTracker(RAPIDAPI_KEY) if USE_INJURIES and RAPIDAPI_KEY else None
        self.nba_injuries_cache: list[dict[str, Any]] = []
        self.local_injury_index: dict[str, float] = {}
        if self.injury_tracker and sport == "nba":
            try:
                self.nba_injuries_cache = self.injury_tracker.fetch_nba_injuries()
                print(f"[features] Loaded {len(self.nba_injuries_cache)} NBA injuries", flush=True)
            except Exception as e:
                print(f"[features] Could not fetch injuries: {e}", flush=True)
        if sport == "nba" and not self.nba_injuries_cache:
            self.local_injury_index = load_local_nba_injuries()
            if self.local_injury_index:
                print(
                    f"[features] Loaded {len(self.local_injury_index)} NBA injury impacts from local cache",
                    flush=True,
                )

    @staticmethod
    def _build_odds_lookup(odds: list[OddsRecord]) -> dict[str, dict[str, list[OddsRecord]]]:
        lookup: dict[str, dict[str, list[OddsRecord]]] = defaultdict(lambda: defaultdict(list))
        for record in odds:
            lookup[record.game_id][record.market].append(record)
        return lookup

    def _odds_insights(self, game_id: str) -> dict[str, Any]:
        market_map = self.odds_lookup.get(game_id, {})
        series = market_map.get("h2h") or market_map.get("moneyline") or []
        if not series:
            return {
                "latest_home_prob": None,
                "latest_away_prob": None,
                "open_home_prob": None,
                "open_away_prob": None,
                "line_movement": 0.0,
                "sharp_signal": "neutral",
                "history": [],
            }
        sorted_history = sorted(
            series,
            key=lambda record: parse_datetime(record.collected_at)
            or datetime.min.replace(tzinfo=UTC),
        )
        opening = sorted_history[0]
        latest = sorted_history[-1]
        open_home_prob = american_to_prob(opening.home_price)
        open_away_prob = american_to_prob(opening.away_price)
        latest_home_prob = american_to_prob(latest.home_price)
        latest_away_prob = american_to_prob(latest.away_price)
        if open_home_prob is None or latest_home_prob is None:
            line_movement = 0.0
        else:
            line_movement = latest_home_prob - open_home_prob
        return {
            "latest_home_prob": latest_home_prob,
            "latest_away_prob": latest_away_prob,
            "open_home_prob": open_home_prob,
            "open_away_prob": open_away_prob,
            "line_movement": line_movement,
            "sharp_signal": detect_sharp_movement(sorted_history),
            "history": sorted_history,
        }

    def _recent_stats(self, team: str) -> dict[str, float]:
        history = self.team_history.get(team) or []
        if not history:
            return {
                "win_pct": 0.5,
                "avg_points": 24.0,
                "avg_allowed": 24.0,
                "rest_days": 6.0,
            }
        recent = history[-ROLLING_WINDOW:]
        wins = sum(1 for game in recent if game.get("won"))
        avg_points = sum(game.get("points", 0.0) for game in recent) / len(recent)
        avg_allowed = sum(game.get("allowed", 0.0) for game in recent) / len(recent)
        last_game = recent[-1]
        rest_days = last_game.get("rest_days", 6.0)
        return {
            "win_pct": wins / len(recent),
            "avg_points": avg_points,
            "avg_allowed": avg_allowed,
            "rest_days": rest_days,
        }

    def _pad_sequence(self, sequence: list[list[float]], feature_dim: int) -> list[list[float]]:
        if len(sequence) >= SEQUENCE_WINDOW:
            return sequence[-SEQUENCE_WINDOW:]
        pad_length = SEQUENCE_WINDOW - len(sequence)
        padding = [[0.0] * feature_dim for _ in range(pad_length)]
        return padding + sequence

    def _build_sequence_vector(
        self,
        home_team: str,
        away_team: str,
        feature_dim: int,
    ) -> list[list[float]]:
        home_history = self.team_feature_history.get(home_team, [])
        away_history = self.team_feature_history.get(away_team, [])
        padded_home = self._pad_sequence([row[:] for row in home_history], feature_dim)
        padded_away = self._pad_sequence([row[:] for row in away_history], feature_dim)
        combined: list[list[float]] = []
        for home_row, away_row in zip(padded_home, padded_away):
            combined.append(home_row + away_row)
        return combined

    def _pad_sequence(self, sequence: list[list[float]], feature_dim: int) -> list[list[float]]:
        if len(sequence) >= SEQUENCE_WINDOW:
            return sequence[-SEQUENCE_WINDOW:]
        pad_length = SEQUENCE_WINDOW - len(sequence)
        padding = [[0.0] * feature_dim for _ in range(pad_length)]
        return padding + sequence

    def _build_sequence_vector(
        self,
        home_team: str,
        away_team: str,
        feature_dim: int,
    ) -> list[list[float]]:
        home_history = self.team_feature_history.get(home_team, [])
        away_history = self.team_feature_history.get(away_team, [])
        padded_home = self._pad_sequence([row[:] for row in home_history], feature_dim)
        padded_away = self._pad_sequence([row[:] for row in away_history], feature_dim)
        combined: list[list[float]] = []
        for h_row, a_row in zip(padded_home, padded_away):
            combined.append(h_row + a_row)
        return combined

    def _odds_features(self, game_id: str) -> dict[str, Any]:
        return self._odds_insights(game_id)

    def build_datasets(
        self,
    ) -> tuple[
        list[list[float]],
        list[int],
        list[dict[str, Any]],
        list[GameRecord],
        list[list[list[float]]],
    ]:
        X: list[list[float]] = []
        y: list[int] = []
        metadata: list[dict[str, Any]] = []
        seen_games: list[GameRecord] = []
        sequence_vectors: list[list[list[float]]] = []

        for game in self.games:
            scheduled_dt = parse_datetime(game.scheduled) or datetime.now(UTC)

            home_stats = self._recent_stats(game.home_team)
            away_stats = self._recent_stats(game.away_team)
            odds_meta = self._odds_features(game.game_id)
            home_prob = odds_meta.get("latest_home_prob") or 0.5
            away_prob = odds_meta.get("latest_away_prob") or 0.5
            home_prob_open = odds_meta.get("open_home_prob") or home_prob
            away_prob_open = odds_meta.get("open_away_prob") or away_prob
            line_movement = odds_meta.get("line_movement", 0.0) or 0.0
            sharp_signal = odds_meta.get("sharp_signal", "neutral")
            regime = detect_regime(game)

            last_home_game = (
                self.team_history[game.home_team][-1]["date"]
                if self.team_history[game.home_team]
                else None
            )
            last_away_game = (
                self.team_history[game.away_team][-1]["date"]
                if self.team_history[game.away_team]
                else None
            )
            rest_days_home = (
                (scheduled_dt - last_home_game).days
                if last_home_game
                else home_stats.get("rest_days", 6.0)
            )
            rest_days_away = (
                (scheduled_dt - last_away_game).days
                if last_away_game
                else away_stats.get("rest_days", 6.0)
            )

            # Base features
            features = [
                home_stats["win_pct"],
                away_stats["win_pct"],
                home_stats["avg_points"],
                away_stats["avg_points"],
                home_stats["avg_allowed"],
                away_stats["avg_allowed"],
                rest_days_home,
                rest_days_away,
                home_prob,
                away_prob,
                home_prob_open,
                away_prob_open,
                line_movement,
            ]

            # Advanced features: Elo ratings
            home_elo = 1500.0
            away_elo = 1500.0
            elo_diff = 0.0
            if USE_ELO and self.elo_system:
                home_elo = self.elo_system.get_rating(game.home_team)
                away_elo = self.elo_system.get_rating(game.away_team)
                elo_diff = home_elo - away_elo
                features.extend([home_elo / 1000.0, away_elo / 1000.0, elo_diff / 100.0])
            else:
                features.extend([1.5, 1.5, 0.0])  # Neutral values

            # Injury impact (NBA only for now)
            home_injury = 0.0
            away_injury = 0.0
            if USE_INJURIES and self.sport == "nba":
                if self.injury_tracker and self.nba_injuries_cache:
                    home_injury = self.injury_tracker.get_team_injury_impact(
                        game.home_team, self.nba_injuries_cache
                    )
                    away_injury = self.injury_tracker.get_team_injury_impact(
                        game.away_team, self.nba_injuries_cache
                    )
                else:
                    home_injury = self.local_injury_index.get(game.home_team.lower(), 0.0)
                    away_injury = self.local_injury_index.get(game.away_team.lower(), 0.0)
                features.extend([home_injury, away_injury])
            else:
                features.extend([0.0, 0.0])

            # Home advantage score
            home_advantage = calculate_home_advantage_score(
                game.home_team, game.home_team
            )  # venue = team for simplicity
            features.append(home_advantage)

            # Feature interactions (2nd / 3rd order)
            features.extend(
                [
                    (home_elo / 1000.0) * rest_days_home,
                    (away_elo / 1000.0) * rest_days_away,
                    home_injury * home_stats["win_pct"],
                    away_injury * away_stats["win_pct"],
                    (elo_diff / 100.0) * home_advantage,
                    home_stats["avg_points"] * (1 - home_injury),
                    away_stats["avg_points"] * (1 - away_injury),
                    (home_elo / 1000.0) * rest_days_home * home_advantage,
                ]
            )

            feature_vector = features
            feature_dim = len(feature_vector)
            sequence_vector = self._build_sequence_vector(
                game.home_team,
                game.away_team,
                feature_dim,
            )

            home_score = game.home_score
            away_score = game.away_score
            game_finished = (
                home_score is not None
                and away_score is not None
                and game.status.lower() in {"closed", "complete", "final", "match finished"}
            )

            seen_games.append(game)

            if not game_finished:
                continue

            # Update rolling stats before using this game for future samples so that
            # sequence vectors are based on prior games only.
            self.team_history[game.home_team].append(
                {
                    "date": scheduled_dt,
                    "won": home_score > away_score,
                    "points": float(home_score),
                    "allowed": float(away_score),
                    "rest_days": rest_days_home,
                }
            )
            self.team_history[game.away_team].append(
                {
                    "date": scheduled_dt,
                    "won": away_score > home_score,
                    "points": float(away_score),
                    "allowed": float(home_score),
                    "rest_days": rest_days_away,
                }
            )

            # Update Elo ratings after each completed game
            if USE_ELO and self.elo_system:
                self.elo_system.update_ratings(
                    game.home_team,
                    game.away_team,
                    home_score,
                    away_score,
                    is_home_a=True,
                    date=game.scheduled,
                )

            self.team_feature_history[game.home_team].append(feature_vector[:])
            self.team_feature_history[game.away_team].append(feature_vector[:])

            if home_score == away_score:
                continue

            X.append(feature_vector)
            y.append(1 if home_score > away_score else 0)
            sequence_vectors.append(sequence_vector)
            metadata.append(
                {
                    "game_id": game.game_id,
                    "scheduled": game.scheduled,
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "home_prob_implied": home_prob,
                    "away_prob_implied": away_prob,
                    "home_prob_open": home_prob_open,
                    "away_prob_open": away_prob_open,
                    "line_movement": line_movement,
                    "regime": regime,
                    "sharp_signal": sharp_signal,
                    "clv": calculate_clv(home_prob_open, home_prob),
                    "home_score": home_score,
                    "away_score": away_score,
                }
            )

        return X, y, metadata, seen_games, sequence_vectors

    def build_future_features(
        self, cutoff: datetime, realtime_schedules: dict[str, list[dict[str, Any]]] | None = None
    ) -> list[tuple[GameRecord, list[float], dict[str, Any]]]:
        """
        Build features for future games.

        Args:
            cutoff: Only include games after this datetime
            realtime_schedules: Real-time schedule data (if provided, uses these instead of historical)
        """
        future_games: list[tuple[GameRecord, list[float], dict[str, Any]]] = []

        # If real-time schedules provided, convert them to GameRecords first
        if realtime_schedules and realtime_schedules.get(self.sport):
            realtime_games = []
            for game_data in realtime_schedules[self.sport]:
                try:
                    game = GameRecord(
                        game_id=game_data.get("game_id", f"{self.sport}_{game_data.get('id', '')}"),
                        home_team=game_data.get("home_team", ""),
                        away_team=game_data.get("away_team", ""),
                        scheduled=game_data.get("scheduled", datetime.now(UTC).isoformat()),
                        sport=self.sport,
                    )
                    realtime_games.append(game)
                except Exception as e:
                    print(f"[sports_analytics] Error converting real-time game: {e}", flush=True)
                    continue

            # Use real-time games instead of historical future games
            games_to_process = realtime_games
        else:
            # Fall back to historical future games
            games_to_process = [
                g for g in self.games if (parse_datetime(g.scheduled) or datetime.now(UTC)) > cutoff
            ]

        for game in games_to_process:
            scheduled_dt = parse_datetime(game.scheduled) or datetime.now(UTC)
            if scheduled_dt <= cutoff:
                continue

            home_stats = self._recent_stats(game.home_team)
            away_stats = self._recent_stats(game.away_team)
            odds_meta = self._odds_features(game.game_id)
            home_prob = odds_meta.get("latest_home_prob") or 0.5
            away_prob = odds_meta.get("latest_away_prob") or 0.5
            home_prob_open = odds_meta.get("open_home_prob") or home_prob
            away_prob_open = odds_meta.get("open_away_prob") or away_prob
            line_movement = odds_meta.get("line_movement", 0.0) or 0.0
            sharp_signal = odds_meta.get("sharp_signal", "neutral")
            regime = detect_regime(game)
            last_home_game = (
                self.team_history[game.home_team][-1]["date"]
                if self.team_history[game.home_team]
                else None
            )
            last_away_game = (
                self.team_history[game.away_team][-1]["date"]
                if self.team_history[game.away_team]
                else None
            )
            rest_days_home = (
                (scheduled_dt - last_home_game).days
                if last_home_game
                else home_stats.get("rest_days", 6.0)
            )
            rest_days_away = (
                (scheduled_dt - last_away_game).days
                if last_away_game
                else away_stats.get("rest_days", 6.0)
            )

            # Base features
            features = [
                home_stats["win_pct"],
                away_stats["win_pct"],
                home_stats["avg_points"],
                away_stats["avg_points"],
                home_stats["avg_allowed"],
                away_stats["avg_allowed"],
                rest_days_home,
                rest_days_away,
                home_prob or 0.5,
                away_prob or 0.5,
                home_prob_open,
                away_prob_open,
                line_movement,
            ]

            # Advanced features: Elo ratings
            home_elo = 1500.0
            away_elo = 1500.0
            elo_diff = 0.0
            if USE_ELO and self.elo_system:
                home_elo = self.elo_system.get_rating(game.home_team)
                away_elo = self.elo_system.get_rating(game.away_team)
                elo_diff = home_elo - away_elo
                features.extend([home_elo / 1000.0, away_elo / 1000.0, elo_diff / 100.0])
            else:
                features.extend([1.5, 1.5, 0.0])

            # Injury impact (NBA only for now)
            home_injury = 0.0
            away_injury = 0.0
            if USE_INJURIES and self.sport == "nba":
                if self.injury_tracker and self.nba_injuries_cache:
                    home_injury = self.injury_tracker.get_team_injury_impact(
                        game.home_team, self.nba_injuries_cache
                    )
                    away_injury = self.injury_tracker.get_team_injury_impact(
                        game.away_team, self.nba_injuries_cache
                    )
                else:
                    home_injury = self.local_injury_index.get(game.home_team.lower(), 0.0)
                    away_injury = self.local_injury_index.get(game.away_team.lower(), 0.0)
                features.extend([home_injury, away_injury])
            else:
                features.extend([0.0, 0.0])

            # Home advantage score
            home_advantage = calculate_home_advantage_score(game.home_team, game.home_team)
            features.append(home_advantage)

            # Feature interactions
            features.extend(
                [
                    (home_elo / 1000.0) * rest_days_home,
                    (away_elo / 1000.0) * rest_days_away,
                    home_injury * home_stats["win_pct"],
                    away_injury * away_stats["win_pct"],
                    (elo_diff / 100.0) * home_advantage,
                    home_stats["avg_points"] * (1 - home_injury),
                    away_stats["avg_points"] * (1 - away_injury),
                    (home_elo / 1000.0) * rest_days_home * home_advantage,
                ]
            )

            feature_vector = features

            feature_dim = len(feature_vector)
            sequence_vector = self._build_sequence_vector(
                game.home_team,
                game.away_team,
                feature_dim,
            )

            meta = {
                "home_prob_implied": home_prob,
                "away_prob_implied": away_prob,
                "scheduled": game.scheduled,
                "home_prob_open": home_prob_open,
                "away_prob_open": away_prob_open,
                "line_movement": line_movement,
                "sharp_signal": sharp_signal,
                "regime": regime,
                "clv_estimate": calculate_clv(home_prob_open, home_prob),
                "sequence_vector": sequence_vector,
            }
            future_games.append((game, feature_vector, meta))
        return future_games


def train_ensemble(
    X: list[list[float]],
    y: list[int],
    sample_metadata: list[dict[str, Any]],
    sequence_sequences: list[list[list[float]]] | None = None,
    sport: str | None = None,
) -> tuple[dict[str, Any], list[ModelMetadata], dict[str, Any]]:
    if not (HAS_SKLEARN and HAS_NUMPY) or len(X) < 20:
        return {"type": "mock"}, [], {}

    X_np = np.asarray(X, dtype=float)
    y_np = np.asarray(y, dtype=int)

    indices = np.arange(len(X_np))
    stratify = y_np if len(set(y_np)) > 1 else None
    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X_np,
        y_np,
        indices,
        test_size=0.2,
        random_state=42,
        stratify=stratify,
    )

    sequence_array: np.ndarray | None
    if sequence_sequences and len(sequence_sequences) == len(X):
        try:
            sequence_array = np.asarray(sequence_sequences, dtype=float)
        except Exception:
            sequence_array = None
    else:
        sequence_array = None

    regime_labels: list[str] = ["default"] * len(X_np)
    if sample_metadata:
        limit = min(len(sample_metadata), len(regime_labels))
        for i in range(limit):
            label = sample_metadata[i].get("regime") or sample_metadata[i].get("regime_label")
            if label:
                regime_labels[i] = str(label).strip().lower() or "default"

    fitted_models: dict[str, Any] = {}
    metadata_records: list[ModelMetadata] = []
    model_prob_store: dict[str, np.ndarray] = {}
    train_prob_store: dict[str, np.ndarray] = {}
    weight_map: dict[str, float] = {}

    models = {
        "random_forest": RandomForestClassifier(n_estimators=400, max_depth=10, random_state=42),
        "gradient_boosting": GradientBoostingClassifier(random_state=42),
        "logistic_regression": LogisticRegression(max_iter=2000, solver="lbfgs"),
        "mlp": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=1500, random_state=42),
    }
    if HAS_XGBOOST:
        models["xgboost"] = xgb.XGBClassifier(
            eval_metric="logloss",
            n_estimators=500,
            max_depth=8,
            subsample=0.8,
            colsample_bytree=0.8,
            learning_rate=0.05,
            min_child_weight=2,
            random_state=42,
        )
    if HAS_LIGHTGBM:
        models["lightgbm"] = lgb.LGBMClassifier(
            n_estimators=600,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
        )

    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        probs = None
        try:
            probs = model.predict_proba(X_test)
        except Exception:
            probs = None
        accuracy = accuracy_score(y_test, preds)
        ll = log_loss(y_test, probs) if probs is not None else None
        fitted_models[name] = model
        metadata_records.append(
            ModelMetadata(name=name, accuracy=float(accuracy), log_loss=float(ll) if ll else None)
        )
        if probs is not None:
            model_prob_store[name] = probs[:, 1]
            try:
                train_probs = model.predict_proba(X_train)
                train_prob_store[name] = train_probs[:, 1]
            except Exception:
                pass
            try:
                train_probs = model.predict_proba(X_train)
                train_prob_store[name] = train_probs[:, 1]
            except Exception:
                pass

    if HAS_OPTUNA and HAS_LIGHTGBM and OPTUNA_TRIALS > 0 and len(regime_labels) == len(X_np):
        regime_array = np.asarray(regime_labels)
        unique_regimes = sorted(set(regime_array))

        def _slug(text: str) -> str:
            return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in text)

        for regime_label in unique_regimes:
            if not regime_label:
                continue
            regime_indices = np.where(regime_array == regime_label)[0]
            if regime_indices.size < OPTUNA_MIN_SAMPLES:
                continue
            regime_targets = y_np[regime_indices]
            if len(np.unique(regime_targets)) < 2:
                continue

            train_reg_mask = np.isin(idx_train, regime_indices)
            test_reg_mask = np.isin(idx_test, regime_indices)
            if train_reg_mask.sum() < max(OPTUNA_MIN_SAMPLES // 2, 60):
                continue
            if test_reg_mask.sum() < 20:
                continue

            X_train_reg = X_train[train_reg_mask]
            y_train_reg = y_train[train_reg_mask]
            if len(np.unique(y_train_reg)) < 2:
                continue

            regime_seed = (hash(regime_label) + OPTUNA_SEED) % (2**32)

            def objective(trial: optuna.Trial) -> float:
                params = {
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                    "n_estimators": trial.suggest_int("n_estimators", 200, 800, step=100),
                    "max_depth": trial.suggest_int("max_depth", 4, 12),
                    "num_leaves": trial.suggest_int("num_leaves", 16, 128),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                    "min_child_samples": trial.suggest_int("min_child_samples", 10, 120),
                    "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
                    "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
                }
                model = lgb.LGBMClassifier(
                    objective="binary",
                    random_state=regime_seed,
                    n_jobs=-1,
                    **params,
                )
                split = train_test_split(
                    X_train_reg,
                    y_train_reg,
                    test_size=0.2,
                    random_state=int(regime_seed + trial.number),
                    stratify=y_train_reg if len(np.unique(y_train_reg)) > 1 else None,
                )
                X_sub_train, X_sub_valid, y_sub_train, y_sub_valid = split
                if len(np.unique(y_sub_valid)) < 2:
                    raise optuna.exceptions.TrialPruned("Validation fold lacks class diversity")
                try:
                    model.fit(
                        X_sub_train,
                        y_sub_train,
                        eval_set=[(X_sub_valid, y_sub_valid)],
                        eval_metric="logloss",
                        callbacks=[lgb.early_stopping(25, verbose=False)],
                    )
                except Exception as exc:  # pragma: no cover - LightGBM training failure
                    raise optuna.exceptions.TrialPruned(str(exc))
                probs = model.predict_proba(X_sub_valid)[:, 1]
                ll = log_loss(
                    y_sub_valid,
                    np.column_stack([1.0 - probs, probs]),
                )
                return float(ll)

            sampler = optuna.samplers.TPESampler(seed=regime_seed)
            study = optuna.create_study(direction="minimize", sampler=sampler)
            try:
                study.optimize(
                    objective,
                    n_trials=OPTUNA_TRIALS,
                    timeout=OPTUNA_TIMEOUT if OPTUNA_TIMEOUT > 0 else None,
                    show_progress_bar=False,
                )
            except Exception as exc:  # pragma: no cover - safeguard against Optuna failures
                print(f"[optuna] regime={regime_label} failed: {exc}", flush=True)
                continue

            if not study.trials:
                continue

            best_params = dict(study.best_params)
            best_model = lgb.LGBMClassifier(
                objective="binary",
                random_state=regime_seed,
                n_jobs=-1,
                **best_params,
            )
            best_model.fit(X_train_reg, y_train_reg)

            train_probs_full = np.full(len(X_train), 0.5, dtype=float)
            test_probs_full = np.full(len(X_test), 0.5, dtype=float)

            train_probs = best_model.predict_proba(X_train_reg)[:, 1]
            train_probs_full[train_reg_mask] = train_probs

            test_indices_reg = np.where(test_reg_mask)[0]
            test_accuracy = None
            test_logloss = None
            if test_indices_reg.size > 0:
                test_probs = best_model.predict_proba(X_test[test_reg_mask])[:, 1]
                test_probs_full[test_reg_mask] = test_probs
                test_preds = (test_probs >= 0.5).astype(int)
                test_accuracy = accuracy_score(y_test[test_reg_mask], test_preds)
                test_logloss = log_loss(
                    y_test[test_reg_mask],
                    np.column_stack([1.0 - test_probs, test_probs]),
                )

            model_name = f"lightgbm_optuna_{regime_label}"
            fitted_models[model_name] = {
                "type": "optuna_lightgbm",
                "model": best_model,
                "regime": regime_label,
                "best_params": best_params,
                "best_value": float(study.best_value),
                "trials": len(study.trials),
            }

            metadata_records.append(
                ModelMetadata(
                    name=model_name,
                    accuracy=float(test_accuracy) if test_accuracy is not None else 0.0,
                    log_loss=float(test_logloss) if test_logloss is not None else None,
                )
            )

            model_prob_store[model_name] = test_probs_full
            train_prob_store[model_name] = train_probs_full
            if test_accuracy is not None:
                weight_map[model_name] = float(np.clip(test_accuracy, 0.6, 0.995))
            else:
                weight_map[model_name] = 0.6

            manifest = {
                "timestamp": datetime.now(UTC).isoformat(),
                "sport": sport,
                "regime": regime_label,
                "best_params": best_params,
                "best_value": float(study.best_value),
                "trials": len(study.trials),
            }
            manifest_path = (
                OPTUNA_DIR / f"lightgbm_{_slug((sport or 'na') + '_' + regime_label)}.json"
            )
            try:
                manifest_path.write_text(json.dumps(manifest, indent=2))
            except Exception:
                pass
            print(
                f"[optuna] regime={regime_label} best_logloss={study.best_value:.4f} trials={len(study.trials)}",
                flush=True,
            )

    # Sequence model (GRU) for temporal context
    if (
        HAS_TENSORFLOW
        and sequence_array is not None
        and sequence_array.ndim == 3
        and sequence_array.shape[0] == len(X)
        and sequence_array.shape[2] > 0
        and np.any(sequence_array)
    ):
        seq_train = sequence_array[idx_train]
        seq_test = sequence_array[idx_test]
        try:
            seq_model = tf.keras.Sequential(
                [
                    tf.keras.layers.Input(shape=(seq_train.shape[1], seq_train.shape[2])),
                    tf.keras.layers.Masking(mask_value=0.0),
                    tf.keras.layers.Bidirectional(
                        tf.keras.layers.GRU(
                            32,
                            return_sequences=False,
                            reset_after=False,  # ensure pure TensorFlow kernel (no cuDNN dependency)
                        )
                    ),
                    tf.keras.layers.Dropout(0.2),
                    tf.keras.layers.Dense(16, activation="relu"),
                    tf.keras.layers.Dense(1, activation="sigmoid"),
                ]
            )
            seq_model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
            seq_model.fit(
                seq_train,
                y_train,
                epochs=SEQUENCE_EPOCHS,
                batch_size=min(64, max(16, seq_train.shape[0] // 8)),
                verbose=0,
            )
            seq_probs_train = seq_model.predict(seq_train, verbose=0).reshape(-1)
            seq_probs_test = seq_model.predict(seq_test, verbose=0).reshape(-1)
            seq_accuracy = accuracy_score(y_test, (seq_probs_test >= 0.5).astype(int))
            seq_ll = log_loss(
                y_test,
                np.column_stack([1.0 - seq_probs_test, seq_probs_test]),
            )
            metadata_records.append(
                ModelMetadata(
                    name="sequence_gru", accuracy=float(seq_accuracy), log_loss=float(seq_ll)
                )
            )
            fitted_models["sequence_gru"] = {
                "type": "sequence",
                "model": seq_model,
                "feature_dim": seq_train.shape[2],
                "sequence_window": seq_train.shape[1],
            }
            model_prob_store["sequence_gru"] = seq_probs_test
            train_prob_store["sequence_gru"] = seq_probs_train
            weight_map["sequence_gru"] = float(np.clip(seq_accuracy, 0.6, 0.995))
        except Exception as exc:  # pragma: no cover - TensorFlow optional failures
            print(f"[sequence] Skipping sequence model: {exc}", flush=True)

    if (
        USE_TRANSFORMER_SEQUENCE
        and HAS_TENSORFLOW
        and sequence_array is not None
        and sequence_array.ndim == 3
        and sequence_array.shape[0] == len(X)
        and sequence_array.shape[2] > 0
        and np.any(sequence_array)
    ):
        seq_train = sequence_array[idx_train]
        seq_test = sequence_array[idx_test]

        def _build_transformer(input_shape: tuple[int, int]) -> tf.keras.Model:
            inputs = tf.keras.layers.Input(shape=input_shape)
            x = tf.keras.layers.Masking(mask_value=0.0)(inputs)
            attn = tf.keras.layers.MultiHeadAttention(
                num_heads=max(1, TRANSFORMER_HEADS),
                key_dim=min(input_shape[-1], TRANSFORMER_DFF),
            )(x, x)
            x = tf.keras.layers.Add()([attn, x])
            x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)
            ff = tf.keras.layers.Dense(TRANSFORMER_DFF, activation="relu")(x)
            ff = tf.keras.layers.Dropout(TRANSFORMER_DROPOUT)(ff)
            ff = tf.keras.layers.Dense(input_shape[-1])(ff)
            x = tf.keras.layers.Add()([ff, x])
            x = tf.keras.layers.LayerNormalization(epsilon=1e-6)(x)
            x = tf.keras.layers.GlobalAveragePooling1D()(x)
            x = tf.keras.layers.Dropout(TRANSFORMER_DROPOUT)(x)
            x = tf.keras.layers.Dense(32, activation="relu")(x)
            outputs = tf.keras.layers.Dense(1, activation="sigmoid")(x)
            model = tf.keras.Model(inputs, outputs)
            model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
            return model

        try:
            transformer_model = _build_transformer((seq_train.shape[1], seq_train.shape[2]))
            batch_size = int(max(16, seq_train.shape[0] * TRANSFORMER_BATCH_FRACTION))
            batch_size = min(batch_size, 128)
            transformer_model.fit(
                seq_train,
                y_train,
                epochs=max(TRANSFORMER_EPOCHS, 3),
                batch_size=batch_size,
                verbose=0,
            )
            trans_train_probs = transformer_model.predict(seq_train, verbose=0).reshape(-1)
            trans_test_probs = transformer_model.predict(seq_test, verbose=0).reshape(-1)

            trans_accuracy = accuracy_score(y_test, (trans_test_probs >= 0.5).astype(int))
            trans_ll = log_loss(
                y_test,
                np.column_stack([1.0 - trans_test_probs, trans_test_probs]),
            )

            metadata_records.append(
                ModelMetadata(
                    name="sequence_transformer",
                    accuracy=float(trans_accuracy),
                    log_loss=float(trans_ll),
                )
            )
            fitted_models["sequence_transformer"] = {
                "type": "sequence_transformer",
                "model": transformer_model,
                "feature_dim": seq_train.shape[2],
                "sequence_window": seq_train.shape[1],
                "config": {
                    "heads": TRANSFORMER_HEADS,
                    "dff": TRANSFORMER_DFF,
                    "dropout": TRANSFORMER_DROPOUT,
                    "epochs": max(TRANSFORMER_EPOCHS, 3),
                    "batch_size": batch_size,
                },
            }
            model_prob_store["sequence_transformer"] = trans_test_probs
            train_prob_store["sequence_transformer"] = trans_train_probs
            weight_map["sequence_transformer"] = float(np.clip(trans_accuracy, 0.6, 0.995))
        except Exception as exc:  # pragma: no cover - transformer optional failures
            print(f"[sequence] Skipping transformer model: {exc}", flush=True)

    for record in metadata_records:
        if record.name not in weight_map:
            base_weight = max(record.accuracy, 0.55)
            weight_map[record.name] = float(np.clip(base_weight, 0.55, 0.99))

    multitask_context: dict[str, Any] | None = None
    if HAS_TENSORFLOW and sport:
        feature_dim = X_np.shape[1]
        try:
            if MULTITASK_DATA_PATH.exists():
                data = np.load(MULTITASK_DATA_PATH, allow_pickle=True)
                sports_list = data["sports"].tolist()
                multi_features = data["features"]
                multi_labels = data["labels"]
                multi_sport_ids = data["sport_ids"]
                if multi_features.shape[1] != feature_dim:
                    sports_list = []
                    multi_features = np.empty((0, feature_dim), dtype=float)
                    multi_labels = np.empty((0,), dtype=int)
                    multi_sport_ids = np.empty((0,), dtype=int)
            else:
                sports_list = []
                multi_features = np.empty((0, feature_dim), dtype=float)
                multi_labels = np.empty((0,), dtype=int)
                multi_sport_ids = np.empty((0,), dtype=int)
        except Exception:
            sports_list = []
            multi_features = np.empty((0, feature_dim), dtype=float)
            multi_labels = np.empty((0,), dtype=int)
            multi_sport_ids = np.empty((0,), dtype=int)

        if sport not in sports_list:
            sports_list.append(sport)
        sport_id = sports_list.index(sport)

        multi_features = np.vstack([multi_features, X_np])
        multi_labels = np.concatenate([multi_labels, y_np])
        multi_sport_ids = np.concatenate([multi_sport_ids, np.full(len(X_np), sport_id, dtype=int)])

        try:
            np.savez_compressed(
                MULTITASK_DATA_PATH,
                sports=np.array(sports_list, dtype=object),
                features=multi_features,
                labels=multi_labels,
                sport_ids=multi_sport_ids,
            )
        except Exception as exc:
            print(f"[multitask] Failed to persist dataset: {exc}", flush=True)

        unique_sports = np.unique(multi_sport_ids)
        if unique_sports.size >= 2 and multi_labels.size >= 400:
            try:
                num_sports = len(sports_list)
                one_hot = np.eye(num_sports)[multi_sport_ids]
                multitask_input = np.hstack([multi_features, one_hot])
                multitask_model = tf.keras.Sequential(
                    [
                        tf.keras.layers.Input(shape=(multitask_input.shape[1],)),
                        tf.keras.layers.Dense(64, activation="relu"),
                        tf.keras.layers.Dropout(0.2),
                        tf.keras.layers.Dense(32, activation="relu"),
                        tf.keras.layers.Dense(1, activation="sigmoid"),
                    ]
                )
                multitask_model.compile(
                    optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"]
                )
                multitask_model.fit(
                    multitask_input,
                    multi_labels,
                    epochs=max(3, SEQUENCE_EPOCHS),
                    batch_size=128,
                    verbose=0,
                )
                try:
                    multitask_model.save(MULTITASK_MODEL_PATH, overwrite=True)
                except Exception:
                    pass
                test_one_hot = np.eye(num_sports)[np.full(len(X_test), sport_id, dtype=int)]
                multitask_test_input = np.hstack([X_test, test_one_hot])
                multitask_probs_test = multitask_model.predict(
                    multitask_test_input, verbose=0
                ).reshape(-1)
                multitask_accuracy = accuracy_score(
                    y_test, (multitask_probs_test >= 0.5).astype(int)
                )
                multitask_ll = log_loss(
                    y_test,
                    np.column_stack([1.0 - multitask_probs_test, multitask_probs_test]),
                )
                metadata_records.append(
                    ModelMetadata(
                        name="multitask_dense",
                        accuracy=float(multitask_accuracy),
                        log_loss=float(multitask_ll),
                    )
                )
                fitted_models["multitask_dense"] = {
                    "type": "multitask",
                    "model": multitask_model,
                    "sports": sports_list,
                }
                model_prob_store["multitask_dense"] = multitask_probs_test
                multitask_train_one_hot = np.eye(num_sports)[
                    np.full(len(X_train), sport_id, dtype=int)
                ]
                multitask_train_input = np.hstack([X_train, multitask_train_one_hot])
                multitask_train_probs = multitask_model.predict(
                    multitask_train_input, verbose=0
                ).reshape(-1)
                train_prob_store["multitask_dense"] = multitask_train_probs
                weight_map["multitask_dense"] = float(np.clip(multitask_accuracy, 0.6, 0.995))
                multitask_context = {
                    "sports": sports_list,
                    "num_sports": num_sports,
                    "sport_id": sport_id,
                }
            except Exception as exc:  # pragma: no cover
                print(f"[multitask] Skipping multi-task model: {exc}", flush=True)

    meta_info: dict[str, Any] | None = None
    if len(train_prob_store) >= 2:
        meta_feature_names = list(train_prob_store.keys())
        try:
            train_meta_matrix = np.vstack([train_prob_store[name] for name in meta_feature_names]).T
            test_meta_matrix = np.vstack([model_prob_store[name] for name in meta_feature_names]).T
            if train_meta_matrix.shape[0] == len(y_train) and test_meta_matrix.shape[0] == len(
                y_test
            ):
                base_meta_model = LogisticRegression(max_iter=2000)
                calibration_folds = min(5, max(2, len(y_train) // 100))
                try:
                    meta_model = CalibratedClassifierCV(
                        estimator=base_meta_model,
                        method="isotonic",
                        cv=calibration_folds,
                    )
                except TypeError:
                    # Fallback for older scikit-learn versions that expect base_estimator
                    meta_model = CalibratedClassifierCV(
                        base_estimator=base_meta_model,
                        method="isotonic",
                        cv=calibration_folds,
                    )
                meta_model.fit(train_meta_matrix, y_train)
                meta_probs = meta_model.predict_proba(test_meta_matrix)[:, 1]
                meta_accuracy = accuracy_score(y_test, (meta_probs >= 0.5).astype(int))
                meta_ll = log_loss(
                    y_test,
                    np.column_stack([1.0 - meta_probs, meta_probs]),
                )
                metadata_records.append(
                    ModelMetadata(
                        name="meta_logistic", accuracy=float(meta_accuracy), log_loss=float(meta_ll)
                    )
                )
                model_prob_store["meta_logistic"] = meta_probs
                try:
                    train_prob_store["meta_logistic"] = meta_model.predict_proba(train_meta_matrix)[
                        :, 1
                    ]
                except Exception:
                    pass
                weight_map["meta_logistic"] = float(np.clip(meta_accuracy, 0.65, 0.995))
                meta_info = {
                    "model": meta_model,
                    "feature_names": meta_feature_names,
                    "calibration": {"method": "isotonic", "cv": calibration_folds},
                }
        except Exception as exc:  # pragma: no cover
            print(f"[meta] Skipping meta-learner: {exc}", flush=True)

    ensemble_probs = None
    if model_prob_store:
        weights_np = np.asarray(
            [weight_map[name] for name in model_prob_store],
            dtype=float,
        )
        probs_np = np.vstack([model_prob_store[name] for name in model_prob_store])
        if weights_np.size > 0:
            ensemble_probs = np.average(probs_np, axis=0, weights=weights_np)

    if ensemble_probs is None:
        ensemble_probs = np.full_like(y_test, fill_value=0.5, dtype=float)
    if meta_info and "meta_logistic" in model_prob_store:
        ensemble_probs = model_prob_store["meta_logistic"]

    ensemble_preds = (ensemble_probs >= 0.5).astype(int)
    ensemble_accuracy = accuracy_score(y_test, ensemble_preds)
    brier = float(np.mean((ensemble_probs - y_test) ** 2))

    test_meta = [sample_metadata[i] for i in idx_test if i < len(sample_metadata)]
    simulated_roi = 0.0
    stakes = 0.0
    for prob, outcome, meta in zip(ensemble_probs, y_test, test_meta):
        implied = meta.get("home_prob_implied")
        if implied in (None, 0):
            continue
        edge = prob - implied
        if edge <= EDGE_THRESHOLD:
            continue
        decimal_odds = 1.0 / implied
        stake = MAX_RISK_PER_BET
        stakes += stake
        if outcome == 1:
            simulated_roi += stake * (decimal_odds - 1.0)
        else:
            simulated_roi -= stake
    roi_pct = (simulated_roi / stakes) if stakes > 0 else 0.0
    bayesian_variances: list[float] = []
    if model_prob_store:
        model_names = list(model_prob_store.keys())
        weights_for_variance = [weight_map.get(name, 0.6) for name in model_names]
        prior_alpha = 1.0
        prior_beta = 1.0
        for sample_idx in range(len(ensemble_probs)):
            sample_probs = [model_prob_store[name][sample_idx] for name in model_names]
            _, _, _, variance = compute_bayesian_stats(
                weights_for_variance,
                sample_probs,
                prior_alpha=prior_alpha,
                prior_beta=prior_beta,
            )
            bayesian_variances.append(variance)
    clv_samples = [
        calculate_clv(meta.get("home_prob_open"), meta.get("home_prob_implied"))
        for meta in test_meta
        if meta.get("home_prob_open") and meta.get("home_prob_implied")
    ]
    avg_clv = float(np.mean(clv_samples)) if clv_samples else 0.0
    avg_bayesian_variance = float(np.mean(bayesian_variances)) if bayesian_variances else 0.0

    eval_metrics = {
        "ensemble_accuracy": float(ensemble_accuracy),
        "brier_score": brier,
        "test_samples": int(len(y_test)),
        "simulated_roi": float(roi_pct),
        "avg_clv": avg_clv,
        "avg_bayesian_variance": avg_bayesian_variance,
    }
    if metadata_records:
        eval_metrics["model_breakdown"] = [asdict(record) for record in metadata_records]

    sequence_window = None
    if sequence_array is not None and getattr(sequence_array, "ndim", 0) == 3:
        sequence_window = int(sequence_array.shape[1])

    return (
        {
            "type": "ensemble",
            "models": fitted_models,
            "metadata": [asdict(m) for m in metadata_records],
            "weights": weight_map,
            "bayesian_prior": {"alpha": 1.0, "beta": 1.0},
            "meta": meta_info,
            "sequence_window": sequence_window,
            "multitask_context": multitask_context,
        },
        metadata_records,
        eval_metrics,
    )


def _predict_from_bundle(
    bundle: dict[str, Any],
    features: list[float],
    sequence_vector: list[list[float]] | None = None,
    sport: str | None = None,
) -> tuple[float, dict[str, float]]:
    if bundle.get("type") != "ensemble":
        return 0.5, {"alpha": 1.0, "beta": 1.0, "mean": 0.5, "variance": 0.25}

    metadata_list = bundle.get("metadata") or []
    models = bundle.get("models") or {}
    weight_map = bundle.get("weights", {})
    meta_info = bundle.get("meta") or {}
    sequence_window = bundle.get("sequence_window")

    model_probs: dict[str, float] = {}
    weights: list[float] = []
    probs: list[float] = []

    for meta_dict in metadata_list:
        name = meta_dict.get("name")
        if not name or name == "meta_logistic":
            continue
        model = models.get(name)
        if model is None:
            continue

        prob: float | None = None
        if isinstance(model, dict):
            model_type = model.get("type")
            if model_type == "sequence":
                seq_model = model.get("model")
                if seq_model is None or sequence_vector is None:
                    continue
                seq_data = sequence_vector
                seq_win = int(model.get("sequence_window", sequence_window or len(seq_data)))
                if len(seq_data) > seq_win:
                    seq_data = seq_data[-seq_win:]
                elif len(seq_data) < seq_win and seq_data:
                    pad = [[0.0] * len(seq_data[0]) for _ in range(seq_win - len(seq_data))]
                    seq_data = pad + seq_data
                try:
                    seq_array = np.asarray([seq_data], dtype=float)
                except Exception:
                    continue
                prob = float(seq_model.predict(seq_array, verbose=0).reshape(-1)[0])
            elif model_type == "multitask":
                multi_model = model.get("model")
                sports_list = model.get("sports") or []
                if multi_model is None or sport is None or sport not in sports_list:
                    continue
                num_sports = len(sports_list)
                sport_idx = sports_list.index(sport)
                sport_vec = np.zeros(num_sports, dtype=float)
                sport_vec[sport_idx] = 1.0
                input_vec = np.concatenate([np.asarray(features, dtype=float), sport_vec]).reshape(
                    1, -1
                )
                prob = float(multi_model.predict(input_vec, verbose=0).reshape(-1)[0])
            else:
                try:
                    prob = float(model.predict_proba([features])[0][1])
                except Exception:
                    continue
        else:
            try:
                prob = float(model.predict_proba([features])[0][1])
            except Exception:
                continue

        if prob is None:
            continue
        model_probs[name] = prob
        weight = weight_map.get(name, max(meta_dict.get("accuracy", 0.5), 0.5))
        weights.append(weight)
        probs.append(prob)

    feature_names = meta_info.get("feature_names") if meta_info else None
    meta_model = meta_info.get("model") if meta_info else None
    if feature_names and meta_model and all(name in model_probs for name in feature_names):
        meta_vector = [model_probs[name] for name in feature_names]
        try:
            meta_prob = float(meta_model.predict_proba([meta_vector])[0][1])
            weight = weight_map.get("meta_logistic", 0.7)
            model_probs["meta_logistic"] = meta_prob
            weights.append(weight)
            probs.append(meta_prob)
        except Exception:
            pass

    if not probs:
        return 0.5, {"alpha": 1.0, "beta": 1.0, "mean": 0.5, "variance": 0.25}

    weights_np = np.asarray(weights)
    probs_np = np.asarray(probs)
    prob = float(np.average(probs_np, weights=weights_np))
    prior = bundle.get("bayesian_prior", {})
    alpha, beta, mean, variance = compute_bayesian_stats(
        weights_np,
        probs_np,
        prior_alpha=float(prior.get("alpha", 1.0)),
        prior_beta=float(prior.get("beta", 1.0)),
    )
    return prob, {
        "alpha": alpha,
        "beta": beta,
        "mean": mean,
        "variance": variance,
    }


def ensemble_predict(
    model_bundle: dict[str, Any],
    features: list[float],
    regime: str = "default",
    sequence_vector: list[list[float]] | None = None,
    sport: str | None = None,
) -> tuple[float, dict[str, float]]:
    bundle_type = model_bundle.get("type")
    if bundle_type == "ensemble_regime":
        regime_bundles = model_bundle.get("models_by_regime", {})
        target = regime_bundles.get(regime) or regime_bundles.get("default")
        if not target:
            return 0.5, {"alpha": 1.0, "beta": 1.0, "mean": 0.5, "variance": 0.25}
        return _predict_from_bundle(target, features, sequence_vector, sport)
    return _predict_from_bundle(model_bundle, features, sequence_vector, sport)


def persist_summary(sport: str, payload: dict[str, Any]) -> None:
    file_path = STATE / f"sports_predictions_{sport}.json"
    file_path.write_text(json.dumps(payload, indent=2))
    index_path = STATE / "sports_predictions.json"
    if index_path.exists():
        try:
            existing = json.loads(index_path.read_text())
        except json.JSONDecodeError:
            existing = {}
        existing[sport] = payload
    existing["last_update"] = datetime.now(UTC).isoformat()
    index_path.write_text(json.dumps(existing, indent=2))

    with PREDICTIONS_LOG.open("a", encoding="utf-8") as log_file:
        log_file.write(
            json.dumps({"sport": sport, "timestamp": payload.get("timestamp")}, ensure_ascii=False)
            + "\n"
        )


def fallback_predictions(games: list[GameRecord], sport: str) -> dict[str, Any]:
    predictions = []
    for game in games[:5]:
        predictions.append(
            {
                "game_id": game.game_id,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "home_win_probability": 0.55,
                "away_win_probability": 0.45,
                "confidence": 0.55,
                "edge": 0.05,
                "recommended_side": game.home_team,
                "sport": sport,
            }
        )
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "sport": sport,
        "model": {"type": "mock"},
        "predictions": predictions,
    }


def process_sport(sport: str) -> dict[str, Any]:
    seasons = generate_season_list(YEARS_OF_HISTORY)

    if sport == "soccer":
        backfill_soccer_history(seasons, SOCCER_LEAGUES)
    else:
        backfill_sportradar_history(sport, seasons)
    backfill_odds_history(sport, seasons)

    games = load_game_history(sport, seasons)
    odds = load_odds_history(sport, seasons)

    # EINSTEIN-LEVEL FIX: Fetch real-time schedules for today
    try:
        from agents.sports_realtime_schedule import fetch_realtime_schedules

        realtime_schedules = fetch_realtime_schedules([sport])
        print(
            f"[sports_analytics] ✅ Fetched real-time schedule for {sport}: {len(realtime_schedules.get(sport, []))} games",
            flush=True,
        )
    except Exception as e:
        print(
            f"[sports_analytics] ⚠️ Real-time schedule fetch failed: {e}, using historical data",
            flush=True,
        )
        realtime_schedules = None

    if not games:
        return fallback_predictions([], sport)

    builder = FeatureBuilder(sport, games, odds)
    X, y, metadata, _, sequence_vectors = builder.build_datasets()

    # Save Elo ratings after processing historical games
    if USE_ELO and builder.elo_system:
        builder.elo_system.save()
        print(f"[{sport}] Saved Elo ratings", flush=True)

    if len(X) < 20:
        return fallback_predictions(games, sport)

    default_bundle, _, default_metrics = train_ensemble(X, y, metadata, sequence_vectors, sport)

    regime_groups: dict[str, list[int]] = defaultdict(list)
    for idx, meta_entry in enumerate(metadata):
        regime_label = meta_entry.get("regime") or "default"
        regime_groups[regime_label].append(idx)
    if "default" not in regime_groups:
        regime_groups["default"] = list(range(len(X)))

    models_by_regime: dict[str, dict[str, Any]] = {"default": default_bundle}
    combined_metrics: dict[str, Any] = {
        "overall": default_metrics,
        "regimes": {"default": default_metrics},
    }

    for regime_label, idxs in regime_groups.items():
        if regime_label == "default":
            continue
        if len(idxs) < MIN_REGIME_SAMPLES:
            continue
        subset_X = [X[i] for i in idxs]
        subset_y = [y[i] for i in idxs]
        subset_meta = [metadata[i] for i in idxs]
        subset_sequences = (
            [sequence_vectors[i] for i in idxs if sequence_vectors and i < len(sequence_vectors)]
            if sequence_vectors
            else None
        )
        regime_bundle, _, regime_metrics = train_ensemble(
            subset_X, subset_y, subset_meta, subset_sequences, None
        )
        if regime_bundle.get("type") == "mock":
            continue
        models_by_regime[regime_label] = regime_bundle
        combined_metrics["regimes"][regime_label] = regime_metrics

    model_bundle = {
        "type": "ensemble_regime",
        "models_by_regime": models_by_regime,
        "metadata": default_bundle.get("metadata"),
    }
    regime_metadata_summary = {
        regime: bundle.get("metadata") for regime, bundle in models_by_regime.items()
    }

    # Use real-time schedules if available, otherwise fall back to historical
    future_entries = builder.build_future_features(
        datetime.now(UTC), realtime_schedules=realtime_schedules if realtime_schedules else None
    )

    predictions = []
    for game, feature_vector, meta in future_entries:
        regime_label = meta.get("regime", "default")
        sequence_vector = meta.get("sequence_vector")
        prob_home, bayes_stats = ensemble_predict(
            model_bundle,
            feature_vector,
            regime_label,
            sequence_vector,
            sport,
        )
        prob_away = 1.0 - prob_home
        implied = meta.get("home_prob_implied") or 0.5
        edge = prob_home - implied
        recommended_side = game.home_team if edge >= 0 else game.away_team
        confidence = max(prob_home, prob_away)
        if confidence < CONFIDENCE_THRESHOLD:
            continue
        line_movement_value = meta.get("line_movement")
        if line_movement_value is None:
            line_movement_value = 0.0
        clv_estimate = meta.get("clv_estimate")

        predictions.append(
            {
                "game_id": game.game_id,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "home_win_probability": round(prob_home, 4),
                "away_win_probability": round(prob_away, 4),
                "confidence": round(confidence, 4),
                "edge": round(edge, 4),
                "recommended_side": recommended_side,
                "implied_home_prob": meta.get("home_prob_implied"),
                "implied_away_prob": meta.get("away_prob_implied"),
                "home_prob_open": meta.get("home_prob_open"),
                "away_prob_open": meta.get("away_prob_open"),
                "line_movement": round(line_movement_value, 4),
                "sharp_signal": meta.get("sharp_signal"),
                "regime": regime_label,
                "clv_estimate": round(clv_estimate, 4) if clv_estimate is not None else None,
                "bayesian_mean": round(bayes_stats.get("mean", prob_home), 4),
                "bayesian_variance": round(bayes_stats.get("variance", 0.0), 6),
                "bayesian_alpha": round(bayes_stats.get("alpha", 0.0), 4),
                "bayesian_beta": round(bayes_stats.get("beta", 0.0), 4),
                "scheduled": meta.get("scheduled"),
                "sport": sport,
            }
        )

    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "sport": sport,
        "model": {
            "type": model_bundle.get("type"),
            "metadata": model_bundle.get("metadata"),
            "regime_metadata": regime_metadata_summary,
        },
        "training_samples": len(X),
        "metrics": combined_metrics,
        "predictions": predictions,
    }
    return payload


def main() -> None:
    print(
        f"[sports_analytics] Starting sports analytics ensemble (history={YEARS_OF_HISTORY}y, threshold={CONFIDENCE_THRESHOLD:.2f})",
        flush=True,
    )
    
    # Quick startup validation
    try:
        print("[sports_analytics] Validating dependencies...", flush=True)
        if not HAS_PANDAS:
            raise ImportError("pandas is required but not installed")
        if not HAS_NUMPY:
            raise ImportError("numpy is required but not installed")
        if not HAS_SKLEARN:
            raise ImportError("scikit-learn is required but not installed")
        print("[sports_analytics] ✅ Dependencies validated", flush=True)
    except Exception as e:
        print(f"[sports_analytics] ❌ Startup validation failed: {e}", flush=True)
        sys.exit(1)

    # Initial delay to let other agents start first
    print("[sports_analytics] Waiting 10 seconds for system initialization...", flush=True)
    time.sleep(10)

    consecutive_errors = 0
    max_consecutive_errors = 3

    while True:
        try:
            for sport in SPORTS:
                print(f"[sports_analytics] Processing {sport.upper()}...", flush=True)
                try:
                    payload = process_sport(sport)
                    persist_summary(sport, payload)
                    summary = payload.get("model", {}).get("metadata") or []
                    accuracy = summary[0]["accuracy"] if summary else "n/a"
                    print(
                        f"[sports_analytics] ✅ {sport.upper()} predictions ready • edges={len(payload.get('predictions', []))} • top acc={accuracy}",
                        flush=True,
                    )
                    consecutive_errors = 0  # Reset on success
                    time.sleep(2)
                except Exception as sport_error:
                    print(f"[sports_analytics] ⚠️ Error processing {sport}: {sport_error}", flush=True)
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"[sports_analytics] ❌ Too many consecutive errors ({consecutive_errors}), exiting", flush=True)
                        sys.exit(1)
                    time.sleep(30)  # Short delay before retry
                    continue

            print("[sports_analytics] Sleeping 30 minutes before next sweep", flush=True)
            consecutive_errors = 0  # Reset on successful sweep
            time.sleep(1800)
        except KeyboardInterrupt:
            print("[sports_analytics] Interrupted by user", flush=True)
            break
        except Exception as exc:
            consecutive_errors += 1
            print(f"[sports_analytics] Error: {exc}", flush=True)
            traceback.print_exc()
            if consecutive_errors >= max_consecutive_errors:
                print(f"[sports_analytics] ❌ Too many consecutive errors ({consecutive_errors}), exiting", flush=True)
                sys.exit(1)
            time.sleep(300)


if __name__ == "__main__":
    main()

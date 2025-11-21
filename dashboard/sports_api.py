#!/usr/bin/env python3
"""FastAPI endpoints for sports betting dashboard."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

ROOT = Path.home() / "neolight"
STATE = ROOT / "state"
DASHBOARD = ROOT / "dashboard"
CLV_FILE = STATE / "sports_paper_clv.json"

router = APIRouter(prefix="/api/sports", tags=["sports"])


@router.get("/")
async def sports_dashboard():
    """Serve the sports dashboard HTML."""
    dashboard_file = DASHBOARD / "sports_dashboard.html"
    if not dashboard_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(dashboard_file)


@router.get("/predictions")
async def get_predictions() -> dict[str, Any]:
    """Get current sports predictions."""
    predictions_file = STATE / "sports_predictions.json"
    if not predictions_file.exists():
        return {"predictions": [], "last_update": None}

    try:
        data = json.loads(predictions_file.read_text())
        return data
    except json.JSONDecodeError:
        return {"predictions": [], "last_update": None}


@router.get("/today")
async def get_today_bets() -> dict[str, Any]:
    """Get today's betting recommendations with proper date filtering."""
    today = datetime.now().strftime("%Y-%m-%d")
    today_formats = [
        today,  # 2025-11-18
        datetime.now().strftime("%m/%d/%Y"),  # 11/18/2025
        datetime.now().strftime("%d/%m/%Y"),  # 18/11/2025
        datetime.now().strftime("%Y-%m-%d"),  # 2025-11-18
    ]

    results = {
        "date": today,
        "recommendations": [],
        "total_opportunities": 0,
        "total_expected_value": 0.0,
        "total_stake": 0.0,
    }

    # Check Einstein queue (top recommendations)
    einstein_file = STATE / "sports_einstein_queue.json"
    if einstein_file.exists():
        try:
            einstein_data = json.loads(einstein_file.read_text())
            opportunities = einstein_data.get("opportunities", [])

            for opp in opportunities:
                scheduled = opp.get("scheduled", "")
                # Check if scheduled date matches today in any format
                if any(today_format in str(scheduled) for today_format in today_formats):
                    results["recommendations"].append({
                        "sport": opp.get("sport", "unknown"),
                        "home_team": opp.get("home_team", ""),
                        "away_team": opp.get("away_team", ""),
                        "recommended_side": opp.get("recommended_side", ""),
                        "confidence": opp.get("confidence", 0.0),
                        "edge": opp.get("edge", 0.0),
                        "recommended_stake": opp.get("recommended_stake", 0.0),
                        "expected_value": opp.get("expected_value", 0.0),
                        "scheduled": scheduled,
                        "decimal_odds": opp.get("decimal_odds", 2.0),
                        "einstein_score": opp.get("einstein_score", 0.0),
                    })
                    results["total_expected_value"] += opp.get("expected_value", 0.0)
                    results["total_stake"] += opp.get("recommended_stake", 0.0)

            results["total_opportunities"] = len(results["recommendations"])
            # Sort by expected value descending
            results["recommendations"].sort(key=lambda x: x.get("expected_value", 0.0), reverse=True)
        except json.JSONDecodeError:
            pass

    # Also check predictions files for today's games
    predictions_file = STATE / "sports_predictions_nba.json"
    if predictions_file.exists():
        try:
            nba_data = json.loads(predictions_file.read_text())
            predictions = nba_data.get("predictions", [])
            for pred in predictions:
                scheduled = pred.get("scheduled", "")
                if any(today_format in str(scheduled) for today_format in today_formats):
                    # Check if not already in recommendations
                    game_id = f"{pred.get('home_team', '')}_{pred.get('away_team', '')}"
                    if not any(r.get("home_team") == pred.get("home_team") and
                              r.get("away_team") == pred.get("away_team")
                              for r in results["recommendations"]):
                        results["recommendations"].append({
                            "sport": "nba",
                            "home_team": pred.get("home_team", ""),
                            "away_team": pred.get("away_team", ""),
                            "recommended_side": pred.get("recommended_side", ""),
                            "confidence": pred.get("confidence", 0.0),
                            "edge": pred.get("edge", 0.0),
                            "recommended_stake": pred.get("recommended_stake", 0.0) or (1000 * 0.02 * (pred.get("edge", 0.0) / 0.02)),
                            "expected_value": pred.get("expected_value", 0.0) or (pred.get("edge", 0.0) * 1000 * 0.02),
                            "scheduled": scheduled,
                            "decimal_odds": pred.get("decimal_odds", 2.0),
                            "einstein_score": pred.get("einstein_score", 0.0),
                        })
        except json.JSONDecodeError:
            pass

    return results


@router.get("/arbitrage")
async def get_arbitrage() -> list[dict[str, Any]]:
    """Get current arbitrage opportunities."""
    arb_file = STATE / "sports_arbitrage_opportunities.json"
    if not arb_file.exists():
        return []

    try:
        data = json.loads(arb_file.read_text())
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


@router.get("/bankroll")
async def get_bankroll() -> dict[str, Any]:
    """Get current bankroll status."""
    bankroll_file = STATE / "sports_bankroll.json"
    if not bankroll_file.exists():
        return {"bankroll": 1000, "initial_bankroll": 1000, "updated_at": None}

    try:
        data = json.loads(bankroll_file.read_text())
        return data
    except json.JSONDecodeError:
        return {"bankroll": 1000, "initial_bankroll": 1000, "updated_at": None}


@router.get("/queue")
async def get_bet_queue() -> list[dict[str, Any]]:
    """Get manual bet queue."""
    queue_file = STATE / "manual_bet_queue.json"
    if not queue_file.exists():
        return []

    try:
        data = json.loads(queue_file.read_text())
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


@router.get("/history")
async def get_betting_history() -> list[dict[str, Any]]:
    """Get betting history for charts from paper trader."""
    paper_trades_file = STATE / "sports_paper_trades.json"
    if not paper_trades_file.exists():
        return []

    try:
        trades = json.loads(paper_trades_file.read_text())
        if not isinstance(trades, list):
            return []

        # Filter settled trades and group by date
        settled_trades = [t for t in trades if t.get("status") == "settled" and t.get("settled_at")]
        if not settled_trades:
            return []

        # Group by date and calculate daily P&L
        daily_data: dict[str, dict[str, Any]] = {}
        initial_bankroll = 10000.0  # Default paper bankroll

        for trade in settled_trades:
            settled_at = trade.get("settled_at", "")
            if not settled_at:
                continue

            # Extract date from ISO timestamp
            date = settled_at.split("T")[0] if "T" in settled_at else settled_at[:10]

            if date not in daily_data:
                daily_data[date] = {"date": date, "pnl": 0.0, "trades": 0, "wins": 0, "losses": 0}

            daily_data[date]["pnl"] += trade.get("pnl", 0.0)
            daily_data[date]["trades"] += 1
            if trade.get("result") == "win":
                daily_data[date]["wins"] += 1
            elif trade.get("result") == "loss":
                daily_data[date]["losses"] += 1

        # Convert to list and calculate cumulative bankroll
        history = []
        cumulative_pnl = 0.0
        for date in sorted(daily_data.keys()):
            daily_pnl = daily_data[date]["pnl"]
            cumulative_pnl += daily_pnl
            history.append({
                "date": date,
                "bankroll": initial_bankroll + cumulative_pnl,
                "pnl": daily_pnl,
                "trades": daily_data[date]["trades"],
                "wins": daily_data[date]["wins"],
                "losses": daily_data[date]["losses"],
            })

        return history
    except json.JSONDecodeError:
        return []
    except Exception as e:
        print(f"Error loading betting history: {e}")
        return []


@router.get("/results")
async def get_betting_results() -> dict[str, Any]:
    """Get recent betting results and performance."""
    paper_trades_file = STATE / "sports_paper_trades.json"
    paper_summary_file = STATE / "sports_paper_summary.json"

    results = {
        "recent_trades": [],
        "summary": {},
        "performance": {},
    }

    # Load recent settled trades
    if paper_trades_file.exists():
        try:
            trades = json.loads(paper_trades_file.read_text())
            settled = [t for t in trades if t.get("status") == "settled"]
            # Sort by settled_at descending, get last 20
            settled.sort(key=lambda x: x.get("settled_at", ""), reverse=True)
            results["recent_trades"] = settled[:20]
        except json.JSONDecodeError:
            pass

    # Load summary
    if paper_summary_file.exists():
        try:
            results["summary"] = json.loads(paper_summary_file.read_text())
        except json.JSONDecodeError:
            pass

    # Calculate performance metrics
    if results["recent_trades"]:
        wins = sum(1 for t in results["recent_trades"] if t.get("result") == "win")
        losses = sum(1 for t in results["recent_trades"] if t.get("result") == "loss")
        total_pnl = sum(t.get("pnl", 0.0) for t in results["recent_trades"])

        results["performance"] = {
            "win_rate": (wins / len(results["recent_trades"]) * 100) if results["recent_trades"] else 0.0,
            "total_pnl": total_pnl,
            "wins": wins,
            "losses": losses,
            "total_trades": len(results["recent_trades"]),
        }

    return results


@router.post("/queue/update")
async def update_bet_queue(bet_id: str, status: str, result: str = None) -> dict[str, str]:
    """Update a bet in the manual queue."""
    queue_file = STATE / "manual_bet_queue.json"
    if not queue_file.exists():
        raise HTTPException(status_code=404, detail="Queue not found")

    try:
        queue = json.loads(queue_file.read_text())

        for bet in queue:
            if bet.get("id") == bet_id:
                bet["status"] = status
                if result:
                    bet["result"] = result
                break

        queue_file.write_text(json.dumps(queue, indent=2))
        return {"status": "success", "message": f"Bet {bet_id} updated"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest")
async def get_backtest_summary() -> dict[str, Any]:
    """Get sports backtest summary."""
    summary_file = STATE / "sports_backtest_summary.json"
    if not summary_file.exists():
        return {"status": "no_data"}

    try:
        data = json.loads(summary_file.read_text())
        return data
    except json.JSONDecodeError:
        return {"status": "error"}


def _load_clv_payload() -> dict[str, Any]:
    if not CLV_FILE.exists():
        return {"trades": [], "summary": {}}
    try:
        return json.loads(CLV_FILE.read_text())
    except json.JSONDecodeError:
        return {"trades": [], "summary": {}}


@router.get("/clv/summary")
async def get_clv_summary() -> dict[str, Any]:
    """Return CLV summary metrics and steam flags."""
    payload = _load_clv_payload()
    summary = payload.get("summary", {})
    trades = payload.get("trades", [])

    clv_values = [float(t.get("clv")) for t in trades if isinstance(t.get("clv"), (int, float))]
    total_trades = len(trades)
    total_numeric = len(clv_values)
    positive = sum(1 for value in clv_values if value > 0)
    avg_clv = (sum(clv_values) / total_numeric) if total_numeric else None

    summary_defaults = {
        "total_trades": total_trades,
        "positive_rate": (positive / total_numeric) if total_numeric else None,
        "average_clv": avg_clv,
        "steam_summary": summary.get("steam_summary", {}),
        "weekly_leaders": summary.get("weekly_leaders", []),
        "monthly_leaders": summary.get("monthly_leaders", []),
        "distribution": summary.get("distribution", {}),
        "flags": summary.get("flags", {}),
        "portfolio": summary.get("portfolio", {}),
        "by_sport": summary.get("by_sport", []),
        "by_league": summary.get("by_league", []),
        "by_regime": summary.get("by_regime", []),
        "by_steam": summary.get("by_steam", []),
        "postgame_reviews": summary.get("postgame_reviews", []),
        "learning_insights": summary.get("learning_insights", []),
        "generated_at": summary.get("generated_at"),
    }

    return summary_defaults


@router.get("/clv/trades")
async def get_clv_trades(
    limit: int = 250,
    sport: Optional[str] = None,
    steam: Optional[str] = None,
    regime: Optional[str] = None,
) -> dict[str, Any]:
    """Return individual CLV trade records with optional filters."""
    payload = _load_clv_payload()
    trades = payload.get("trades", [])

    if sport:
        trades = [t for t in trades if str(t.get("sport", "")).lower() == sport.lower()]
    if steam:
        trades = [t for t in trades if str(t.get("steam_direction", "")).lower() == steam.lower()]
    if regime:
        trades = [t for t in trades if str(t.get("regime", "")).lower() == regime.lower()]

    trades_sorted = sorted(trades, key=lambda t: t.get("placed_at"), reverse=True)
    sliced = trades_sorted[: max(limit, 0)]
    return {"count": len(trades), "trades": sliced}

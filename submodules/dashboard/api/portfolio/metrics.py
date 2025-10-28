# api/portfolio/metrics.py
from fastapi import APIRouter
from tools.portfolio_manager import InstitutionalPortfolioManager

router = APIRouter()

@router.post("/api/portfolio/metrics")
def calculate_metrics(returns: list[float], benchmark: list[float]):
    pm = InstitutionalPortfolioManager(returns)
    return {
        "sharpe": pm.sharpe_ratio(),
        "sortino": pm.sortino_ratio(),
        "calmar": pm.calmar_ratio(),
        "beta": pm.beta(benchmark),
        "var_95": pm.value_at_risk(0.95)
    }

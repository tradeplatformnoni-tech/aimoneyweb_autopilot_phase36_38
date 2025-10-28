#!/bin/bash

echo "🏦 Starting Phase 1101–1200: Institutional Portfolio Manager..."

mkdir -p tools
mkdir -p api/portfolio

# Create portfolio manager module
cat <<EOT > tools/portfolio_manager.py
# tools/portfolio_manager.py
import numpy as np

class InstitutionalPortfolioManager:
    def __init__(self, returns):
        self.returns = returns

    def sharpe_ratio(self):
        return round(np.mean(self.returns) / np.std(self.returns), 3)

    def sortino_ratio(self):
        downside = [r for r in self.returns if r < 0]
        return round(np.mean(self.returns) / (np.std(downside) or 1), 3)

    def calmar_ratio(self):
        max_drawdown = max([abs(min(self.returns[i:] or [0])) for i in range(len(self.returns))])
        return round(np.mean(self.returns) / (max_drawdown or 1), 3)

    def beta(self, benchmark_returns):
        covariance = np.cov(self.returns, benchmark_returns)[0][1]
        variance = np.var(benchmark_returns)
        return round(covariance / variance, 3)

    def value_at_risk(self, confidence=0.95):
        return round(np.percentile(self.returns, (1 - confidence) * 100), 3)
EOT

# Metrics API
cat <<EOT > api/portfolio/metrics.py
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
EOT

# Adjust API placeholder
cat <<EOT > api/portfolio/adjust.py
# api/portfolio/adjust.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/api/portfolio/adjust")
def adjust_portfolio():
    return {"status": "🔧 Adjustment logic coming soon"}
EOT

# Inject into backend/main.py
main_file="backend/main.py"
if grep -q "portfolio" "$main_file"; then
    echo "✅ Portfolio routes already configured."
else
    echo "⚙️ Patching backend/main.py for portfolio API..."
    sed -i '' '/from fastapi import FastAPI/a\
from api.portfolio import metrics, adjust' $main_file

    sed -i '' '/app = FastAPI()/a\
app.include_router(metrics.router)\napp.include_router(adjust.router)' $main_file
fi

# Restart
pm2 restart neolight || echo "⚠️ PM2 not found. Restart manually."

echo "✅ Institutional Portfolio Manager Activated!"
echo "🧪 Test metrics via POST to /api/portfolio/metrics"


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

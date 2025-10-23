def tripped(pnl_pct, max_drawdown_pct, var_est):
    # kill if >5% dd or VaR > 3% or pnl below -2% intraday
    return (max_drawdown_pct<=-0.05) or (var_est>0.03) or (pnl_pct<-0.02)

import numpy as np
def forecast_pnl(equity_series):
    if len(equity_series)<5: return 0
    x=np.arange(len(equity_series)); y=np.array(equity_series)
    slope=np.polyfit(x,y,1)[0]
    return float(slope/1000)

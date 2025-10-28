import numpy as np
def value_at_risk(pnl_series,alpha=0.05):
    if len(pnl_series)<5: return 0
    return -np.percentile(pnl_series,100*alpha)

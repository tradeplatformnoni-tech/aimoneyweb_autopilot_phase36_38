import numpy as np
def compute_drawdown(equity_series):
    if len(equity_series)<2:return 0
    peak=max(equity_series)
    trough=equity_series[-1]
    dd=(peak-trough)/peak*100
    return dd
def position_size(signal,equity,drawdown):
    base=equity*0.01
    adj=(1-abs(signal))*max(0.2,1-drawdown/20)
    return max(base*adj,100)

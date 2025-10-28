import numpy as np
from ai import agent_alpha, agent_beta, agent_gamma
def fuse_signals(pnl,risk,equity,drawdown):
    a=agent_alpha.predict_signal(pnl,risk)
    b=agent_beta.predict_signal(pnl,risk)
    c=agent_gamma.predict_signal(pnl,risk)
    weights=[0.5,0.3,0.2]
    raw=np.dot([a,b,c],weights)
    risk_adj=max(0.1,1-drawdown/10)
    return float(raw*risk_adj)

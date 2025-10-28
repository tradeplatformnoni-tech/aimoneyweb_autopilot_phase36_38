import numpy as np, random
def predict_signal(pnl,risk):
    return (pnl/(risk+1e-6))*np.exp(-abs(pnl)*5)+random.uniform(-0.1,0.1)

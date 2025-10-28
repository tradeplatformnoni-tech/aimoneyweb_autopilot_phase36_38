import numpy as np, random
def predict_signal(pnl,risk):
    return np.sin(pnl*15)+random.uniform(-0.05,0.05)

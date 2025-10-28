import numpy as np, random
def predict_signal(pnl,risk):
    return np.tanh(pnl*10 - risk*5 + random.uniform(-0.1,0.1))

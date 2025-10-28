import numpy as np
def consensus(votes):
    arr=np.sign(votes)
    return float(np.sign(np.sum(arr)))

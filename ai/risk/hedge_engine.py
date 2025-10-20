import random
def hedge_signal(signal):
    # invert if exposure too strong
    if abs(signal)>0.8: signal*=-0.5
    return signal

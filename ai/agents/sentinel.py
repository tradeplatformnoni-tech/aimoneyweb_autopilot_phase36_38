import random, time
def guard(signal, var, dd):
    if abs(signal)>1.2 or var>0.03 or dd>0.05:
        print("⚠️ Sentinel blocked over-risky signal.")
        return 0.0
    return signal

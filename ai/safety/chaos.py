import random
def maybe_fault():
    # inject 10% chance of mild fault signal (for resilience drills)
    return random.random()<0.10

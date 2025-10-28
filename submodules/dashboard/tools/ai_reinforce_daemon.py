# tools/ai_reinforce_daemon.py
import time
from ai.reinforcement.reinforce_engine import ReinforceEngine

engine = ReinforceEngine()

def simulate():
    for i in range(5):
        engine.observe("state", "buy", i, "new_state")
    engine.train()

if __name__ == "__main__":
    while True:
        simulate()
        time.sleep(60)

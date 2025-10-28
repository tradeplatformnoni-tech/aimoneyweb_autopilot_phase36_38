import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import time, traceback
from ai.risk.risk_engine import compute

if __name__=="__main__":
    print("📊 Risk daemon started (every 120s)")
    while True:
        try:
            compute()
        except Exception:
            traceback.print_exc()
        time.sleep(120)

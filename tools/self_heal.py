"""
tools/self_heal.py
Watches logs for anomalies and triggers corrective scripts.
"""
import time, os

LOG = "logs/backend.log"

def detect_issue():
    if not os.path.exists(LOG):
        return False
    with open(LOG) as f:
        lines = f.readlines()[-10:]
    return any("Traceback" in l or "ERROR" in l for l in lines)

if __name__ == "__main__":
    while True:
        if detect_issue():
            print("⚠️ Issue detected! Running AutoFix...")
            os.system("./neolight-fix")
        time.sleep(120)

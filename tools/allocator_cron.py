import time, traceback
from ai.allocators.goal_allocator import adapt

if __name__=="__main__":
    print("⚖️ Goal-allocator cron started (every 10 minutes)")
    while True:
        try:
            adapt()
        except Exception:
            traceback.print_exc()
        time.sleep(600)

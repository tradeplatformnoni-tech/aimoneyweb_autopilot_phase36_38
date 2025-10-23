"""
Disabled-by-default execution bridge.
Enable later by adding API keys and uncommenting trade() logic.
"""
import os, json
def trade(order):
    # --- PLACEHOLDER ---
    # Example structure only:
    # if os.getenv("ALPACA_API_KEY"):
    #     # send live order to Alpaca / Binance
    #     pass
    return {"status":"disabled","order":order}

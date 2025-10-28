import json, datetime, random
from ai.providers.commodity_provider import CommodityProvider
commodity = CommodityProvider()
from ai.providers.data_feed import get_bars_for_symbol

symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "SPY", "GOLD", "SILVER"]

def generate_signals():
    out = []
    for sym in symbols:
        if sym in ["GOLD", "SILVER"]:
            data = commodity.get_latest_prices()
            price = data.get('XAU' if sym == "GOLD" else 'XAG')
            if price:
                bars = [{"t": "now", "o": price, "h": price, "l": price, "c": price}]
                print(f"💰 Commodity feed OK: {sym} = {price}")
            else:
                print(f"⚠️ No price for {sym}")
                bars = []
        else:
            bars = get_bars_for_symbol(sym, limit=30)

if __name__ == "__main__":
    generate_signals()


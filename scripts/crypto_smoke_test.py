# Simple crypto data smoke test (CoinGecko ping + price fetch)
import requests, sys, json

def main():
    try:
        ping = requests.get("https://api.coingecko.com/api/v3/ping", timeout=5).json()
        print("✅ CoinGecko ping:", ping)
        for sym in ["bitcoin", "ethereum", "solana"]:
            r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={sym}&vs_currencies=usd", timeout=8).json()
            print(f"💰 {sym}: ${r.get(sym, {}).get('usd')}")
        print("🚦 Crypto data path OK.")
    except Exception as e:
        print("❌ Crypto smoke test failed:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()


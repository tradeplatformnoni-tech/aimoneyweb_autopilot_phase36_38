import time, traceback, random
from ai.sentiment.sentiment_stub import analyze

if __name__=="__main__":
    print("📰 Sentiment daemon started (every 90s)")
    samples = [
        "tech earnings beat expectations",
        "inflation concerns rising",
        "ai sector momentum surges",
        "crypto range-bound, volatility compressing"
    ]
    while True:
        try:
            analyze(random.choice(samples))
        except Exception:
            traceback.print_exc()
        time.sleep(90)

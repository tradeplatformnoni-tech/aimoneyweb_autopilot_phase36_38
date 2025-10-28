import random, datetime, json, pathlib
RUNTIME = pathlib.Path("runtime"); OUT = RUNTIME/"sentiment_log.jsonl"

def analyze(text="market outlook"):
    score = round(random.uniform(-1,1), 2)
    mood = "bullish" if score>0.25 else "bearish" if score<-0.25 else "neutral"
    data = {"timestamp": datetime.datetime.utcnow().isoformat(), "text": text, "score": score, "mood": mood}
    OUT.open("a").write(json.dumps(data)+"\n")
    return data

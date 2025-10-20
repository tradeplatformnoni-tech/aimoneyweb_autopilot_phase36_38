from textblob import TextBlob
import requests
def sentiment_boost(symbol="AAPL"):
    try:
        r=requests.get(f"https://api.marketaux.com/v1/news/all?symbols={symbol}&filter_entities=true&language=en&api_token=demo")
        data=r.json().get("data",[])
        txt=" ".join([x.get("title","") for x in data])
        s=TextBlob(txt).sentiment.polarity
        return s
    except Exception: return 0

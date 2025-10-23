"""
ai/nlp_query.py
Tiny offline NLP parser to answer questions about agent status and trades.
"""
import json, re, os

DATA = {
    "agents": ["Atlas","SportsInsight","CollectiblesBot","Studio"],
    "symbols": json.load(open("config/symbols.json")) if os.path.exists("config/symbols.json") else []
}

def query(text:str):
    t=text.lower()
    if "agents" in t: 
        return {"agents":DATA["agents"]}
    if "symbols" in t or "assets" in t:
        return {"symbols":DATA["symbols"]}
    return {"message":"Query understood but no matching data."}

if __name__=="__main__":
    q=input("Ask NeoLight: ")
    print(query(q))

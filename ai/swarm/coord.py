import json,random,requests,os,time
PEERS=["http://127.0.0.1:8000","http://127.0.0.1:8001"]
def broadcast_signal(sig):
    results=[]
    for peer in PEERS:
        try:
            r=requests.post(f"{peer}/api/swarm",json={"signal":sig},timeout=2)
            results.append(r.json().get("ack","ok"))
        except Exception as e:
            results.append(str(e))
    return results

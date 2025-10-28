import time,requests
def ping(peer="http://127.0.0.1:8000"):
    try:
        r=requests.get(peer+"/api/health",timeout=2)
        return r.status_code==200
    except Exception: return False

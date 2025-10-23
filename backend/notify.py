import json, os, requests
CONFIG_FILE="runtime/notify_config.json"
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f: return json.load(f)
    return {"discord_webhook": None, "telegram_token": None, "telegram_chat": None}
def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE,"w") as f: json.dump(cfg,f,indent=2)
def send_discord(msg,url):
    if not url: return {"status":"no webhook"}
    try:
        r=requests.post(url,json={"content":msg},timeout=8)
        return {"status":"ok","code":r.status_code}
    except Exception as e: return {"status":"error","error":str(e)}
def send_telegram(msg,token,chat):
    if not token or not chat: return {"status":"no token/chat"}
    try:
        url=f"https://api.telegram.org/bot{token}/sendMessage"
        r=requests.post(url,data={"chat_id":chat,"text":msg},timeout=8)
        return {"status":"ok","code":r.status_code}
    except Exception as e: return {"status":"error","error":str(e)}
def notify_all(message):
    cfg=load_config()
    return {
        "discord":  send_discord(message, cfg.get("discord_webhook")),
        "telegram": send_telegram(message, cfg.get("telegram_token"), cfg.get("telegram_chat"))
    }

#!/usr/bin/env bash
# NeoLight Phase 661–680  ::  Notification Integrator Autopilot
set -e
echo "🔔  NeoLight v4.2  – Notification Integrator"

# --- Create backend/notify.py ---
mkdir -p backend runtime
cat > backend/notify.py <<'PYCODE'
import json, os, requests
CONFIG_FILE = "runtime/notify_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"discord_webhook": None, "telegram_token": None, "telegram_chat": None}

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE,"w") as f: json.dump(cfg,f,indent=2)

def send_discord(msg,url):
    if not url: return {"status":"no webhook"}
    try:
        r=requests.post(url,json={"content":msg},timeout=5)
        return {"status":"ok","code":r.status_code}
    except Exception as e: return {"status":"error","error":str(e)}

def send_telegram(msg,token,chat):
    if not token or not chat: return {"status":"no token/chat"}
    try:
        url=f"https://api.telegram.org/bot{token}/sendMessage"
        r=requests.post(url,data={"chat_id":chat,"text":msg})
        return {"status":"ok","code":r.status_code}
    except Exception as e: return {"status":"error","error":str(e)}

def notify_all(message):
    cfg=load_config()
    return {
        "discord":  send_discord(message,cfg.get("discord_webhook")),
        "telegram": send_telegram(message,cfg.get("telegram_token"),cfg.get("telegram_chat"))
    }
PYCODE

# --- Patch static dashboard if not present ---
DASH="templates/index.html"
if ! grep -q "tab-notify" "$DASH" 2>/dev/null; then
  echo "🧩  Adding Notifications tab to dashboard"
  cat >> "$DASH" <<'HTMLCODE'
<!-- ==== Notifications Tab ==== -->
<button data-tab="tab-notify">Notifications</button>
<section id="tab-notify" class="tab">
  <div class="panel">
    <h3>🔔 Notification Settings</h3>
    <label>Discord Webhook: <input id="discord_url" class="winput"/></label><br>
    <label>Telegram Token: <input id="telegram_token" class="winput"/></label><br>
    <label>Telegram Chat ID: <input id="telegram_chat" class="winput"/></label><br>
    <button id="save_notify">Save</button>
    <button id="test_notify">Send Test Alert</button>
    <pre id="notify_status"></pre>
  </div>
</section>
HTMLCODE
fi

# --- Append JS logic if missing ---
JS="static/app.js"
if ! grep -q "function loadNotify" "$JS" 2>/dev/null; then
cat >> "$JS" <<'JSCODE'
async function loadNotify(){
  const c=await (await fetch('/api/notify/config')).json();
  discord_url.value=c.discord_webhook||'';
  telegram_token.value=c.telegram_token||'';
  telegram_chat.value=c.telegram_chat||'';
}
async function saveNotify(){
  const body={
    discord_webhook: discord_url.value,
    telegram_token: telegram_token.value,
    telegram_chat: telegram_chat.value
  };
  const r=await fetch('/api/notify/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  notify_status.textContent=JSON.stringify(await r.json(),null,2);
}
async function testNotify(){
  const msg=prompt("Enter test message","NeoLight test alert");
  const r=await fetch('/api/notify/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
  notify_status.textContent=JSON.stringify(await r.json(),null,2);
}
document.getElementById('save_notify').addEventListener('click',saveNotify);
document.getElementById('test_notify').addEventListener('click',testNotify);
loadNotify();
JSCODE
fi

# --- Restart FastAPI ---
echo "🚀 Restarting backend..."
pkill -f "uvicorn backend.main:app" || true
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload >> logs/backend.log 2>&1 &
sleep 2
echo "✅ Done.  Visit  http://localhost:8000/dashboard"


document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("modeToggle");
    const status = document.getElementById("modeStatus");
    const logs = document.getElementById("logs");

    // Load toggle status
    fetch('/api/live-toggle')
        .then(res => res.json())
        .then(data => {
            toggle.checked = data.live;
            status.innerText = data.live ? "LIVE Mode" : "SIM Mode";
        });

    // Listen for toggle changes
    toggle.addEventListener("change", () => {
        fetch('/api/live-toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ live: toggle.checked })
        }).then(() => {
            status.innerText = toggle.checked ? "LIVE Mode" : "SIM Mode";
        });
    });

    // Load strategy logs
    fetch('/api/strategy-log')
        .then(res => res.json())
        .then(data => {
            if (data.length === 0) {
                logs.innerText = "No strategy logs yet.";
            } else {
                logs.innerText = data.map(entry => JSON.stringify(entry)).join("\n");
            }
        })
        .catch(err => {
            logs.innerText = "Failed to load logs.";
        });
});

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

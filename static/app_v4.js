let priceChart;
const $ = (id)=>document.getElementById(id);
function renderLine(canvasId, labels, data, labelText){
  const ctx=$(canvasId).getContext('2d');
  return new Chart(ctx,{type:'line',data:{labels,datasets:[{label:labelText,data,borderColor:'#00ffff',tension:0.3}]},options:{plugins:{legend:{labels:{color:'#00ffff'}}},scales:{x:{ticks:{color:'#00ffff'}},y:{ticks:{color:'#00ffff'}}}}});
}
function initTabs(){
  const btns=document.querySelectorAll('.tabs button'); const tabs=document.querySelectorAll('.tab');
  btns.forEach(b=>b.addEventListener('click',()=>{btns.forEach(x=>x.classList.remove('active'));tabs.forEach(t=>t.classList.remove('active'));b.classList.add('active');document.getElementById(b.dataset.tab).classList.add('active');}));
}
async function jget(u,params){const q=params?('?'+new URLSearchParams(params)):"";const r=await fetch(u+q);return r.json();}
async function jpost(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});return r.json();}
async function refreshPrice(){
  const auto=await jget('/api/auto-mode'); $('qty').value=auto.qty||1; $('autoStatus').textContent=auto.auto_trade?'On':'Off';
  const d=await jget('/api/ohlc',{symbol:auto.symbol||'AAPL',limit:300}); const labels=d.map(x=>(x.t||'').toString().slice(11,16)); const closes=d.map(x=>x.close);
  if (priceChart){priceChart.data.labels=labels;priceChart.data.datasets[0].data=closes;priceChart.update();} else {priceChart=renderLine('priceChart',labels,closes,'Close');}
}
async function refreshLogs(){ const logs=await jget('/api/strategy-log'); $('logs').textContent=logs.length?logs.map(l=>JSON.stringify(l)).join('\n'):'No logs.'; }
async function refreshMetrics(){ const m=await jget('/api/metrics'); $('metrics').textContent=JSON.stringify(m,null,2); }
async function loadNotify(){ const c=await jget('/api/notify/config'); $('discord_url').value=c.discord_webhook||''; $('telegram_token').value=c.telegram_token||''; $('telegram_chat').value=c.telegram_chat||''; }
async function saveNotify(){ const body={discord_webhook:$('discord_url').value,telegram_token:$('telegram_token').value,telegram_chat:$('telegram_chat').value}; const r=await jpost('/api/notify/config',body); $('notify_status').textContent=JSON.stringify(r,null,2); }
async function testNotify(){ const msg=prompt("Enter test message","NeoLight test alert"); const r=await jpost('/api/notify/test',{message:msg}); $('notify_status').textContent=JSON.stringify(r,null,2); }
$('save_notify')?.addEventListener('click',saveNotify); $('test_notify')?.addEventListener('click',testNotify);
document.addEventListener('DOMContentLoaded',async()=>{initTabs();await Promise.all([refreshPrice(),refreshLogs(),refreshMetrics(),loadNotify()]);setInterval(refreshPrice,5000);setInterval(refreshLogs,7000);setInterval(refreshMetrics,7000);});

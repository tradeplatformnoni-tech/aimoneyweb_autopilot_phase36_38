const $  = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const fmt = n => (Math.abs(n)>=1? n.toFixed(2): n.toFixed(4));
async function jget(u){ const r=await fetch(u); return r.json(); }
async function jpost(u,b){ const r=await fetch(u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})}); return r.json(); }

// ---- lightweight-charts
const chart = LightweightCharts.createChart($('#candles'),{
  layout:{background:{type:'solid',color:'transparent'},textColor:'#b5eaff'},
  grid:{vertLines:{visible:false},horzLines:{visible:false}},
  rightPriceScale:{borderVisible:false}, timeScale:{borderVisible:false}
});
const series = chart.addCandlestickSeries({ upColor:'#00ff88', downColor:'#ff2d2d', borderUpColor:'#00ff88', borderDownColor:'#ff2d2d', wickUpColor:'#00ff88', wickDownColor:'#ff2d2d'});

const ws = new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws');
ws.onmessage = ev => {
  const d = JSON.parse(ev.data);
  series.update({ time:Math.floor(d.ts/1000), ...d.ohlc });
  $('#k_balance').textContent = `$${fmt(d.kpis.balance)}`;
  $('#k_profit').textContent = `${d.kpis.profit>=0?'+':''}${fmt(d.kpis.profit)}%`;
  $('#k_loss').textContent = `${fmt(d.kpis.loss)}%`;
};

// ---- performance
async function refreshPerf(){
  const p = await jget('/api/performance');
  $('#pnl').textContent = `$${fmt(p.pnl)}`;
  $('#win').textContent = `${(p.win_rate*100).toFixed(1)}%`;
  $('#sharpe').textContent = `${fmt(p.sharpe)}`;
}
setInterval(refreshPerf, 4000); refreshPerf();

// ---- trade
$('#tradeForm').addEventListener('submit', async e=>{
  e.preventDefault();
  const payload = { 
    symbol: $('#t_symbol').value.trim(),
    price: parseFloat($('#t_price').value),
    action: $('#t_action').value,
    qty: parseFloat($('#t_qty').value)
  };
  const res = await jpost('/api/paper_trade', payload);
  $('#tradeOut').textContent = JSON.stringify(res, null, 2);
  refreshPerf();
});

// ---- strategy: list + load defaults + load saved + save/apply
async function loadStrategyList(){
  const data = await jget('/api/strategies');
  const sel = $('#s_name'); sel.innerHTML='';
  (data.strategies||[]).forEach(n=>{
    const o = document.createElement('option'); o.value = o.textContent = n; sel.appendChild(o);
  });
}
async function loadSaved(){
  const cfg = await jget('/api/strategy_config');
  $('#s_name').value = cfg.name || 'momentum';
  $('#s_params').value = JSON.stringify(cfg.params || {}, null, 2);
  $('#stratOut').textContent = 'loaded saved config';
}
async function loadDefaults(){
  const name = $('#s_name').value;
  const d = await jget('/api/strategy_default?name='+encodeURIComponent(name));
  $('#s_params').value = JSON.stringify(d.params || {}, null, 2);
  $('#stratOut').textContent = 'loaded defaults for '+name;
}
async function saveApply(){
  let params={}; try{ params=JSON.parse($('#s_params').value||'{}'); }catch(e){ $('#stratOut').textContent='⚠️ JSON error: '+e.message; return; }
  const name = $('#s_name').value;
  const save = await jpost('/api/strategy_config', {name, params});
  const apply = await jpost('/api/strategy/apply', {});
  $('#stratOut').textContent = JSON.stringify({save, apply}, null, 2);
}
$('#btnLoadDefault').addEventListener('click', loadDefaults);
$('#btnSaveApply').addEventListener('click', saveApply);
$('#s_name').addEventListener('change', loadDefaults);

(async ()=>{ await loadStrategyList(); await loadSaved(); })();

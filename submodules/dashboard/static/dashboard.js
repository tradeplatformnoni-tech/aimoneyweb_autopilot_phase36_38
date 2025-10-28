async function getJSON(u){return (await fetch(u)).json();}
async function health(){
  const h=document.getElementById('health');
  try{const r=await getJSON('/api/health');h.textContent='✅ '+r.status;}
  catch(e){h.textContent='❌ Offline';}
}
async function chart(){
  const data=await getJSON('/api/ohlc');
  const ctx=document.getElementById('chart').getContext('2d');
  new Chart(ctx,{type:'line',data:{
    labels:data.map(d=>d.t.slice(11,16)),
    datasets:[{label:'Close',data:data.map(d=>d.close),borderColor:'#0ff'}]
  }});
}
health();chart();

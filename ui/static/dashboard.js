// dashboard.js - renders live positions & metrics
async function loadPortfolio() {
  const res = await fetch('/api/portfolio/data');
  const data = await res.json();
  const posDiv = document.getElementById('positions');
  posDiv.innerHTML = '<h4>Positions</h4>' + data.positions.map(
    p => `<div>${p.symbol}: ${parseFloat(p.market_value).toFixed(2)} (${p.qty})</div>`
  ).join('');
}
setInterval(loadPortfolio, 10000);

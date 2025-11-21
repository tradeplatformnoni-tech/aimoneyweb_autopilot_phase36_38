const COLOR_ORANGE = '#ff8b2a';
const COLOR_TEAL = '#00f6ff';
const COLOR_POS = '#44ffa5';
const COLOR_NEG = '#ff5178';
const GRID_COLOR = 'rgba(0,246,255,0.12)';
const PANEL_BG = 'rgba(9,18,42,0.85)';

let refreshInterval;
let galleryLoaded = false;
let parallaxFrame = null;
let audioInitialized = false;
let audioEnabled = false;

const baseLayout = () => ({
  plot_bgcolor: PANEL_BG,
  paper_bgcolor: 'rgba(5,8,17,0.95)',
  font: { color: '#f3f9ff', family: '"IBM Plex Mono", monospace' },
  xaxis: { gridcolor: GRID_COLOR, tickfont: { color: '#8ca7c6' } },
  yaxis: { gridcolor: GRID_COLOR, tickfont: { color: '#8ca7c6' } }
});

const mergeLayout = (extra = {}) => {
  const base = baseLayout();
  return {
    ...base,
    ...extra,
    xaxis: { ...base.xaxis, ...(extra.xaxis || {}) },
    yaxis: { ...base.yaxis, ...(extra.yaxis || {}) }
  };
};

const statusClass = (status) => {
  const normalized = (status || '').toString().toLowerCase();
  if (['running', 'active', 'approved', 'ok', 'filled', 'live'].includes(normalized)) {
    return 'neo-status-success';
  }
  if (['pending', 'open', 'watch', 'warming'].includes(normalized)) {
    return 'neo-status-warning';
  }
  return 'neo-status-danger';
};

const formatCurrency = (value) =>
  '$' + Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const formatPnL = (value) => `${value >= 0 ? '+' : ''}${Number(value || 0).toFixed(2)}`;

const plot = (elementId, traces, layoutExtra = {}) =>
  Plotly.newPlot(elementId, traces, mergeLayout(layoutExtra), { responsive: true, displayModeBar: false });

function showPanel(panelId, trigger) {
  document.querySelectorAll('.neo-panel').forEach((panel) => panel.classList.remove('active'));
  document.querySelectorAll('.neo-tab').forEach((tab) => tab.classList.remove('active'));
  const panel = document.getElementById(panelId);
  if (panel) panel.classList.add('active');

  if (trigger) {
    trigger.classList.add('active');
  } else {
    const tab = document.querySelector(`.neo-tab[data-target="${panelId}"]`);
    if (tab) tab.classList.add('active');
  }

  switch (panelId) {
    case 'overview':
      loadEquityChart();
      loadRiskChart();
      break;
    case 'transactions':
      loadTransactions();
      break;
    case 'approvals':
      loadApprovals();
      break;
    case 'agents':
      loadAgents();
      break;
    case 'revenue':
      loadRevenue();
      break;
    case 'analytics':
      loadAnalytics();
      break;
    case 'portfolio':
      loadPortfolioAnalytics();
      break;
    case 'aiCohort':
      loadAiCohort();
      break;
    case 'commodityHedges':
      loadCommodityHedges();
      break;
    case 'macroSignals':
      loadMacroSignals();
      break;
    case 'neoGallery':
      loadNeoGallery();
      break;
    case 'risk':
      loadRiskAttribution();
      break;
    case 'events':
      loadEvents();
      break;
    case 'sports':
      loadTodayBets();
      break;
    default:
      break;
  }
}

async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('equity').textContent = formatCurrency(data.equity || 0);
    document.getElementById('dailyPnl').textContent = Number(data.dailyPnl || 0).toFixed(2) + '%';
    document.getElementById('totalTrades').textContent = data.totalTrades || 0;
    document.getElementById('winRate').textContent = ((data.winRate || 0) * 100).toFixed(1) + '%';
    document.getElementById('pendingApprovals').textContent = data.pendingApprovals || 0;
    if (data.mode) {
      document.getElementById('dashboardMode').textContent = data.mode.replace(/_/g, ' ').toUpperCase();
    }
  } catch (error) {
    console.error('Error loading stats:', error);
  }
}

async function loadEquityChart() {
  try {
    const res = await fetch('/api/equity-curve');
    const data = await res.json();
    plot('equityChart', [
      {
        x: data.dates || [],
        y: data.equity || [],
        type: 'scatter',
        mode: 'lines',
        line: { color: COLOR_TEAL, width: 2 },
        name: 'Equity'
      }
    ], { title: 'Equity Curve' });
  } catch (error) {
    console.error('Error loading equity chart:', error);
  }
}

async function loadRiskChart() {
  try {
    const res = await fetch('/api/risk-metrics');
    const data = await res.json();
    plot('riskChart', [
      {
        x: data.dates || [],
        y: data.risk_scaler || [],
        type: 'scatter',
        mode: 'lines',
        name: 'Risk Scaler',
        line: { color: COLOR_POS }
      },
      {
        x: data.dates || [],
        y: data.confidence || [],
        type: 'scatter',
        mode: 'lines',
        name: 'Confidence',
        line: { color: COLOR_ORANGE }
      }
    ], { title: 'Risk & Confidence Metrics' });
  } catch (error) {
    console.error('Error loading risk chart:', error);
  }
}

async function loadTransactions() {
  try {
    const res = await fetch('/api/transactions');
    const data = await res.json();
    const tbody = document.getElementById('transactionsTable');
    tbody.innerHTML = (data.transactions || []).map((t) => `
      <tr>
        <td>${new Date(t.timestamp).toLocaleString()}</td>
        <td>${t.symbol}</td>
        <td>${t.side?.toUpperCase() || ''}</td>
        <td>${Number(t.qty || 0).toFixed(4)}</td>
        <td>${formatCurrency(t.price)}</td>
        <td style="color:${t.pnl >= 0 ? COLOR_POS : COLOR_NEG}">${formatPnL(t.pnl)}</td>
        <td><span class="neo-status-badge ${statusClass(t.status)}">${t.status}</span></td>
      </tr>
    `).join('');
  } catch (error) {
    console.error('Error loading transactions:', error);
  }
}

async function loadApprovals() {
  try {
    const res = await fetch('/api/approvals');
    const data = await res.json();
    const tbody = document.getElementById('approvalsTable');
    if (!data.pending || data.pending.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:40px; color:#8ca7c6;">No pending approvals</td></tr>';
    } else {
      tbody.innerHTML = data.pending.map((t) => `
        <tr>
          <td>${new Date(t.timestamp).toLocaleString()}</td>
          <td>${t.type}</td>
          <td>${t.details}</td>
          <td>${formatCurrency(t.amount)}</td>
          <td>
            <button class="neo-btn neo-btn-approve" onclick="approveTransaction(${t.id})">Approve</button>
            <button class="neo-btn neo-btn-reject" onclick="rejectTransaction(${t.id})">Reject</button>
          </td>
        </tr>
      `).join('');
    }
    document.getElementById('pendingApprovals').textContent = data.pending?.length || 0;
  } catch (error) {
    console.error('Error loading approvals:', error);
  }
}

async function approveTransaction(id) {
  try {
    const res = await fetch(`/api/approve/${id}`, { method: 'POST' });
    if (res.ok) {
      await loadApprovals();
      await loadStats();
    }
  } catch (error) {
    alert('Error approving transaction');
  }
}

async function rejectTransaction(id) {
  try {
    const res = await fetch(`/api/reject/${id}`, { method: 'POST' });
    if (res.ok) {
      await loadApprovals();
    }
  } catch (error) {
    alert('Error rejecting transaction');
  }
}

async function loadAgents() {
  try {
    const res = await fetch('/api/agents');
    const data = await res.json();
    const tbody = document.getElementById('agentsTable');
    tbody.innerHTML = (data.agents || []).map((a) => `
      <tr>
        <td>${a.name}</td>
        <td><span class="neo-status-badge ${statusClass(a.status)}">${a.status}</span></td>
        <td>${a.lastUpdate || 'N/A'}</td>
        <td>${a.performance || 'N/A'}</td>
      </tr>
    `).join('');
  } catch (error) {
    console.error('Error loading agents:', error);
  }
}

async function loadRevenue() {
  try {
    const res = await fetch('/api/revenue');
    const data = await res.json();
    const tbody = document.getElementById('revenueTable');
    tbody.innerHTML = (data.agents || []).map((a) => `
      <tr>
        <td>${a.name}</td>
        <td>${formatCurrency(a.revenue)}</td>
        <td>${formatCurrency(a.cost)}</td>
        <td style="color:${a.netPnl >= 0 ? COLOR_POS : COLOR_NEG}">${formatPnL(a.netPnl)}</td>
        <td style="color:${a.roi >= 0 ? COLOR_POS : COLOR_NEG}">${Number(a.roi || 0).toFixed(1)}%</td>
        <td><span class="neo-status-badge ${statusClass(a.status)}">${a.status}</span></td>
      </tr>
    `).join('');

    if (data.agents && data.agents.length > 0) {
      plot('revenueChart', [
        {
          x: data.agents.map((a) => a.name),
          y: data.agents.map((a) => a.revenue),
          type: 'bar',
          marker: { color: COLOR_ORANGE }
        }
      ], { title: 'Revenue by Agent', yaxis: { title: 'USD' } });
    }
  } catch (error) {
    console.error('Error loading revenue:', error);
  }
}

async function loadAnalytics() {
  try {
    const res = await fetch('/api/analytics');
    const data = await res.json();

    if (data.sentiment && data.sentiment.length > 0) {
      plot('sentimentChart', [
        {
          x: data.sentiment.map((s) => s.symbol),
          y: data.sentiment.map((s) => s.score),
          type: 'bar',
          marker: { color: data.sentiment.map((s) => s.score > 0 ? COLOR_POS : COLOR_NEG) }
        }
      ], { title: 'Market Sentiment' });
    }

    if (data.strategies && data.strategies.length > 0) {
      plot('strategyChart', [
        {
          x: data.strategies.map((s) => s.name),
          y: data.strategies.map((s) => s.score),
          type: 'bar',
          marker: { color: COLOR_TEAL }
        }
      ], { title: 'Strategy Performance Scores' });
    }
  } catch (error) {
    console.error('Error loading analytics:', error);
  }
}

async function loadPortfolioAnalytics() {
  try {
    const res = await fetch('/api/portfolio-analytics');
    const data = await res.json();

    if (data.attribution && data.attribution.length > 0) {
      plot('attributionChart', [
        {
          x: data.attribution.map((a) => a.strategy),
          y: data.attribution.map((a) => a.contribution),
          type: 'bar',
          marker: { color: data.attribution.map((a) => a.contribution > 0 ? COLOR_POS : COLOR_NEG) }
        }
      ], { title: 'Performance Attribution' });
    }

    if (data.factor_exposure && Object.keys(data.factor_exposure).length > 0) {
      const factors = Object.keys(data.factor_exposure);
      const values = Object.values(data.factor_exposure);
      plot('factorExposureChart', [
        {
          x: factors,
          y: values,
          type: 'bar',
          marker: { color: COLOR_TEAL }
        }
      ], { title: 'Factor Exposure' });
    }

    const tbody = document.getElementById('portfolioTable');
    if (data.strategies && data.strategies.length > 0) {
      tbody.innerHTML = data.strategies.map((s) => `
        <tr>
          <td>${s.name}</td>
          <td>${(s.allocation * 100).toFixed(1)}%</td>
          <td style="color:${s.contribution > 0 ? COLOR_POS : COLOR_NEG}">${s.contribution.toFixed(2)}%</td>
          <td>${Number(s.sharpe || 0).toFixed(2)}</td>
          <td>${s.trade_count || 0}</td>
        </tr>
      `).join('');
    } else {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:40px; color:#8ca7c6;">No portfolio data available</td></tr>';
    }
  } catch (error) {
    console.error('Error loading portfolio analytics:', error);
  }
}

async function loadAiCohort() {
  try {
    const res = await fetch('/api/panels/ai-cohort');
    const data = await res.json();
    const totalWeight = (data.total_weight || 0) * 100;
    document.getElementById('aiCohortWeight').textContent = totalWeight.toFixed(1) + '%';

    const members = data.members || [];
    document.getElementById('aiCohortTop').textContent = members[0]?.symbol || '—';

    const tbody = document.getElementById('aiCohortTable');
    if (members.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:40px; color:#8ca7c6;">No AI cohort data available</td></tr>';
      return;
    }

    tbody.innerHTML = members.map((m) => `
      <tr>
        <td>${m.symbol}</td>
        <td>${Number(m.weight_pct ?? (m.weight || 0) * 100).toFixed(2)}%</td>
        <td>${m.price != null ? formatCurrency(m.price) : '—'}</td>
        <td>${(m.source || 'alpaca').toUpperCase()}</td>
      </tr>
    `).join('');
  } catch (error) {
    console.error('Error loading AI cohort panel:', error);
  }
}

async function loadCommodityHedges() {
  try {
    const res = await fetch('/api/panels/commodity-hedges');
    const data = await res.json();
    const totalWeight = (data.total_weight || 0) * 100;
    document.getElementById('commodityWeight').textContent = totalWeight.toFixed(1) + '%';

    const members = data.members || [];
    document.getElementById('commodityTop').textContent = members[0]?.symbol || '—';

    const tbody = document.getElementById('commodityTable');
    if (members.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:40px; color:#8ca7c6;">No commodity hedge data available</td></tr>';
      return;
    }

    tbody.innerHTML = members.map((m) => `
      <tr>
        <td>${m.symbol}</td>
        <td>${Number(m.weight_pct ?? (m.weight || 0) * 100).toFixed(2)}%</td>
        <td>${m.price != null ? formatCurrency(m.price) : '—'}</td>
        <td>${(m.source || 'alpaca').toUpperCase()}</td>
      </tr>
    `).join('');
  } catch (error) {
    console.error('Error loading commodity hedge panel:', error);
  }
}

async function loadMacroSignals() {
  try {
    const res = await fetch('/api/panels/macro-signals');
    const data = await res.json();
    const spread = data.yield_spread;
    document.getElementById('macroYieldSpread').textContent = spread != null ? spread.toFixed(2) + ' bp' : '--';

    const signals = data.signals || [];
    const tbody = document.getElementById('macroSignalsTable');
    if (signals.length === 0) {
      tbody.innerHTML = '<tr><td colspan="2" style="text-align:center; padding:40px; color:#8ca7c6;">No macro signals available</td></tr>';
      return;
    }

    tbody.innerHTML = signals.map((s) => `
      <tr>
        <td>${s.label || s.symbol}</td>
        <td>${s.value != null ? Number(s.value).toFixed(2) : '—'}</td>
      </tr>
    `).join('');
  } catch (error) {
    console.error('Error loading macro signals panel:', error);
  }
}

async function loadNeoGallery() {
  try {
    if (galleryLoaded) {
      return;
    }
    const res = await fetch('/static/data/gallery.json');
    const items = await res.json();
    const grid = document.getElementById('neoGalleryGrid');
    grid.innerHTML = items.map((item) => `
      <article class="neo-gallery-card">
        <img src="/static/images/${item.filename}" alt="${item.title}">
        <div class="neo-gallery-caption">
          <strong>${item.title}</strong><br>
          <span>${item.subtitle || ''}</span>
        </div>
      </article>
    `).join('');
    galleryLoaded = true;
  } catch (error) {
    console.error('Error loading gallery assets:', error);
  }
}

async function loadRiskAttribution() {
  try {
    const res = await fetch('/api/risk-attribution');
    const data = await res.json();
    document.getElementById('diversificationScore').textContent =
      ((data.diversification_score || 0).toFixed(1)) + '/100';

    if (data.risk_contributions && Object.keys(data.risk_contributions).length > 0) {
      const strategies = Object.keys(data.risk_contributions);
      const contributions = Object.values(data.risk_contributions);
      plot('riskContributionChart', [
        {
          x: strategies,
          y: contributions,
          type: 'bar',
          marker: { color: contributions.map((c) => (c > 40 ? COLOR_NEG : c > 20 ? COLOR_ORANGE : COLOR_POS)) }
        }
      ], { title: 'Risk Contribution by Strategy (%)' });
    }

    const tbody = document.getElementById('riskTable');
    if (data.strategies && data.strategies.length > 0) {
      tbody.innerHTML = data.strategies.map((s) => `
        <tr>
          <td>${s.strategy}</td>
          <td>${s.allocation_pct.toFixed(1)}%</td>
          <td>${s.risk_contribution_pct.toFixed(1)}%</td>
          <td>${s.volatility_pct.toFixed(1)}%</td>
          <td><span class="neo-status-badge ${s.alert ? 'neo-status-warning' : 'neo-status-success'}">${s.alert ? 'HIGH' : 'OK'}</span></td>
        </tr>
      `).join('');
    } else {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:40px; color:#8ca7c6;">No risk data available</td></tr>';
    }
  } catch (error) {
    console.error('Error loading risk attribution:', error);
  }
}

async function loadEvents() {
  try {
    const filter = document.getElementById('eventFilter')?.value || '';
    const res = await fetch(filter ? `/api/events?type=${filter}` : '/api/events');
    const data = await res.json();
    const tbody = document.getElementById('eventsTable');
    const events = (data.events || []).slice(-50).reverse();

    if (events.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:40px; color:#8ca7c6;">No events available</td></tr>';
      return;
    }

    tbody.innerHTML = events.map((event) => {
      const badgeClass = event.type === 'BUY' || event.type === 'SIGNAL_BUY'
        ? 'neo-status-success'
        : event.type === 'SELL' || event.type === 'SIGNAL_SELL'
          ? 'neo-status-danger'
          : 'neo-status-warning';
      return `
        <tr>
          <td>${new Date(event.timestamp).toLocaleString()}</td>
          <td><span class="neo-status-badge ${badgeClass}">${event.type}</span></td>
          <td>${event.source || 'unknown'}</td>
          <td style="font-size:12px; color:#8ca7c6;">${JSON.stringify(event.data).substring(0, 100)}...</td>
        </tr>
      `;
    }).join('');
  } catch (error) {
    console.error('Error loading events:', error);
  }
}

const updateLastRefresh = () => {
  document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
};

function startAutoRefresh() {
  loadStats();
  updateLastRefresh();
  refreshInterval = setInterval(() => {
    loadStats();
    const activePanel = document.querySelector('.neo-panel.active');
    const panelId = activePanel?.id;
    if (panelId) {
      showPanel(panelId);
    }
    updateLastRefresh();
  }, 5000);
}

window.showPanel = showPanel;
window.loadEvents = loadEvents;
window.loadTodayBets = loadTodayBets;
window.loadSportsResults = loadSportsResults;
window.approveTransaction = approveTransaction;
window.rejectTransaction = rejectTransaction;

function bindParallax() {
  const root = document.body;
  if (!root) return;
  const update = (x, y) => {
    root.style.setProperty('--parallax-x', `${x}px`);
    root.style.setProperty('--parallax-y', `${y}px`);
    parallaxFrame = null;
  };
  const handlePointer = (event) => {
    const x = (event.clientX / window.innerWidth - 0.5) * 20;
    const y = (event.clientY / window.innerHeight - 0.5) * 20;
    if (parallaxFrame) cancelAnimationFrame(parallaxFrame);
    parallaxFrame = requestAnimationFrame(() => update(x, y));
  };
  window.addEventListener('pointermove', handlePointer);
}

async function initAmbientAudio() {
  if (audioInitialized) return;
  audioInitialized = true;
  const audioEl = document.getElementById('ambientAudio');
  const controls = document.getElementById('audioControls');
  const toggleBtn = document.getElementById('audioToggle');
  const statusEl = document.getElementById('audioStatus');
  if (!audioEl || !controls || !toggleBtn || !statusEl) return;

  try {
    const src = audioEl.getAttribute('src');
    if (!src) return;
    const response = await fetch(src, { method: 'HEAD' });
    if (!response.ok) return;
    controls.style.display = 'inline-flex';
    audioEl.volume = 0.4;
    toggleBtn.addEventListener('click', async () => {
      if (!audioEnabled) {
        try {
          await audioEl.play();
          audioEnabled = true;
          toggleBtn.textContent = 'Mute Ambient';
          statusEl.textContent = 'Playing';
        } catch (error) {
          console.warn('Ambient audio playback blocked by browser interaction', error);
        }
      } else {
        audioEl.pause();
        audioEl.currentTime = 0;
        audioEnabled = false;
        toggleBtn.textContent = 'Enable Ambient';
        statusEl.textContent = 'Muted';
      }
    });
    audioEl.addEventListener('ended', () => {
      audioEnabled = false;
      toggleBtn.textContent = 'Enable Ambient';
      statusEl.textContent = 'Muted';
    });
  } catch (error) {
    console.warn('Ambient audio unavailable', error);
  }
}

async function loadTodayBets() {
  try {
    const res = await fetch('/api/sports/today');
    const data = await res.json();
    
    // Update stats
    document.getElementById('sportsDate').textContent = data.date || new Date().toLocaleDateString();
    document.getElementById('sportsTotalOpps').textContent = data.total_opportunities || 0;
    document.getElementById('sportsTotalEV').textContent = formatCurrency(data.total_expected_value || 0);
    document.getElementById('sportsTotalStake').textContent = formatCurrency(data.total_stake || 0);
    
    // Update table
    const tbody = document.getElementById('sportsBetsTable');
    const recommendations = data.recommendations || [];
    
    if (recommendations.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px; color:#8ca7c6;">No betting opportunities for today. Check back later or refresh predictions.</td></tr>';
    } else {
      tbody.innerHTML = recommendations.map((bet) => {
        const confidenceClass = bet.confidence > 0.7 ? 'neo-status-success' : bet.confidence > 0.6 ? 'neo-status-warning' : 'neo-status-danger';
        const edgeClass = bet.edge > 0 ? COLOR_POS : COLOR_NEG;
        const game = `${bet.away_team || ''} @ ${bet.home_team || ''}`;
        
        return `
          <tr>
            <td><strong>${(bet.sport || 'unknown').toUpperCase()}</strong></td>
            <td>${game}</td>
            <td><strong style="color:${COLOR_TEAL}">${bet.recommended_side || 'N/A'}</strong></td>
            <td><span class="neo-status-badge ${confidenceClass}">${(bet.confidence * 100).toFixed(0)}%</span></td>
            <td style="color:${edgeClass}">${(bet.edge * 100).toFixed(2)}%</td>
            <td>${formatCurrency(bet.recommended_stake || 0)}</td>
            <td style="color:${COLOR_POS}">${formatCurrency(bet.expected_value || 0)}</td>
            <td>${bet.scheduled || 'N/A'}</td>
          </tr>
        `;
      }).join('');
    }
    
    // Load results and performance
    await loadSportsResults();
  } catch (error) {
    console.error('Error loading today\'s bets:', error);
    const tbody = document.getElementById('sportsBetsTable');
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px; color:#ff5178;">Error loading today\'s bets. Please try again.</td></tr>';
  }
}

async function loadSportsResults() {
  try {
    const res = await fetch('/api/sports/results');
    const data = await res.json();
    
    // Update performance stats
    const perf = data.performance || {};
    document.getElementById('sportsWinRate').textContent = (perf.win_rate || 0).toFixed(1) + '%';
    document.getElementById('sportsTotalPnL').textContent = formatCurrency(perf.total_pnl || 0);
    document.getElementById('sportsTotalTrades').textContent = perf.total_trades || 0;
    document.getElementById('sportsWinsLosses').textContent = `${perf.wins || 0} / ${perf.losses || 0}`;
    
    // Update results table
    const tbody = document.getElementById('sportsResultsTable');
    const trades = data.recent_trades || [];
    
    if (trades.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:40px; color:#8ca7c6;">No settled bets yet. Results will appear here after games complete.</td></tr>';
    } else {
      tbody.innerHTML = trades.map((trade) => {
        const result = trade.result || 'pending';
        const resultClass = result === 'win' ? 'neo-status-success' : result === 'loss' ? 'neo-status-danger' : 'neo-status-warning';
        const pnl = trade.pnl || 0;
        const pnlClass = pnl >= 0 ? COLOR_POS : COLOR_NEG;
        const stake = trade.stake || 0;
        const roi = stake > 0 ? (pnl / stake * 100) : 0;
        const game = `${trade.away_team || ''} @ ${trade.home_team || ''}`;
        const date = trade.settled_at ? new Date(trade.settled_at).toLocaleDateString() : 'N/A';
        
        return `
          <tr>
            <td>${date}</td>
            <td><strong>${(trade.sport || 'unknown').toUpperCase()}</strong></td>
            <td>${game}</td>
            <td><strong>${trade.recommended_side || 'N/A'}</strong></td>
            <td>${formatCurrency(stake)}</td>
            <td><span class="neo-status-badge ${resultClass}">${result.toUpperCase()}</span></td>
            <td style="color:${pnlClass}">${formatPnL(pnl)}</td>
            <td style="color:${pnlClass}">${roi.toFixed(2)}%</td>
          </tr>
        `;
      }).join('');
    }
  } catch (error) {
    console.error('Error loading sports results:', error);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const defaultTab = document.querySelector('.neo-tab[data-target="overview"]');
  showPanel('overview', defaultTab);
  bindParallax();
  initAmbientAudio();
  startAutoRefresh();
});


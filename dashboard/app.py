#!/usr/bin/env python3
"""
NeoLight Unified Dashboard - Complete Transaction & Monitoring System
Shows all trades, revenue, agent activity, and allows approve/disapprove
"""

import csv
import json
import logging
import os
from datetime import datetime, timezone

UTC = timezone.utc  # Python 3.9+ compatibility
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
LOGS = ROOT / "logs"

app = FastAPI(title="NeoLight Unified Dashboard", version="3.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

try:
    from .sports_api import router as sports_router
except ImportError:
    from dashboard.sports_api import router as sports_router

app.include_router(sports_router)

# Observability endpoints
try:
    from dashboard.observability import (
        get_agent_status,
        get_anomaly_detections,
        get_failure_predictions,
        get_metrics,
        get_observability_summary,
        get_traces,
    )
    HAS_OBSERVABILITY = True
except ImportError:
    HAS_OBSERVABILITY = False

# Shared market universe context
try:
    from analytics.realtime_market_data import YAHOO_ONLY_SYMBOLS as ANALYTICS_YAHOO_SYMBOLS
except Exception:
    ANALYTICS_YAHOO_SYMBOLS = []

YAHOO_SYMBOLS_SET = set(ANALYTICS_YAHOO_SYMBOLS)
MACRO_SIGNAL_SYMBOLS = ["^VIX", "^TYX", "^FVX", "MOVE.P"]
MACRO_SIGNAL_LABELS = {
    "^VIX": "VIX Volatility",
    "^TYX": "30Y Treasury Yield",
    "^FVX": "5Y Treasury Yield",
    "MOVE.P": "MOVE Bond Volatility",
}
dashboard_logger = logging.getLogger("dashboard.panels")

# In-memory cache for meta-metrics (Phase 5600)
_meta_metrics_cache = {}
_meta_metrics_timestamp = None

# Transaction approval queue
APPROVAL_QUEUE_FILE = STATE / "approval_queue.json"
APPROVED_FILE = STATE / "approved_transactions.json"


def load_approval_queue() -> list[dict[str, Any]]:
    """Load pending transactions requiring approval."""
    if APPROVAL_QUEUE_FILE.exists():
        try:
            return json.loads(APPROVAL_QUEUE_FILE.read_text())
        except:
            pass
    return []


def save_approval_queue(queue: list[dict[str, Any]]) -> None:
    """Save approval queue."""
    APPROVAL_QUEUE_FILE.write_text(json.dumps(queue, indent=2))


def load_approved() -> list[dict[str, Any]]:
    """Load approved transactions."""
    if APPROVED_FILE.exists():
        try:
            return json.loads(APPROVED_FILE.read_text())
        except:
            pass
    return []


def add_to_approval_queue(transaction: dict[str, Any]) -> None:
    """Add transaction to approval queue."""
    queue = load_approval_queue()
    transaction["id"] = len(queue) + 1
    transaction["status"] = "pending"
    transaction["timestamp"] = datetime.now().isoformat()
    queue.append(transaction)
    save_approval_queue(queue)


def _load_allocation_groups() -> dict[str, dict[str, Any]]:
    """Load allocations and groups from runtime override."""
    allocations = {}
    groups = {}
    try:
        alloc_file = RUNTIME / "allocations_override.json"
        if alloc_file.exists():
            data = json.loads(alloc_file.read_text())
            allocations = data.get("allocations", {}) or {}
            groups = data.get("groups", {}) or {}
    except Exception as exc:
        dashboard_logger.debug("Allocation override load failed: %s", exc)
    return {"allocations": allocations, "groups": groups}


def _fetch_panel_prices(symbols: list[str]) -> dict[str, float | None]:
    """Fetch latest prices for requested symbols via yfinance."""
    prices: dict[str, float | None] = dict.fromkeys(symbols)
    if not symbols:
        return prices
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        dashboard_logger.warning("yfinance not installed; panel prices unavailable")
        return prices

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1h")
            if not hist.empty:
                prices[symbol] = float(hist["Close"].iloc[-1])
            else:
                info = ticker.info
                latest = info.get("currentPrice") or info.get("regularMarketPrice")
                if latest is not None:
                    prices[symbol] = float(latest)
        except Exception as exc:  # noqa: BLE001
            dashboard_logger.debug("Price fetch failed for %s: %s", symbol, exc)
    return prices


def _build_group_panel(
    group_name: str, symbols: list[str], allocations: dict[str, float]
) -> dict[str, Any]:
    """Assemble panel payload for a symbol group."""
    weights = []
    total_weight = 0.0
    for sym in symbols:
        weight = float(allocations.get(sym, 0.0))
        if weight <= 0:
            continue
        weights.append((sym, weight))
        total_weight += weight

    weights.sort(key=lambda item: item[1], reverse=True)
    price_map = _fetch_panel_prices([sym for sym, _ in weights])

    members = [
        {
            "symbol": sym,
            "weight": weight,
            "weight_pct": weight * 100.0,
            "price": price_map.get(sym),
            "source": "yahoo" if sym in YAHOO_SYMBOLS_SET else "alpaca",
        }
        for sym, weight in weights
    ]

    return {
        "group": group_name,
        "total_weight": total_weight,
        "members": members,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _build_macro_signals_payload() -> dict[str, Any]:
    """Fetch macro indicators for dashboard panel."""
    prices = _fetch_panel_prices(MACRO_SIGNAL_SYMBOLS)
    signals = []
    for symbol in MACRO_SIGNAL_SYMBOLS:
        signals.append(
            {
                "symbol": symbol,
                "label": MACRO_SIGNAL_LABELS.get(symbol, symbol),
                "value": prices.get(symbol),
            }
        )

    tyx = prices.get("^TYX")
    fvx = prices.get("^FVX")
    yield_spread = None
    if tyx is not None and fvx is not None:
        yield_spread = (tyx - fvx) * 100.0

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "signals": signals,
        "yield_spread": yield_spread,
    }


@app.get("/healthz")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/", response_class=HTMLResponse)
def dashboard_home():
    """Main dashboard HTML."""
    template_path = Path(__file__).resolve().parent / "templates" / "dashboard.html"
    if template_path.exists():
        return HTMLResponse(template_path.read_text(encoding="utf-8"))
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeoLight Command Mesh</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Montserrat:wght@400;600&display=swap">
    <link rel="stylesheet" href="/static/css/theme-neon.css">
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>
        .neo-chart { width: 100%; height: 420px; }
        .neo-table-wrapper { overflow-x: auto; }
    </style>
</head>
<body class="neo-body neo-grid-overlay">
    <div class="neo-dashboard">
        <header class="neo-header">
            <div>
                <span class="neo-hud-tag">NeoLight Command Mesh</span>
                <h1 style="font-family: var(--font-alt); font-size: 26px; letter-spacing: 0.12em;">Wealth & Sports Intelligence</h1>
    </div>
            <div class="neo-chip">
                <span>Mode</span>
                <strong id="dashboardMode">Paper</strong>
            </div>
        </header>

        <section class="neo-stat-grid" id="stats">
            <div class="neo-stat-card">
                <span class="neo-stat-label">Current Equity</span>
                <span class="neo-stat-value" id="equity">$0</span>
        </div>
            <div class="neo-stat-card">
                <span class="neo-stat-label">Daily P&L</span>
                <span class="neo-stat-value" id="dailyPnl">0%</span>
        </div>
            <div class="neo-stat-card">
                <span class="neo-stat-label">Total Trades</span>
                <span class="neo-stat-value" id="totalTrades">0</span>
        </div>
            <div class="neo-stat-card">
                <span class="neo-stat-label">Win Rate</span>
                <span class="neo-stat-value" id="winRate">0%</span>
        </div>
            <div class="neo-stat-card">
                <span class="neo-stat-label">Pending Approvals</span>
                <span class="neo-stat-value" id="pendingApprovals">0</span>
        </div>
        </section>
    
        <nav class="neo-tabs" role="tablist">
            <button class="neo-tab active" onclick="showPanel('overview', this)">Overview</button>
            <button class="neo-tab" onclick="showPanel('transactions', this)">Transactions</button>
            <button class="neo-tab" onclick="showPanel('approvals', this)">Approvals</button>
            <button class="neo-tab" onclick="showPanel('agents', this)">Agents</button>
            <button class="neo-tab" onclick="showPanel('revenue', this)">Revenue</button>
            <button class="neo-tab" onclick="showPanel('analytics', this)">Analytics</button>
            <button class="neo-tab" onclick="showPanel('portfolio', this)">Portfolio</button>
            <button class="neo-tab" onclick="showPanel('aiCohort', this)">AI Cohort</button>
            <button class="neo-tab" onclick="showPanel('commodityHedges', this)">Commodity</button>
            <button class="neo-tab" onclick="showPanel('macroSignals', this)">Macro</button>
            <button class="neo-tab" onclick="showPanel('neoGallery', this)">Neo Gallery</button>
            <button class="neo-tab" onclick="showPanel('risk', this)">Risk</button>
            <button class="neo-tab" onclick="showPanel('events', this)">Events</button>
        </nav>
    
        <section id="overview" class="neo-panel active">
            <div class="neo-hud-tag">System Telemetry</div>
            <div class="neo-chart" id="equityChart"></div>
            <hr class="neo-glow-divider"/>
            <div class="neo-hud-tag">Risk Vector</div>
            <div class="neo-chart" id="riskChart"></div>
        </section>
    
        <section id="transactions" class="neo-panel">
            <div class="neo-hud-tag">Order Flow</div>
            <div class="neo-table-wrapper">
                <table class="neo-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Quantity</th>
                    <th>Price</th>
                            <th>PnL</th>
                    <th>Status</th>
                </tr>
            </thead>
                    <tbody id="transactionsTable"></tbody>
        </table>
    </div>
        </section>

        <section id="approvals" class="neo-panel">
            <div class="neo-hud-tag">Pending Approvals</div>
            <p class="neo-stat-label" style="margin-bottom: 18px;">Review and action required transactions</p>
            <div class="neo-table-wrapper">
                <table class="neo-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Details</th>
                    <th>Amount</th>
                    <th>Action</th>
                </tr>
            </thead>
                    <tbody id="approvalsTable"></tbody>
        </table>
    </div>
        </section>

        <section id="agents" class="neo-panel">
            <div class="neo-hud-tag">Agent Status</div>
            <div class="neo-table-wrapper">
                <table class="neo-table">
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>Status</th>
                    <th>Last Update</th>
                    <th>Performance</th>
                </tr>
            </thead>
                    <tbody id="agentsTable"></tbody>
        </table>
    </div>
        </section>

        <section id="revenue" class="neo-panel">
            <div class="neo-hud-tag">Revenue by Agent</div>
            <div class="neo-chart" id="revenueChart"></div>
            <hr class="neo-glow-divider"/>
            <div class="neo-table-wrapper">
                <table class="neo-table">
            <thead>
                <tr>
                    <th>Agent</th>
                    <th>Total Revenue</th>
                    <th>Total Cost</th>
                    <th>Net P&L</th>
                    <th>ROI %</th>
                    <th>Status</th>
                </tr>
            </thead>
                    <tbody id="revenueTable"></tbody>
        </table>
    </div>
        </section>

        <section id="analytics" class="neo-panel">
            <div class="neo-hud-tag">Analytics & Intelligence</div>
            <div class="neo-chart" id="sentimentChart"></div>
            <hr class="neo-glow-divider"/>
            <div class="neo-chart" id="strategyChart"></div>
        </section>
    
        <section id="portfolio" class="neo-panel">
            <div class="neo-hud-tag">Portfolio Analytics</div>
            <div class="neo-chart" id="attributionChart"></div>
            <hr class="neo-glow-divider"/>
            <div class="neo-chart" id="factorExposureChart"></div>
            <div class="neo-table-wrapper" style="margin-top: 24px;">
                <table class="neo-table">
            <thead>
                <tr>
                    <th>Strategy</th>
                    <th>Allocation %</th>
                            <th>Contribution %</th>
                            <th>Sharpe</th>
                            <th>Trades</th>
                </tr>
            </thead>
                    <tbody id="portfolioTable"></tbody>
        </table>
    </div>
        </section>

        <section id="aiCohort" class="neo-panel">
            <div class="neo-hud-tag">AI Rotation Cohort</div>
            <div class="neo-stat-grid" style="margin-bottom: 24px;">
                <div class="neo-stat-card">
                    <span class="neo-stat-label">Total Allocation</span>
                    <span class="neo-stat-value" id="aiCohortWeight">0%</span>
        </div>
                <div class="neo-stat-card">
                    <span class="neo-stat-label">Top Weighted Symbol</span>
                    <span class="neo-stat-value" id="aiCohortTop">—</span>
                </div>
            </div>
            <div class="neo-table-wrapper">
                <table class="neo-table">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Weight %</th>
                            <th>Last Price</th>
                            <th>Source</th>
                        </tr>
                    </thead>
                    <tbody id="aiCohortTable"></tbody>
                </table>
            </div>
        </section>

        <section id="commodityHedges" class="neo-panel">
            <div class="neo-hud-tag">Commodity Hedges</div>
            <div class="neo-stat-grid" style="margin-bottom: 24px;">
                <div class="neo-stat-card">
                    <span class="neo-stat-label">Total Allocation</span>
                    <span class="neo-stat-value" id="commodityWeight">0%</span>
                </div>
                <div class="neo-stat-card">
                    <span class="neo-stat-label">Top Hedge</span>
                    <span class="neo-stat-value" id="commodityTop">—</span>
                </div>
            </div>
            <div class="neo-table-wrapper">
                <table class="neo-table">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Weight %</th>
                            <th>Last Price</th>
                            <th>Source</th>
                        </tr>
                    </thead>
                    <tbody id="commodityTable"></tbody>
                </table>
            </div>
        </section>

        <section id="macroSignals" class="neo-panel">
            <div class="neo-hud-tag">Macro Signals</div>
            <div class="neo-stat-grid" style="margin-bottom: 24px;">
                <div class="neo-stat-card">
                    <span class="neo-stat-label">30Y-5Y Yield Spread (bp)</span>
                    <span class="neo-stat-value" id="macroYieldSpread">--</span>
                </div>
            </div>
            <div class="neo-table-wrapper">
                <table class="neo-table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody id="macroSignalsTable"></tbody>
                </table>
            </div>
        </section>

        <section id="neoGallery" class="neo-panel">
            <div class="neo-hud-tag">Neo Gallery</div>
            <p class="neo-stat-label" style="margin-bottom: 18px;">Curated ambient imagery for the command center aesthetic.</p>
            <div class="neo-gallery" id="neoGalleryGrid"></div>
        </section>

        <section id="risk" class="neo-panel">
            <div class="neo-hud-tag">Risk Attribution</div>
            <div class="neo-stat-card" style="margin-bottom: 24px;">
                <span class="neo-stat-label">Diversification Score</span>
                <span class="neo-stat-value" id="diversificationScore">0/100</span>
            </div>
            <div class="neo-chart" id="riskContributionChart"></div>
            <div class="neo-table-wrapper" style="margin-top: 24px;">
                <table class="neo-table">
            <thead>
                <tr>
                    <th>Strategy</th>
                    <th>Allocation %</th>
                    <th>Risk Contribution %</th>
                    <th>Volatility %</th>
                    <th>Alert</th>
                </tr>
            </thead>
                    <tbody id="riskTable"></tbody>
        </table>
    </div>
        </section>

        <section id="events" class="neo-panel">
            <div class="neo-hud-tag">Event Stream</div>
            <div style="margin-bottom: 20px; display:flex; gap:12px; align-items:center;">
                <button class="neo-btn neo-btn-primary" onclick="loadEvents()">Refresh Events</button>
                <select id="eventFilter" class="neo-select" onchange="loadEvents()">
                <option value="">All Events</option>
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
                <option value="SIGNAL_BUY">SIGNAL_BUY</option>
                <option value="SIGNAL_SELL">SIGNAL_SELL</option>
                <option value="REGIME_CHANGE">REGIME_CHANGE</option>
            </select>
        </div>
            <div class="neo-table-wrapper">
                <table class="neo-table">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Type</th>
                    <th>Source</th>
                    <th>Details</th>
                </tr>
            </thead>
                    <tbody id="eventsTable"></tbody>
        </table>
    </div>
        </section>
    
        <div class="auto-refresh neo-chip">
            <span>Auto Refresh</span>
            <strong id="refreshStatus">ON</strong>
            <span>Last Ping</span>
            <strong id="lastUpdate">–</strong>
        </div>
    </div>
    
        }
        
        async function loadAiCohort() {
            try {
                const res = await fetch('/api/panels/ai-cohort');
                const data = await res.json();
                const totalWeight = (data.total_weight || 0) * 100;
                document.getElementById('aiCohortWeight').textContent = totalWeight.toFixed(1) + '%';
                
                const members = data.members || [];
                const topMember = members.length > 0 ? members[0] : null;
                document.getElementById('aiCohortTop').textContent = topMember ? topMember.symbol : '—';
                
                const tbody = document.getElementById('aiCohortTable');
                if (members.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 40px; color: #94a3b8;">No AI cohort data available</td></tr>';
                } else {
                    tbody.innerHTML = members.map(m => `
                        <tr>
                            <td>${m.symbol}</td>
                            <td>${(m.weight_pct ?? (m.weight || 0) * 100).toFixed(2)}%</td>
                            <td>${m.price != null ? '$' + m.price.toFixed(2) : '—'}</td>
                            <td>${(m.source || 'alpaca').toUpperCase()}</td>
                        </tr>
                    `).join('');
                }
            } catch (e) {
                console.error('Error loading AI cohort panel:', e);
            }
        }
        
        async function loadCommodityHedges() {
            try {
                const res = await fetch('/api/panels/commodity-hedges');
                const data = await res.json();
                const totalWeight = (data.total_weight || 0) * 100;
                document.getElementById('commodityWeight').textContent = totalWeight.toFixed(1) + '%';
                
                const members = data.members || [];
                const topMember = members.length > 0 ? members[0] : null;
                document.getElementById('commodityTop').textContent = topMember ? topMember.symbol : '—';
                
                const tbody = document.getElementById('commodityTable');
                if (members.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 40px; color: #94a3b8;">No commodity hedge data available</td></tr>';
                } else {
                    tbody.innerHTML = members.map(m => `
                    <tr>
                            <td>${m.symbol}</td>
                            <td>${(m.weight_pct ?? (m.weight || 0) * 100).toFixed(2)}%</td>
                            <td>${m.price != null ? '$' + m.price.toFixed(2) : '—'}</td>
                            <td>${(m.source || 'alpaca').toUpperCase()}</td>
                    </tr>
                `).join('');
                }
            } catch (e) {
                console.error('Error loading commodity hedge panel:', e);
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
                    tbody.innerHTML = '<tr><td colspan="2" style="text-align:center; padding: 40px; color: #94a3b8;">No macro signals available</td></tr>';
                } else {
                    tbody.innerHTML = signals.map(s => `
                        <tr>
                            <td>${s.label || s.symbol}</td>
                            <td>${s.value != null ? s.value.toFixed(2) : '—'}</td>
                        </tr>
                    `).join('');
                }
            } catch (e) {
                console.error('Error loading macro signals panel:', e);
            }
        }
        
        async function loadRiskAttribution() {
            try {
                const res = await fetch('/api/risk-attribution');
                const data = await res.json();
                
                // Update diversification score
                document.getElementById('diversificationScore').textContent = 
                    (data.diversification_score || 0).toFixed(1) + '/100';
                
                // Load risk contribution chart
                if (data.risk_contributions && Object.keys(data.risk_contributions).length > 0) {
                    const strategies = Object.keys(data.risk_contributions);
                    const contributions = Object.values(data.risk_contributions);
                    Plotly.newPlot('riskContributionChart', [{
                        x: strategies,
                        y: contributions,
                        type: 'bar',
                        marker: { color: contributions.map(c => c > 40 ? '#ef4444' : c > 20 ? '#f59e0b' : '#10b981') }
                    }], {
                        title: 'Risk Contribution by Strategy (%)',
                        plot_bgcolor: '#1e293b',
                        paper_bgcolor: '#1e293b',
                        font: { color: '#e0e7ff' }
                    });
                }
                
                // Load risk table
                const tbody = document.getElementById('riskTable');
                if (data.strategies && data.strategies.length > 0) {
                    tbody.innerHTML = data.strategies.map(s => `
                        <tr>
                            <td>${s.strategy}</td>
                            <td>${s.allocation_pct.toFixed(1)}%</td>
                            <td>${s.risk_contribution_pct.toFixed(1)}%</td>
                            <td>${s.volatility_pct.toFixed(1)}%</td>
                            <td>${s.alert ? '<span class="status-badge status-pending">HIGH</span>' : '<span class="status-badge status-approved">OK</span>'}</td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px; color: #94a3b8;">No risk data available</td></tr>';
                }
            } catch (e) {
                console.error('Error loading risk attribution:', e);
            }
        }
        
        async function loadEvents() {
            try {
                const filter = document.getElementById('eventFilter')?.value || '';
                const url = filter ? `/api/events?type=${filter}` : '/api/events';
                const res = await fetch(url);
                const data = await res.json();
                const tbody = document.getElementById('eventsTable');
                
                if (data.events && data.events.length > 0) {
                    tbody.innerHTML = data.events.slice(-50).reverse().map(e => `
                        <tr>
                            <td>${new Date(e.timestamp).toLocaleString()}</td>
                            <td><span class="status-badge ${e.type === 'BUY' || e.type === 'SIGNAL_BUY' ? 'status-approved' : e.type === 'SELL' || e.type === 'SIGNAL_SELL' ? 'status-rejected' : 'status-pending'}">${e.type}</span></td>
                            <td>${e.source || 'unknown'}</td>
                            <td style="font-size: 12px; color: #94a3b8;">${JSON.stringify(e.data).substring(0, 100)}...</td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 40px; color: #94a3b8;">No events available</td></tr>';
                }
            } catch (e) {
                console.error('Error loading events:', e);
            }
        }
        
        function updateLastRefresh() {
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }
        
        function startAutoRefresh() {
            loadStats();
            updateLastRefresh();
            refreshInterval = setInterval(() => {
                loadStats();
                const activePanel = document.querySelector('.panel.active').id;
                if (activePanel === 'overview') {
                    loadEquityChart();
                    loadRiskChart();
                } else if (activePanel === 'transactions') {
                    loadTransactions();
                } else if (activePanel === 'approvals') {
                    loadApprovals();
                } else if (activePanel === 'agents') {
                    loadAgents();
                } else if (activePanel === 'revenue') {
                    loadRevenue();
                } else if (activePanel === 'portfolio') {
                    loadPortfolioAnalytics();
                } else if (activePanel === 'risk') {
                    loadRiskAttribution();
                } else if (activePanel === 'events') {
                    loadEvents();
                }
                updateLastRefresh();
            }, 5000); // Refresh every 5 seconds
        }
        
        // Initialize
        startAutoRefresh();
    </script>
</body>
</html>"""
    return HTMLResponse(html)


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value in (None, "", "None"):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


@app.get("/api/stats")
def get_stats():
    """Get dashboard statistics."""
    try:
        equity = 100000.0
        daily_pnl = 0.0
        total_trades = 0
        win_rate = 0.0
        trading_mode_raw = (
            (STATE / "trading_mode.json").read_text().strip()
            if (STATE / "trading_mode.json").exists()
            else ""
        )
        trading_mode = ""

        perf_file = STATE / "performance_metrics.csv"
        if perf_file.exists():
            with open(perf_file) as f:
                rows = list(csv.DictReader(f))
                if rows:
                    latest = rows[-1]
                    equity = _safe_float(latest.get("equity"), equity)
                    daily_pnl = _safe_float(latest.get("pnl_1d"), daily_pnl)

        pnl_file = STATE / "pnl_history.csv"
        if pnl_file.exists():
            with open(pnl_file) as f:
                rows = list(csv.DictReader(f))
            total_trades = max(len(rows), 0)
            if rows:
                wins = sum(1 for row in rows if _safe_float(row.get("pnl") or row.get("fee")) > 0)
                total = len(rows)
                win_rate = wins / total if total else 0.0

        pending = len(load_approval_queue())

        if trading_mode_raw:
            try:
                trading_mode = json.loads(trading_mode_raw).get("mode", "")
            except json.JSONDecodeError:
                trading_mode = trading_mode_raw

        return {
            "equity": equity,
            "dailyPnl": daily_pnl,
            "totalTrades": total_trades,
            "winRate": win_rate,
            "pendingApprovals": pending,
            "mode": trading_mode or "PAPER",
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/transactions")
def get_transactions():
    """Get all transactions."""
    try:
        transactions = []
        pnl_file = STATE / "pnl_history.csv"
        if pnl_file.exists():
            with open(pnl_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    transactions.append(
                        {
                            "timestamp": row.get("ts", ""),
                            "symbol": row.get("symbol", ""),
                            "side": row.get("side", ""),
                            "qty": float(row.get("qty", 0)),
                            "price": float(row.get("price", 0)),
                            "pnl": float(row.get("fee", 0)),  # Simplified
                            "status": "executed",
                        }
                    )
        return {"transactions": transactions[-100:]}  # Last 100
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/approvals")
def get_approvals():
    """Get pending approvals."""
    queue = load_approval_queue()
    return {"pending": queue}


@app.post("/api/approve/{transaction_id}")
def approve_transaction(transaction_id: int):
    """Approve a transaction."""
    queue = load_approval_queue()
    transaction = next((t for t in queue if t.get("id") == transaction_id), None)
    if transaction:
        transaction["status"] = "approved"
        approved = load_approved()
        approved.append(transaction)
        APPROVED_FILE.write_text(json.dumps(approved, indent=2))
        queue.remove(transaction)
        save_approval_queue(queue)
        return {"status": "approved"}
    raise HTTPException(status_code=404, detail="Transaction not found")


@app.post("/api/reject/{transaction_id}")
def reject_transaction(transaction_id: int):
    """Reject a transaction."""
    queue = load_approval_queue()
    transaction = next((t for t in queue if t.get("id") == transaction_id), None)
    if transaction:
        transaction["status"] = "rejected"
        queue.remove(transaction)
        save_approval_queue(queue)
        return {"status": "rejected"}
    raise HTTPException(status_code=404, detail="Transaction not found")


@app.get("/api/equity-curve")
def get_equity_curve():
    """Get equity curve data for chart."""
    try:
        dates = []
        equity = []
        perf_file = STATE / "performance_metrics.csv"
        if perf_file.exists():
            with open(perf_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    dates.append(row.get("timestamp", ""))
                    equity.append(float(row.get("equity", 100000)))
        return {"dates": dates, "equity": equity}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/risk-metrics")
def get_risk_metrics():
    """Get risk and confidence metrics."""
    try:
        dates = []
        risk_scaler = []
        confidence = []

        # Read from telemetry or brain file
        brain_file = RUNTIME / "atlas_brain.json"
        if brain_file.exists():
            data = json.loads(brain_file.read_text())
            dates.append(data.get("updated", ""))
            risk_scaler.append(data.get("risk_scaler", 1.0))
            confidence.append(data.get("confidence", 0.5))

        return {"dates": dates, "risk_scaler": risk_scaler, "confidence": confidence}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/agents")
def get_agents():
    """Get agent status."""
    agents = [
        {
            "name": "intelligence_orchestrator",
            "status": "running",
            "lastUpdate": "Just now",
            "performance": "Good",
        },
        {
            "name": "smart_trader",
            "status": "running",
            "lastUpdate": "Just now",
            "performance": "Active",
        },
        {
            "name": "market_intelligence",
            "status": "running",
            "lastUpdate": "Just now",
            "performance": "Gathering",
        },
        {
            "name": "strategy_research",
            "status": "running",
            "lastUpdate": "Just now",
            "performance": "Analyzing",
        },
    ]
    return {"agents": agents}


@app.get("/api/revenue")
def get_revenue():
    """Get revenue by agent."""
    try:
        revenue_file = STATE / "revenue_by_agent.json"
        agents = []
        if revenue_file.exists():
            data = json.loads(revenue_file.read_text())
            for name, info in data.get("agents", {}).items():
                revenue = info.get("total_revenue", 0.0)
                cost = info.get("total_cost", 0.0)
                net_pnl = revenue - cost
                roi = (net_pnl / cost * 100) if cost > 0 else 0.0
                agents.append(
                    {
                        "name": name,
                        "revenue": revenue,
                        "cost": cost,
                        "netPnl": net_pnl,
                        "roi": roi,
                        "status": info.get("status", "active"),
                    }
                )
        return {"agents": agents}
    except Exception:
        return {"agents": []}


@app.get("/api/analytics")
def get_analytics():
    """Get analytics data."""
    try:
        # Market sentiment
        intel_file = STATE / "market_intelligence.json"
        sentiment = []
        if intel_file.exists():
            data = json.loads(intel_file.read_text())
            for sym, signals in data.get("signals", {}).items():
                composite = signals.get("composite_sentiment", 0.0)
                sentiment.append({"symbol": sym, "score": composite})

        # Strategy performance
        strategies_file = STATE / "strategy_performance.json"
        strategies = []
        if strategies_file.exists():
            data = json.loads(strategies_file.read_text())
            for name, info in data.get("scores", {}).items():
                strategies.append(
                    {
                        "name": info.get("stats", {}).get("name", name),
                        "score": info.get("score", 0.0),
                    }
                )

        return {"sentiment": sentiment, "strategies": strategies}
    except Exception:
        return {"sentiment": [], "strategies": []}


@app.get("/api/panels/ai-cohort")
def get_ai_cohort_panel():
    """AI rotation cohort panel data."""
    context = _load_allocation_groups()
    allocations = context["allocations"]
    groups = context["groups"]
    ai_symbols = groups.get("ai_rotation", [])
    return _build_group_panel("ai_rotation", ai_symbols, allocations)


@app.get("/api/panels/commodity-hedges")
def get_commodity_hedges_panel():
    """Commodity hedge panel data."""
    context = _load_allocation_groups()
    allocations = context["allocations"]
    groups = context["groups"]
    macro_symbols = groups.get("macro_hedges", [])
    focus = [sym for sym in macro_symbols if sym in {"GLD", "SLV", "USO"}]
    if not focus:
        focus = ["GLD", "SLV", "USO"]
    return _build_group_panel("commodity_hedges", focus, allocations)


@app.get("/api/panels/macro-signals")
def get_macro_signals_panel():
    """Macro signal panel data (yield curve, MOVE, VIX)."""
    return _build_macro_signals_payload()


@app.get("/governor/allocations")
def get_portfolio_allocations():
    """Get current portfolio allocations from optimizer (Phase 2500-2700)."""
    try:
        allocations_file = STATE / "allocations.json"
        if allocations_file.exists():
            data = json.loads(allocations_file.read_text())
            return {
                "weights": data.get("weights", {}),
                "method": data.get("method", "unknown"),
                "expected_sharpe": data.get("expected_sharpe", 0.0),
                "expected_return": data.get("expected_return", 0.0),
                "expected_volatility": data.get("expected_volatility", 0.0),
                "risk_budget": data.get("risk_budget", 1.0),
                "timestamp": data.get("timestamp", ""),
            }
        else:
            # Fallback to runtime allocations
            runtime_file = RUNTIME / "allocations_override.json"
            if runtime_file.exists():
                data = json.loads(runtime_file.read_text())
                return {
                    "weights": data.get("allocations", {}),
                    "method": "runtime",
                    "timestamp": data.get("timestamp", ""),
                }
            return {"weights": {}, "method": "default"}
    except Exception as e:
        return {"weights": {}, "error": str(e)}


@app.get("/risk/status")
def get_risk_status():
    """Get comprehensive risk status (Phase 2700-2900)."""
    try:
        # Try to call risk AI server
        import requests

        risk_ai_url = os.getenv("RISK_AI_URL", "http://localhost:8500")
        try:
            response = requests.get(f"{risk_ai_url}/risk/status", timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            pass

        # Fallback: return basic status
        return {
            "cvar_95": -0.05,
            "cvar_99": -0.07,
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}


# =============== PHASE 5600: Meta Metrics Endpoints ==================
@app.post("/meta/metrics")
async def update_meta_metrics(request: Request):
    """Update meta-metrics cache (called by Phase 5600 agent)."""
    try:
        global _meta_metrics_cache, _meta_metrics_timestamp
        data = await request.json()
        _meta_metrics_cache = data
        _meta_metrics_timestamp = datetime.now().isoformat()
        return {"status": "ok", "timestamp": _meta_metrics_timestamp}
    except Exception as e:
        return {"error": str(e)}


@app.get("/meta/metrics")
def get_meta_metrics():
    """Get combined meta-metrics (Phase 5600 endpoint)."""
    global _meta_metrics_cache, _meta_metrics_timestamp

    # If cache is empty, try to build from files
    if not _meta_metrics_cache:
        try:
            import sys

            sys.path.insert(0, str(ROOT))
            from agents.phase_5600_hive_telemetry import build_meta_metrics

            _meta_metrics_cache = build_meta_metrics()
            _meta_metrics_timestamp = datetime.now().isoformat()
        except Exception as e:
            return {
                "error": f"Failed to build metrics: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    return {**(_meta_metrics_cache or {}), "cache_timestamp": _meta_metrics_timestamp}


@app.get("/meta/performance")
def get_performance():
    """Get performance attribution data."""
    try:
        perf_file = STATE / "performance_attribution.json"
        if perf_file.exists():
            return json.loads(perf_file.read_text())
        return {"decisions": [], "last_update": None}
    except Exception as e:
        return {"error": str(e)}


@app.get("/meta/regime")
def get_regime():
    """Get market regime data."""
    try:
        regime_file = RUNTIME / "market_regime.json"
        if regime_file.exists():
            return json.loads(regime_file.read_text())
        return {"regime": "UNKNOWN", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"regime": "UNKNOWN", "timestamp": datetime.now().isoformat(), "error": str(e)}


@app.get("/api/portfolio-analytics")
def get_portfolio_analytics():
    """Get portfolio analytics and attribution data."""
    try:
        # Load portfolio analytics report
        analytics_file = STATE / "portfolio_analytics_report.json"
        if analytics_file.exists():
            data = json.loads(analytics_file.read_text())

            # Extract attribution data
            attribution = []
            strategies = []

            perf_attribution = data.get("performance_attribution", {})
            for strategy_name, contribution in perf_attribution.items():
                attribution.append({"strategy": strategy_name, "contribution": contribution})

            # Get strategy details from allocations and performance
            allocations_file = RUNTIME / "strategy_allocations.json"
            performance_file = STATE / "strategy_performance.json"

            allocations = {}
            performance = {}

            if allocations_file.exists():
                alloc_data = json.loads(allocations_file.read_text())
                allocations = alloc_data.get("allocations", {})

            if performance_file.exists():
                perf_data = json.loads(performance_file.read_text())
                performance = perf_data.get("strategy_performance", {})

            # Build strategy list
            for strategy_name in allocations.keys():
                perf = performance.get(strategy_name, {})
                strategies.append(
                    {
                        "name": strategy_name,
                        "allocation": allocations.get(strategy_name, 0.0),
                        "contribution": perf_attribution.get(strategy_name, 0.0),
                        "sharpe": perf.get("sharpe_ratio", 0.0),
                        "trade_count": perf.get("trade_count", 0),
                    }
                )

            return {
                "attribution": attribution,
                "factor_exposure": data.get("factor_exposure", {}),
                "strategies": strategies,
                "portfolio_sharpe": data.get("portfolio_sharpe", 0.0),
                "portfolio_volatility": data.get("portfolio_volatility", 0.0),
            }

        return {"attribution": [], "factor_exposure": {}, "strategies": []}
    except Exception as e:
        return {"error": str(e), "attribution": [], "factor_exposure": {}, "strategies": []}


@app.get("/api/risk-attribution")
def get_risk_attribution():
    """Get risk attribution data."""
    try:
        # Load risk attribution report
        risk_file = STATE / "risk_attribution.json"
        if risk_file.exists():
            data = json.loads(risk_file.read_text())

            # Build strategy list for table
            strategies = []
            allocations = data.get("allocations", {})
            risk_contributions = data.get("risk_contributions", {})
            volatilities = data.get("volatilities", {})
            concentrated = data.get("concentrated_exposures", [])
            concentrated_names = {exp["strategy"] for exp in concentrated}

            for strategy_name in allocations.keys():
                strategies.append(
                    {
                        "strategy": strategy_name,
                        "allocation_pct": allocations.get(strategy_name, 0.0),
                        "risk_contribution_pct": risk_contributions.get(strategy_name, 0.0),
                        "volatility_pct": volatilities.get(strategy_name, 0.0),
                        "alert": strategy_name in concentrated_names,
                    }
                )

            return {
                "diversification_score": data.get("diversification_score", 0.0),
                "risk_contributions": risk_contributions,
                "strategies": strategies,
                "concentrated_exposures": concentrated,
                "portfolio_risk_metrics": data.get("portfolio_risk_metrics", {}),
            }

        return {
            "diversification_score": 0.0,
            "risk_contributions": {},
            "strategies": [],
            "concentrated_exposures": [],
        }
    except Exception as e:
        return {
            "error": str(e),
            "diversification_score": 0.0,
            "risk_contributions": {},
            "strategies": [],
        }


@app.get("/api/events")
def get_events(type: str | None = None):
    """Get event stream data."""
    try:
        from phases.phase_3900_4100_events import get_recent_events

        if type:
            events = get_recent_events(event_type=type, limit=100)
        else:
            events = get_recent_events(limit=100)

        return {"events": events, "count": len(events)}
    except ImportError:
        # Fallback: read from file directly
        events_file = STATE / "event_stream.json"
        if events_file.exists():
            try:
                events = json.loads(events_file.read_text())
                if type:
                    events = [e for e in events if e.get("type") == type]
                return {"events": events[-100:], "count": len(events)}
            except:
                pass
        return {"events": [], "count": 0}
    except Exception as e:
        return {"error": str(e), "events": [], "count": 0}


# Observability endpoints
if HAS_OBSERVABILITY:
    @app.get("/observability/summary")
    def get_observability_summary_endpoint():
        """Get comprehensive observability summary."""
        return get_observability_summary()

    @app.get("/observability/agents")
    def get_observability_agents():
        """Get agent status for observability."""
        return get_agent_status()

    @app.get("/observability/predictions")
    def get_observability_predictions():
        """Get failure predictions."""
        return get_failure_predictions()

    @app.get("/observability/anomalies")
    def get_observability_anomalies():
        """Get anomaly detections."""
        return get_anomaly_detections()

    @app.get("/observability/metrics")
    def get_observability_metrics():
        """Get metrics."""
        return get_metrics()

    @app.get("/observability/traces")
    def get_observability_traces(limit: int = 100):
        """Get recent traces."""
        return {"traces": get_traces(limit=limit)}

    @app.get("/metrics")
    def get_prometheus_metrics():
        """Get metrics in Prometheus format."""
        try:
            from utils.metrics_collector import get_metrics_prometheus_format
            return get_metrics_prometheus_format()
        except ImportError:
            return "# Prometheus metrics not available\n"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090)

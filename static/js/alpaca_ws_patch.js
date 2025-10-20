
/*
  AI Money Web — Alpaca Bridge (Phase 34–35)
  - Aggressive WebSocket reconnect
  - Fallback polling every 5s if WS idle
  - Safe DOM binding (re-runs if elements mount late)
*/
(() => {
  const state = {
    lastMsgAt: 0,
    ws: null,
    reconnectDelay: 1500,
    maxDelay: 5000,
    pollIntervalMs: 5000,
    heartbeatMs: 15000,
    pollTimer: null,
    heartbeatTimer: null,
    bound: false,
  };

  const el = {
    get card() { return document.querySelector("#alpaca-card") || document.body; },
    get status() { return document.querySelector("#alpaca-status"); },
    get equity() { return document.querySelector("#alpaca-equity"); },
    get cash() { return document.querySelector("#alpaca-cash"); },
    ensure() {
      // Create minimal UI targets if not present
      if (!this.status) {
        const wrap = document.createElement("div");
        wrap.id = "alpaca-quick-stats";
        wrap.style.display = "grid";
        wrap.style.gridTemplateColumns = "repeat(3, minmax(0, 1fr))";
        wrap.style.gap = "12px";
        wrap.innerHTML = `
          <div class="pro-card"><div class="label">Status</div><div id="alpaca-status" class="value">Loading…</div></div>
          <div class="pro-card"><div class="label">Equity</div><div id="alpaca-equity" class="value">—</div></div>
          <div class="pro-card"><div class="label">Cash</div><div id="alpaca-cash" class="value">—</div></div>
        `;
        (document.querySelector("#alpaca-card .content") || this.card).appendChild(wrap);
      }
    }
  };

  function fmtUSD(x) {
    if (x === null || x === undefined || isNaN(Number(x))) return "—";
    try { return Number(x).toLocaleString(undefined, {style:"currency", currency:"USD"}); }
    catch { return `$${x}`; }
  }

  function applyStatus(payload) {
    el.ensure();
    const { status, equity, cash } = payload || {};
    if (el.status) el.status.textContent = (status || "unknown").toUpperCase();
    if (el.equity) el.equity.textContent = fmtUSD(equity);
    if (el.cash) el.cash.textContent = fmtUSD(cash);
    state.lastMsgAt = Date.now();
  }

  async function pollOnce() {
    try {
      const r = await fetch("/api/alpaca_status", { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const j = await r.json();
      applyStatus(j);
    } catch (e) {
      // optional: console.debug("poll error", e);
    }
  }

  function startPolling() {
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = setInterval(() => {
      const idleMs = Date.now() - state.lastMsgAt;
      if (idleMs > state.pollIntervalMs + 500) pollOnce();
    }, state.pollIntervalMs);
  }

  function startHeartbeat() {
    if (state.heartbeatTimer) clearInterval(state.heartbeatTimer);
    state.heartbeatTimer = setInterval(() => {
      try { state.ws && state.ws.readyState === 1 && state.ws.send(JSON.stringify({type:"ping"})); } catch {}
    }, state.heartbeatMs);
  }

  function wsUrl(path) {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${location.host}${path}`;
  }

  function connect() {
    try { state.ws && state.ws.close && state.ws.close(); } catch {}
    const url = wsUrl("/ws/alpaca_status");
    const ws = new WebSocket(url);
    state.ws = ws;

    ws.addEventListener("open", () => {
      state.reconnectDelay = 1500;
      // Prime with a poll so UI isn't blank while waiting for first tick
      pollOnce();
    });

    ws.addEventListener("message", (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data && (data.status || data.equity || data.cash)) {
          applyStatus(data);
        }
      } catch {}
    });

    ws.addEventListener("close", () => {
      setTimeout(connect, state.reconnectDelay);
      state.reconnectDelay = Math.min(state.reconnectDelay * 1.6, state.maxDelay);
    });

    ws.addEventListener("error", () => {
      try { ws.close(); } catch {}
    });
  }

  function bindEarly() {
    if (state.bound) return;
    state.bound = true;
    el.ensure();
    connect();
    startPolling();
    startHeartbeat();
  }

  // Bind ASAP and also when DOM changes (late-mount dashboards)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindEarly, { once: true });
  } else {
    bindEarly();
  }

  const mo = new MutationObserver(() => el.ensure());
  mo.observe(document.documentElement, { childList: true, subtree: true });
})();

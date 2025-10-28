
# AI Money Web — Phase 34–35 Patch Bundle

This bundle fixes the Alpaca "Loading…" issue, adds a Pro Dark Dashboard skin, and boots glow charts.

## Files

- `static/js/alpaca_ws_patch.js` — WebSocket + fallback polling for `/ws/alpaca_status` + `/api/alpaca_status`
- `static/js/charts_glow_boot.js` — Chart.js v4 glow plugin + safe initialization
- `static/css/dark_pro_skin.css` — 2025-grade dark UI skin (cards, buttons, sidebar)
- `test/test_all.sh` — Starter validation script (curl endpoints)
- `tools/install_phase34_35.sh` — Simple installer (copies assets into your FastAPI app)
- `tools/aimw_unify.py` — Optional: auto-enhancement checker (verifies endpoints, injects assets into template if desired)

## Minimal Template Changes (Jinja/HTML)

Add these tags inside your `dashboard.html` (or equivalent). If you already load Chart.js/Tailwind, keep your versions and just include the two local JS files and CSS.

```html
<!-- Head -->
<link rel="stylesheet" href="/static/css/dark_pro_skin.css">

<!-- Optional: Tailwind CDN for utility classes (dev only) -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Body footer (after your other scripts) -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="/static/js/charts_glow_boot.js"></script>
<script src="/static/js/alpaca_ws_patch.js"></script>
```

Example markup for charts:
```html
<div class="pro-card" style="grid-column: span 12;">
  <div class="pro-header">
    <div class="pro-title">Equity Curve</div>
    <span class="pro-badge">Live</span>
  </div>
  <div class="canvas-300">
    <canvas id="equity-curve" class="chart-glow"></canvas>
  </div>
</div>
```

## Knowledge Sidebar (collapsible)

Add these elements near the end of `<body>`:

```html
<div id="knowledge-tab"><button id="kb-toggle">Knowledge</button></div>
<aside id="knowledge-panel" aria-label="Knowledge Panel">
  <h3>Project Memory</h3>
  <ul>
    <li>Auto-heal: active</li>
    <li>Streams: /ws/alpaca_status /ws/positions /ws/pnl</li>
    <li>Next steps: Supabase persistence, chart streaming</li>
  </ul>
</aside>
<script>
  (function(){
    const p = document.getElementById('knowledge-panel');
    const b = document.getElementById('kb-toggle');
    b.addEventListener('click', ()=> p.classList.toggle('open'));
  })();
</script>
```

## Install (copy assets)

```bash
bash tools/install_phase34_35.sh /path/to/your/fastapi/project
# Example:
# bash tools/install_phase34_35.sh ~/code/ai-money-web
```

## Run Validation

```bash
bash test/test_all.sh
```

Expected:
- `/api/alpaca_status` returns JSON with `status`, `equity`, `cash`
- Positions and stream health endpoints return 200/JSON

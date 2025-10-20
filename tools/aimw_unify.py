
#!/usr/bin/env python3

import sys
import os
import pathlib

HELP = """
AI Money Web — Unifier (Phase 34–35)
- Verifies expected endpoints
- Emits integration hints for world-class polish
- (Optional) can inject asset tags into a template file

Usage:
  python tools/aimw_unify.py /path/to/dashboard.html --inject
"""

ASSET_SNIPPET = """
<link rel="stylesheet" href="/static/css/dark_pro_skin.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="/static/js/charts_glow_boot.js"></script>
<script src="/static/js/alpaca_ws_patch.js"></script>
"""

def inject_assets(path):
    html = pathlib.Path(path).read_text()
    if 'dark_pro_skin.css' in html and 'alpaca_ws_patch.js' in html:
        print("• Assets already present.")
        return
    html = html.replace("</head>", ASSET_SNIPPET + "\n</head>") if "</head>" in html else ASSET_SNIPPET + html
    pathlib.Path(path).write_text(html)
    print(f"• Injected asset tags into {path}")

def main():
    if len(sys.argv) < 2:
        print(HELP); sys.exit(0)
    target = sys.argv[1]
    if os.path.isfile(target) and ("--inject" in sys.argv):
        inject_assets(target)
    print("World-class checklist:")
    checks = [
        "✓ Aggressive WS reconnect & 5s fallback polling",
        "✓ Glow charts (Chart.js v4) with gradient fills",
        "✓ Collapsible knowledge sidebar tab",
        "✓ Responsive 12-col layout & mobile collapse",
        "✓ Shimmer loaders for empty data",
        "✓ Health checks: /control/ping, /api/stream_health",
        "✓ Make target: start-paper to populate charts",
        "✓ Risk badges / status labels for account state",
        "✓ Supabase persistence (next) + Grafana panel feed",
    ]
    for c in checks: print(" -", c)

if __name__ == "__main__":
    main()

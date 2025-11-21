#!/usr/bin/env python3
import http.server
import json
import os
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"
RUNTIME = ROOT / "runtime"
STATE.mkdir(exist_ok=True)
RUNTIME.mkdir(exist_ok=True)

CSV = STATE / "performance_metrics.csv"
HEALTH = STATE / "model_health.json"
LEARNING = RUNTIME / "atlas_learning.json"
SMART = RUNTIME / "smart_params.json"

PORT = int(os.getenv("METRICS_PORT", "9501"))


def latest_metrics_text():
    # Prometheus text exposition
    lines = []
    # csv tail
    try:
        last = CSV.read_text().strip().splitlines()[-1]
        _, equity, pnl, dd, sharpe, sortino, wr, t7 = last.split(",")
        lines += [
            f"neolight_equity {equity}",
            f"neolight_pnl_1d {pnl}",
            f"neolight_drawdown {dd}",
            f"neolight_sharpe_30d {sharpe}",
            f"neolight_sortino_30d {sortino}",
            f"neolight_win_rate_7d {wr}",
            f"neolight_trades_7d {t7}",
        ]
    except Exception:
        pass

    # learning state
    if LEARNING.exists():
        try:
            st = json.loads(LEARNING.read_text())
            lines.append(f"neolight_risk_factor {st.get('risk_factor', 1.0)}")
            lines.append(f"neolight_learn_win_rate {st.get('win_rate', 0.5)}")
        except Exception:
            pass
    return "\n".join(lines) + "\n"


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            txt = latest_metrics_text().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(txt)
        elif self.path == "/model_health":
            if HEALTH.exists():
                data = HEALTH.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(204)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🛰  Metrics exporter on :{PORT} (/metrics, /model_health)", flush=True)
        httpd.serve_forever()

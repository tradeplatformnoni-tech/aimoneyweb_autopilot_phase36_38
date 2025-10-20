#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /absolute/path/to/fastapi_project_root"
  exit 1
fi
DEST="$1"
echo "Installing Phase 34–35 assets into: $DEST"

mkdir -p "$DEST/static/js" "$DEST/static/css"
cp -v "$(dirname "$0")/../static/js/alpaca_ws_patch.js" "$DEST/static/js/"
cp -v "$(dirname "$0")/../static/js/charts_glow_boot.js" "$DEST/static/js/"
cp -v "$(dirname "$0")/../static/css/dark_pro_skin.css" "$DEST/static/css/"

echo "Remember to include in your dashboard template:"
echo '<link rel="stylesheet" href="/static/css/dark_pro_skin.css">'
echo '<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>'
echo '<script src="/static/js/charts_glow_boot.js"></script>'
echo '<script src="/static/js/alpaca_ws_patch.js"></script>'

echo "✅ Install complete."

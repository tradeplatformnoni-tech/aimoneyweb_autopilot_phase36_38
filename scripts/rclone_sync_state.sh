#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/neolight"
rclone copy "$ROOT/state" neo_remote:neolight/state -v --create-empty-src-dirs || true

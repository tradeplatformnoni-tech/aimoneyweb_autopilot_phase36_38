#!/usr/bin/env bash
set -Eeuo pipefail

# Wrapper to call Phase 41–50 from master autopilot
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/../phases/phase_41_50_atlas_dashboard.sh"

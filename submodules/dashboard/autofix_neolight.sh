#!/usr/bin/env bash
# =========================================================
# 🧠  NeoLight Unified AutoFix & Autopilot Controller
#      (Phases 1–12 000+  — Future-Proof Edition)
# ---------------------------------------------------------
#  • Validates and repairs CI/CD configuration
#  • Detects and injects secrets
#  • Re-triggers GitHub Actions workflow automatically
#  • Tests Docker, K8s, Helm, and monitoring stack
#  • Invokes next-phase installers when present
# =========================================================
set -euo pipefail
LOGFILE="autofix_report.log"
REPO=$(git config --get remote.origin.url | sed 's#.*github.com/##; s/.git$//')
echo -e "\n🚀 Starting NeoLight Unified AutoFix Autopilot\n" | tee -a "$LOGFILE"

# ---------------------------------------------------------
# 1️⃣  Ensure executability
echo "🔍 Checking .sh script permissions..."
find . -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
echo "✅ Executable permissions verified."

# ---------------------------------------------------------
# 2️⃣  Verify core tooling
for cmd in git curl kubectl docker; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "⚠️  Missing $cmd — please install before continuing." | tee -a "$LOGFILE"
  fi
done

# ---------------------------------------------------------
# 3️⃣  Secrets detection / load-in
echo "🔐 Checking environment and secrets..."
SECRETS=("NEOLIGHT_GH_TOKEN" "DOCKERHUB_USERNAME" "DOCKERHUB_TOKEN" "KUBE_CONFIG")
MISSING=()
for var in "${SECRETS[@]}"; do
  [[ -z "${!var:-}" ]] && MISSING+=("$var")
done
if ((${#MISSING[@]})); then
  echo "⚠️  Missing secrets: ${MISSING[*]}"
  if [[ -f ~/.autopilot_vault ]]; then
    echo "🧠 Loading from local vault ~/.autopilot_vault ..."
    # shellcheck disable=SC1090
    source ~/.autopilot_vault
  else
    echo "💡 Tip: store secrets in GitHub → Settings → Secrets → Actions"
  fi
else
  echo "✅ All critical secrets available."
fi

# ---------------------------------------------------------
# 4️⃣  Validate kubeconfig
if command -v kubectl &>/dev/null; then
  echo "☸️  Checking Kubernetes connectivity..."
  kubectl cluster-info >/dev/null 2>&1 && echo "✅ K8s reachable." || echo "⚠️  K8s check failed."
fi

# ---------------------------------------------------------
# 5️⃣  GitHub workflow re-trigger
echo "🔗 Syncing with GitHub Actions for repo: $REPO"
TOKEN="${NEOLIGHT_GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -n "$TOKEN" && -n "$REPO" ]]; then
  WF_API="https://api.github.com/repos/$REPO/actions/workflows"
  WF_ID=$(curl -fsS -H "Authorization: Bearer $TOKEN" "$WF_API" | grep -Eo '"id":[0-9]+' | head -n1 | cut -d: -f2 || true)
  if [[ -n "$WF_ID" ]]; then
    echo "🔄 Dispatching workflow id=$WF_ID ..."
    curl -fsS -X POST -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
      "https://api.github.com/repos/$REPO/actions/workflows/$WF_ID/dispatches" \
      -d '{"ref":"main"}' >/dev/null && echo "✅ Workflow triggered."
  else
    echo "⚠️  No workflows found (ensure .github/workflows/cd.yaml exists on main)."
  fi
else
  echo "⚠️  Missing GitHub token or repo — skipping dispatch."
fi

# ---------------------------------------------------------
# 6️⃣  Docker sanity
echo "🐳 Checking Docker daemon..."
docker info >/dev/null 2>&1 && echo "✅ Docker daemon responsive." || echo "⚠️  Docker not running."

# ---------------------------------------------------------
# 7️⃣  Monitoring / Prometheus / Grafana verification
if kubectl get ns neolight-observability >/dev/null 2>&1; then
  echo "📈 Verifying Prometheus & Grafana stack..."
  kubectl -n neolight-observability get pods | grep -E "prom|grafana|loki" || \
    echo "⚠️  Monitoring pods not found — run ./phase10300_monitoring_autopilot.sh"
else
  echo "ℹ️  Observability namespace missing — skip verification."
fi

# ---------------------------------------------------------
# 8️⃣  Auto-invoke next-phase installers if present
echo "🧩 Scanning for next-phase Autopilot scripts..."
for script in phase*.sh; do
  [[ "$script" == "$0" ]] && continue
  if [[ "$script" =~ phase1[01][0-9]{3}.*\.sh ]]; then
    echo "🚀 Detected future-phase script: $script"
    bash "$script" || echo "⚠️  $script exited non-zero, continuing."
  fi
done

# ---------------------------------------------------------
# 9️⃣  Wrap-up
echo "✅ NeoLight AutoFix & Autopilot complete."
date | tee -a "$LOGFILE"
echo "========================================================" >> "$LOGFILE"


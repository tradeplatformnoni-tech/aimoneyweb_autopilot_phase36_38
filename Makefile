# ==========================================================
# 🧠 NeoLight Wealth Mesh — Unified Autopilot Makefile
# Author: Oluwaseye Akinbola
# Project: AIMoneyWeb Autopilot (Phases 1 → 12 000+)
# ==========================================================
# Purpose:
# - Run and manage all phases (Docker, K8s, CI/CD, Monitoring, AutoFix)
# - Integrates GitHub Actions, Prometheus/Grafana, and AutoHealing Agents
# - Future-proof autopilot environment controller
# ==========================================================

PROJECT_NAME := aimoneyweb_autopilot_phase36_38
NAMESPACE    := neolight-observability
GRAFANA_PORT := 30000
PROM_PORT    := 30090
ALERT_PORT   := 30093
LOGFILE      := autopilot.log

# ----------------------------------------------------------
# 🧩 Context Summary (Embedded Documentation)
# ----------------------------------------------------------
# Project Overview:
#   NeoLight Wealth Mesh is a self-healing AI-driven infrastructure mesh
#   integrating Python (Flask + AI Agents), Docker, Kubernetes, and CI/CD
#   to create autonomous trading and analytics pipelines.
#
# Completed Milestones:
#   ✅ Phases 1–38: AI Web Autopilot core (Flask dashboard, agents)
#   ✅ Phase 8100–10000: CI/CD integration via GitHub Actions + DockerHub + GHCR
#   ✅ Phase 10300–11000: Prometheus, Grafana, Loki, AI Monitoring
#   ✅ Unified AutoFix Pilot script (autofix_neolight.sh)
#
# Current Objective:
#   🔹 Verify CI/CD pipelines
#   🔹 Expand AutoFix Pilot → “Guardian Mode” (AI rollback & anomaly response)
#   🔹 Complete Phase 12000+ AI Self-Healing rollout
#
# Known Issues:
#   ⚠️ GitHub PAT scope (repo, workflow, packages)
#   ⚠️ CI workflow detection (cd.yaml name match)
#   ⚠️ Missing local GH CLI (`gh`)
#   ⚠️ Monitoring pods readiness (Helm timing)
#
# Files Included in Context:
#   • autofix_neolight.sh (Unified AutoFix & Phase Scanner)
#   • phase10300_monitoring_autopilot.sh (Monitoring stack)
#   • .github/workflows/cd.yaml (CI/CD workflow)
#   • Dockerfiles / agent_core.py / trading_agent.py
# ==========================================================


# ----------------------------------------------------------
# 🧱 Environment Setup
# ----------------------------------------------------------
setup:
	@echo "🚀 Setting up NeoLight development environment..."
	python3 -m venv venv
	@echo "✅ Virtual environment created (venv)."
	@echo "🧩 Installing base dependencies..."
	@. venv/bin/activate && pip install --upgrade pip setuptools wheel
	@. venv/bin/activate && pip install flask requests kubernetes pyyaml
	@echo "✅ Environment ready."

# ----------------------------------------------------------
# 🧠 Run AutoFix Pilot
# ----------------------------------------------------------
fix:
	@echo "🩺 Running NeoLight AutoFix Pilot..."
	@chmod +x ./autofix_neolight.sh || true
	@./autofix_neolight.sh || echo "⚠️ AutoFix encountered issues — check $(LOGFILE)"
	@echo "✅ AutoFix complete."

# ----------------------------------------------------------
# 🧩 Run CI/CD Workflow (Local Trigger)
# ----------------------------------------------------------
ci:
	@echo "🔄 Triggering GitHub Actions CI/CD build..."
	@bash ./phase8100_neolight_ci_autopilot.sh || echo "⚠️ CI/CD script missing or failed."

# ----------------------------------------------------------
# ☸️ Deploy Monitoring Stack (Prometheus/Grafana/Loki)
# ----------------------------------------------------------
monitor:
	@echo "📈 Deploying NeoLight Monitoring Stack (Prometheus/Grafana)..."
	@chmod +x ./phase10300_monitoring_autopilot.sh || true
	@./phase10300_monitoring_autopilot.sh || echo "⚠️ Monitoring stack deployment failed."
	@echo "✅ Monitoring stack launched."
	@echo "🌐 Grafana: http://127.0.0.1:$(GRAFANA_PORT)"
	@echo "📊 Prometheus: http://127.0.0.1:$(PROM_PORT)"

# ----------------------------------------------------------
# 🧩 Full Autopilot Execution (Phases 1 → 12 000)
# ----------------------------------------------------------
autopilot:
	@echo "🚀 Executing NeoLight Full Autopilot..."
	@make fix
	@make ci
	@make monitor
	@echo "✅ NeoLight Autopilot executed all core phases."

# ----------------------------------------------------------
# 🧹 Clean Environment
# ----------------------------------------------------------
clean:
	@echo "🧼 Cleaning up environment..."
	@docker-compose down || true
	@docker system prune -f || true
	@rm -rf venv __pycache__ *.log k8s/monitoring || true
	@echo "✅ Environment cleaned."

# ----------------------------------------------------------
# 🧪 Diagnostics
# ----------------------------------------------------------
status:
	@echo "🔍 Checking system diagnostics..."
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true
	@kubectl get pods -A | grep neolight || echo "⚠️ No NeoLight pods found."
	@echo "✅ Status check complete."

# ----------------------------------------------------------
# 🔒 Vault Operations
# ----------------------------------------------------------
vault:
	@echo "🔐 Creating local vault (~/.autopilot_vault)..."
	@echo 'export NEOLIGHT_GH_TOKEN="your_gh_token_here"' > ~/.autopilot_vault
	@echo 'export DOCKERHUB_USERNAME="your_dockerhub_user"' >> ~/.autopilot_vault
	@echo 'export DOCKERHUB_TOKEN="your_dockerhub_token"' >> ~/.autopilot_vault
	@echo 'export KUBE_CONFIG="$$(cat ~/.kube/config)"' >> ~/.autopilot_vault
	@chmod 600 ~/.autopilot_vault
	@echo "✅ Vault created and secured."

# ----------------------------------------------------------
# 🧠 Phase Management
# ----------------------------------------------------------
phase-scan:
	@echo "🧩 Scanning for available phase scripts..."
	@ls -1 phase*.sh | sort || echo "⚠️ No phase scripts found."

phase-run:
	@read -p "Enter phase script to run (e.g., phase10300_monitoring_autopilot.sh): " p; \
	if [ -f "$$p" ]; then \
		chmod +x "$$p" && echo "🚀 Running $$p..." && bash "$$p"; \
	else \
		echo "⚠️ Phase script not found: $$p"; \
	fi

# ----------------------------------------------------------
# 📦 Targets Overview
# ----------------------------------------------------------
help:
	@echo "🧭 NeoLight Autopilot Makefile — Available Commands:"
	@echo "  make setup         → Setup Python venv & dependencies"
	@echo "  make fix           → Run NeoLight AutoFix Pilot"
	@echo "  make ci            → Trigger CI/CD GitHub workflow"
	@echo "  make monitor       → Deploy Prometheus/Grafana/Loki"
	@echo "  make autopilot     → Run full unified autopilot flow"
	@echo "  make clean         → Cleanup containers & env"
	@echo "  make status        → Show Docker/K8s status"
	@echo "  make vault         → Create or update local secret vault"
	@echo "  make phase-scan    → List all available phase scripts"
	@echo "  make phase-run     → Run a specific phase script interactively"
	@echo ""
	@echo "📄 Log output → $(LOGFILE)"
	@echo "=========================================================="


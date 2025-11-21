#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ Render Services Assessment Helper                                ║
# ║ Interactive tool to assess and document Render services        ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

# Colors
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
RED=$'\033[0;31m'
CYAN=$'\033[0;36m'
RESET=$'\033[0m'

ASSESSMENT_FILE="$HOME/neolight/render_services_assessment.txt"

echo "${CYAN}╔══════════════════════════════════════════════════════════════════╗${RESET}"
echo "${CYAN}║  Render Services Assessment Helper                               ║${RESET}"
echo "${CYAN}╚══════════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# Create assessment file
cat > "$ASSESSMENT_FILE" << 'EOF'
# Render Services Assessment
# ==========================
# Date: $(date)
# 
# Instructions:
# 1. For each service in Render dashboard, fill in the details below
# 2. Mark action: KEEP, SUSPEND, or DELETE
# 3. Export any useful data before deleting
#
# Format:
# Service Name | Type | Last Deployed | Status | Cost | Has Data | Action | Notes
# -------------|------|---------------|--------|------|----------|--------|------
EOF

echo "${YELLOW}📋 Assessment file created: $ASSESSMENT_FILE${RESET}"
echo ""
echo "${CYAN}Instructions:${RESET}"
echo "1. ${GREEN}Open Render dashboard${RESET} (should be opening in browser)"
echo "2. ${GREEN}Go to Services tab${RESET}"
echo "3. ${GREEN}For each service, fill in the assessment file${RESET}"
echo ""
echo "${YELLOW}Assessment Questions for Each Service:${RESET}"
echo ""
echo "  ${CYAN}1. Service Name:${RESET} What is it called?"
echo "  ${CYAN}2. Type:${RESET} Web Service, Background Worker, Database, etc."
echo "  ${CYAN}3. Last Deployed:${RESET} When was it last updated?"
echo "  ${CYAN}4. Status:${RESET} Running, Suspended, or Stopped?"
echo "  ${CYAN}5. Cost:${RESET} Is it costing money? (Check billing)"
echo "  ${CYAN}6. Has Data:${RESET} Does it have databases, files, or important data?"
echo "  ${CYAN}7. Action:${RESET} KEEP, SUSPEND, or DELETE"
echo "  ${CYAN}8. Notes:${RESET} Any additional info"
echo ""
echo "${YELLOW}Decision Guide:${RESET}"
echo ""
echo "  ${GREEN}KEEP:${RESET}"
echo "    - NeoLight-related services"
echo "    - Services you actively use"
echo "    - Services with important data you need"
echo "    - Services currently in production"
echo ""
echo "  ${YELLOW}SUSPEND:${RESET}"
echo "    - Services you might need later"
echo "    - Services with data you want to keep"
echo "    - Services you're unsure about"
echo "    - Saves money, keeps data"
echo ""
echo "  ${RED}DELETE:${RESET}"
echo "    - Old test deployments"
echo "    - Services you don't recognize"
echo "    - Duplicate services"
echo "    - Services with no data/value"
echo ""
echo "${CYAN}Opening assessment file...${RESET}"
echo ""

# Open assessment file in default editor
if command -v code >/dev/null 2>&1; then
    code "$ASSESSMENT_FILE"
elif command -v nano >/dev/null 2>&1; then
    nano "$ASSESSMENT_FILE"
else
    open -e "$ASSESSMENT_FILE" 2>/dev/null || echo "Please edit: $ASSESSMENT_FILE"
fi

echo ""
echo "${GREEN}✅ Assessment file ready!${RESET}"
echo ""
echo "${YELLOW}Next Steps:${RESET}"
echo "1. Fill in the assessment file with your Render services"
echo "2. Export useful data (env vars, databases) before deleting"
echo "3. Take action: Keep, Suspend, or Delete services"
echo ""
echo "${CYAN}Useful Commands:${RESET}"
echo "  - View assessment: cat $ASSESSMENT_FILE"
echo "  - Edit assessment: code $ASSESSMENT_FILE"
echo ""


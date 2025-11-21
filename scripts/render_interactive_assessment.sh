#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ Render Services - Interactive Assessment Tool                    ║
# ║ Guides you through assessing each Render service                 ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

# Colors
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
RED=$'\033[0;31m'
CYAN=$'\033[0;36m'
BLUE=$'\033[0;34m'
RESET=$'\033[0m'

ASSESSMENT_FILE="$HOME/neolight/render_services_assessment.txt"
RESULTS_FILE="$HOME/neolight/render_assessment_results.txt"

echo "${CYAN}╔══════════════════════════════════════════════════════════════════╗${RESET}"
echo "${CYAN}║  Render Services - Interactive Assessment                        ║${RESET}"
echo "${CYAN}╚══════════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# Initialize results file
cat > "$RESULTS_FILE" << 'EOF'
# Render Services Assessment Results
# ===================================
# Date: $(date '+%Y-%m-%d %H:%M:%S')
#
# Summary:
# - Services to KEEP: 0
# - Services to SUSPEND: 0
# - Services to DELETE: 0
# - Estimated Monthly Savings: $0
#
# Detailed Assessment:
# ====================
EOF

echo "${YELLOW}📋 This tool will help you assess your Render services${RESET}"
echo ""
echo "${CYAN}Instructions:${RESET}"
echo "1. Have Render dashboard open: https://dashboard.render.com"
echo "2. Go to Services tab"
echo "3. For each service, answer the questions below"
echo "4. Results will be saved to: $RESULTS_FILE"
echo ""
read -p "${GREEN}Press Enter to start assessment...${RESET}"

SERVICE_COUNT=0
KEEP_COUNT=0
SUSPEND_COUNT=0
DELETE_COUNT=0
TOTAL_SAVINGS=0

while true; do
    echo ""
    echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo "${CYAN}Service #$((SERVICE_COUNT + 1))${RESET}"
    echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    
    read -p "${YELLOW}Service Name (or 'done' to finish):${RESET} " SERVICE_NAME
    
    if [[ "$SERVICE_NAME" == "done" ]] || [[ -z "$SERVICE_NAME" ]]; then
        break
    fi
    
    echo ""
    echo "${CYAN}Service: $SERVICE_NAME${RESET}"
    echo ""
    
    # Type
    echo "${YELLOW}Service Type:${RESET}"
    echo "  1) Web Service"
    echo "  2) Background Worker"
    echo "  3) Database"
    echo "  4) Static Site"
    echo "  5) Other"
    read -p "Select [1-5]: " TYPE_CHOICE
    case $TYPE_CHOICE in
        1) SERVICE_TYPE="Web Service" ;;
        2) SERVICE_TYPE="Background Worker" ;;
        3) SERVICE_TYPE="Database" ;;
        4) SERVICE_TYPE="Static Site" ;;
        5) read -p "Enter type: " SERVICE_TYPE ;;
        *) SERVICE_TYPE="Unknown" ;;
    esac
    
    # Last Deployed
    read -p "${YELLOW}Last Deployed Date (YYYY-MM-DD or 'unknown'):${RESET} " LAST_DEPLOYED
    
    # Status
    echo ""
    echo "${YELLOW}Current Status:${RESET}"
    echo "  1) Running"
    echo "  2) Suspended"
    echo "  3) Stopped"
    read -p "Select [1-3]: " STATUS_CHOICE
    case $STATUS_CHOICE in
        1) STATUS="Running" ;;
        2) STATUS="Suspended" ;;
        3) STATUS="Stopped" ;;
        *) STATUS="Unknown" ;;
    esac
    
    # Cost
    read -p "${YELLOW}Monthly Cost ($0 if free/unknown):${RESET} $" MONTHLY_COST
    MONTHLY_COST=${MONTHLY_COST:-0}
    
    # Has Data
    echo ""
    echo "${YELLOW}Does this service have important data?${RESET}"
    echo "  1) Yes - Has databases/files I need"
    echo "  2) No - No important data"
    read -p "Select [1-2]: " DATA_CHOICE
    case $DATA_CHOICE in
        1) HAS_DATA="Yes" ;;
        2) HAS_DATA="No" ;;
        *) HAS_DATA="Unknown" ;;
    esac
    
    # NeoLight Related
    echo ""
    echo "${YELLOW}Is this service related to NeoLight/trading?${RESET}"
    echo "  1) Yes"
    echo "  2) No"
    echo "  3) Unsure"
    read -p "Select [1-3]: " NEO_CHOICE
    case $NEO_CHOICE in
        1) NEO_RELATED="Yes" ;;
        2) NEO_RELATED="No" ;;
        3) NEO_RELATED="Unsure" ;;
        *) NEO_RELATED="Unknown" ;;
    esac
    
    # Decision
    echo ""
    echo "${CYAN}Based on your answers, recommendation:${RESET}"
    if [[ "$NEO_RELATED" == "Yes" ]] && [[ "$STATUS" == "Running" ]]; then
        RECOMMENDATION="KEEP"
        echo "${GREEN}✅ Recommended: KEEP (NeoLight-related and active)${RESET}"
    elif [[ "$NEO_RELATED" == "Yes" ]] && [[ "$HAS_DATA" == "Yes" ]]; then
        RECOMMENDATION="SUSPEND"
        echo "${YELLOW}⏸️  Recommended: SUSPEND (NeoLight-related, has data, but not active)${RESET}"
    elif [[ "$HAS_DATA" == "Yes" ]]; then
        RECOMMENDATION="SUSPEND"
        echo "${YELLOW}⏸️  Recommended: SUSPEND (Has data, might need later)${RESET}"
    else
        RECOMMENDATION="DELETE"
        echo "${RED}❌ Recommended: DELETE (No data, not NeoLight-related)${RESET}"
    fi
    
    echo ""
    echo "${YELLOW}Final Decision:${RESET}"
    echo "  1) KEEP"
    echo "  2) SUSPEND"
    echo "  3) DELETE"
    echo "  4) Use recommendation ($RECOMMENDATION)"
    read -p "Select [1-4]: " ACTION_CHOICE
    
    case $ACTION_CHOICE in
        1) FINAL_ACTION="KEEP"; ((KEEP_COUNT++)) ;;
        2) FINAL_ACTION="SUSPEND"; ((SUSPEND_COUNT++)); TOTAL_SAVINGS=$(echo "$TOTAL_SAVINGS + $MONTHLY_COST" | bc) ;;
        3) FINAL_ACTION="DELETE"; ((DELETE_COUNT++)); TOTAL_SAVINGS=$(echo "$TOTAL_SAVINGS + $MONTHLY_COST" | bc) ;;
        4) FINAL_ACTION="$RECOMMENDATION"
           case $RECOMMENDATION in
               KEEP) ((KEEP_COUNT++)) ;;
               SUSPEND) ((SUSPEND_COUNT++)); TOTAL_SAVINGS=$(echo "$TOTAL_SAVINGS + $MONTHLY_COST" | bc) ;;
               DELETE) ((DELETE_COUNT++)); TOTAL_SAVINGS=$(echo "$TOTAL_SAVINGS + $MONTHLY_COST" | bc) ;;
           esac
           ;;
        *) FINAL_ACTION="UNKNOWN" ;;
    esac
    
    # Notes
    echo ""
    read -p "${YELLOW}Additional notes (optional):${RESET} " NOTES
    
    # Save to results
    cat >> "$RESULTS_FILE" << EOF

## Service: $SERVICE_NAME
- **Type:** $SERVICE_TYPE
- **Last Deployed:** $LAST_DEPLOYED
- **Status:** $STATUS
- **Monthly Cost:** \$$MONTHLY_COST
- **Has Data:** $HAS_DATA
- **NeoLight Related:** $NEO_RELATED
- **Action:** $FINAL_ACTION
- **Notes:** $NOTES

EOF
    
    # Save to assessment file (table format)
    echo "$SERVICE_NAME | $SERVICE_TYPE | $LAST_DEPLOYED | $STATUS | \$$MONTHLY_COST | $HAS_DATA | $FINAL_ACTION | $NOTES" >> "$ASSESSMENT_FILE"
    
    ((SERVICE_COUNT++))
    
    echo ""
    echo "${GREEN}✅ Service assessed!${RESET}"
    echo ""
    read -p "${CYAN}Press Enter to continue to next service...${RESET}"
done

# Update summary
sed -i '' "s/- Services to KEEP: 0/- Services to KEEP: $KEEP_COUNT/" "$RESULTS_FILE"
sed -i '' "s/- Services to SUSPEND: 0/- Services to SUSPEND: $SUSPEND_COUNT/" "$RESULTS_FILE"
sed -i '' "s/- Services to DELETE: 0/- Services to DELETE: $DELETE_COUNT/" "$RESULTS_FILE"
sed -i '' "s/- Estimated Monthly Savings: \\$0/- Estimated Monthly Savings: \\$$TOTAL_SAVINGS/" "$RESULTS_FILE"
sed -i '' "s/# Date: \$(date)/# Date: $(date '+%Y-%m-%d %H:%M:%S')/" "$RESULTS_FILE"

# Final summary
echo ""
echo "${CYAN}╔══════════════════════════════════════════════════════════════════╗${RESET}"
echo "${CYAN}║  Assessment Complete!                                           ║${RESET}"
echo "${CYAN}╚══════════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo "${GREEN}Summary:${RESET}"
echo "  Total Services Assessed: $SERVICE_COUNT"
echo "  ${GREEN}To KEEP:${RESET} $KEEP_COUNT"
echo "  ${YELLOW}To SUSPEND:${RESET} $SUSPEND_COUNT"
echo "  ${RED}To DELETE:${RESET} $DELETE_COUNT"
echo "  ${CYAN}Estimated Monthly Savings:${RESET} \$$TOTAL_SAVINGS"
echo ""
echo "${CYAN}Results saved to:${RESET}"
echo "  - Detailed: $RESULTS_FILE"
echo "  - Table format: $ASSESSMENT_FILE"
echo ""
echo "${YELLOW}Next Steps:${RESET}"
echo "  1. Review results in: $RESULTS_FILE"
echo "  2. Extract data from services you plan to delete"
echo "  3. Take action in Render dashboard"
echo ""


#!/bin/bash
# Quick setup script for AutoDS token

set -e

TOKEN="a2b1c3bf-d143-4516-905f-cf4bcf365dc0"
SECRETS_FILE="$HOME/.neolight_secrets_template"

echo "🔑 Setting up AutoDS token..."
echo ""

# Check if file exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo "Creating $SECRETS_FILE..."
    touch "$SECRETS_FILE"
fi

# Check if token already exists
if grep -q "AUTODS_TOKEN" "$SECRETS_FILE"; then
    echo "⚠️  AUTODS_TOKEN already exists in $SECRETS_FILE"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove old token line
        sed -i.bak '/^export AUTODS_TOKEN=/d' "$SECRETS_FILE"
        echo "✅ Updated existing token"
    else
        echo "Keeping existing token"
        exit 0
    fi
fi

# Add token
echo "" >> "$SECRETS_FILE"
echo "# AutoDS Token (from AutoDS dashboard)" >> "$SECRETS_FILE"
echo "export AUTODS_TOKEN='$TOKEN'" >> "$SECRETS_FILE"
echo "" >> "$SECRETS_FILE"
echo "# Platform preference" >> "$SECRETS_FILE"
echo "export DROPSHIP_PLATFORM='ebay'" >> "$SECRETS_FILE"
echo "" >> "$SECRETS_FILE"
echo "# eBay account" >> "$SECRETS_FILE"
echo "export EBAY_USERNAME='seakin67'" >> "$SECRETS_FILE"

echo "✅ AutoDS token added to $SECRETS_FILE"
echo ""
echo "📋 Load environment variables:"
echo "   source $SECRETS_FILE"
echo ""
echo "🧪 Test connection:"
echo "   python3 agents/autods_integration.py"
echo ""
echo "🚀 Launch dropshipping:"
echo "   ./launch_dropshipping.sh"
echo ""


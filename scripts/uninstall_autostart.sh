#!/usr/bin/env bash
# Uninstall NeoLight Trading Agent Auto-Start Service
# Removes both launcher and watchdog services

set -euo pipefail

LAUNCHER_PLIST="com.neolight.trading.plist"
WATCHDOG_PLIST="com.neolight.trading.watchdog.plist"

LAUNCHER_DEST="$HOME/Library/LaunchAgents/$LAUNCHER_PLIST"
WATCHDOG_DEST="$HOME/Library/LaunchAgents/$WATCHDOG_PLIST"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  NeoLight Trading Agent Auto-Start Uninstaller${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════${NC}"
echo ""

# Unload watchdog service
if launchctl list | grep -q "com.neolight.trading.watchdog"; then
    echo -e "${YELLOW}🛑 Unloading watchdog service...${NC}"
    launchctl unload "$WATCHDOG_DEST" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✅ Watchdog unloaded${NC}"
else
    echo -e "${YELLOW}⚠️  Watchdog not currently loaded${NC}"
fi

# Unload launcher service
if launchctl list | grep -q "com.neolight.trading"; then
    echo -e "${YELLOW}🛑 Unloading launcher service...${NC}"
    launchctl unload "$LAUNCHER_DEST" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✅ Launcher unloaded${NC}"
else
    echo -e "${YELLOW}⚠️  Launcher not currently loaded${NC}"
fi

# Remove plist files
if [ -f "$WATCHDOG_DEST" ]; then
    echo -e "${YELLOW}🗑️  Removing watchdog plist...${NC}"
    rm -f "$WATCHDOG_DEST"
    echo -e "${GREEN}✅ Watchdog plist removed${NC}"
fi

if [ -f "$LAUNCHER_DEST" ]; then
    echo -e "${YELLOW}🗑️  Removing launcher plist...${NC}"
    rm -f "$LAUNCHER_DEST"
    echo -e "${GREEN}✅ Launcher plist removed${NC}"
fi

# Verify removal
if launchctl list | grep -q "com.neolight.trading"; then
    echo -e "${RED}❌ Services still running - manual intervention needed${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All services completely removed${NC}"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🗑️  Auto-start service uninstalled successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Note: This does NOT stop currently running trading components.${NC}"
echo -e "${YELLOW}To stop them manually:${NC}"
echo "  pkill -f 'smart_trader.py'"
echo "  pkill -f 'market_intelligence.py'"
echo "  pkill -f 'strategy_research.py'"
echo ""


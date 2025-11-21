#!/usr/bin/env bash
# Install NeoLight autostart on macOS using launchd
set -euo pipefail

ROOT="$HOME/neolight"
PLIST_NAME="com.neolight.guardian"
PLIST_FILE="$ROOT/$PLIST_NAME.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
LAUNCHD_PLIST="$LAUNCHD_DIR/$PLIST_NAME.plist"

echo "🚀 Installing NeoLight autostart..."

# Check if plist exists
if [[ ! -f "$PLIST_FILE" ]]; then
    echo "❌ Error: $PLIST_FILE not found"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCHD_DIR"

# Stop existing service if running
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "⏹️  Stopping existing service..."
    launchctl unload "$LAUNCHD_PLIST" 2>/dev/null || true
fi

# Copy plist to LaunchAgents
echo "📋 Copying plist to LaunchAgents..."
cp "$PLIST_FILE" "$LAUNCHD_PLIST"

# Update paths in plist to use actual home directory (expand ~)
sed -i '' "s|~/neolight|$HOME/neolight|g" "$LAUNCHD_PLIST"

# Load the service
echo "🔄 Loading service..."
launchctl load "$LAUNCHD_PLIST"

# Check status
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "✅ NeoLight autostart installed successfully!"
    echo ""
    echo "Service will start automatically on login."
    echo "To check status: launchctl list | grep $PLIST_NAME"
    echo "To stop: launchctl unload $LAUNCHD_PLIST"
    echo "To start manually: launchctl load $LAUNCHD_PLIST"
else
    echo "⚠️  Service loaded but may not be running yet. Check logs:"
    echo "   tail -f $ROOT/logs/guardian_launchd.log"
fi


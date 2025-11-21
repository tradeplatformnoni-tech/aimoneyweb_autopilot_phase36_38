#!/bin/bash
# Auto-install GitLens - Tries multiple methods

echo "============================================================"
echo "🔍 Auto-Installing GitLens Extension"
echo "============================================================"
echo ""

# Try VS Code
if [ -d "/Applications/Visual Studio Code.app" ]; then
    echo "📦 Trying VS Code..."
    /Applications/Visual\ Studio\ Code.app/Contents/Resources/app/bin/code --install-extension eamodio.gitlens 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ GitLens installed via VS Code!"
        echo ""
        echo "🎯 Next: Reload VS Code and open GitLens sidebar"
        exit 0
    fi
fi

# Try Cursor (VS Code fork)
if [ -d "/Applications/Cursor.app" ]; then
    echo "📦 Trying Cursor..."
    /Applications/Cursor.app/Contents/Resources/app/bin/code --install-extension eamodio.gitlens 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ GitLens installed via Cursor!"
        echo ""
        echo "🎯 Next: Reload Cursor and open GitLens sidebar"
        exit 0
    fi
fi

# Try if 'code' command exists
if command -v code &> /dev/null; then
    echo "📦 Trying 'code' command..."
    code --install-extension eamodio.gitlens 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ GitLens installed!"
        exit 0
    fi
fi

# If all fails, provide manual instructions
echo "⚠️  Automatic installation not possible"
echo ""
echo "Please install GitLens manually (takes 30 seconds):"
echo ""
echo "Method 1: VS Code UI (Recommended)"
echo "1. Open VS Code (or Cursor)"
echo "2. Press ⌘+Shift+X (Extensions)"
echo "3. Search: 'GitLens'"
echo "4. Click 'Install'"
echo ""
echo "Method 2: Enable CLI then run this script again"
echo "1. Open VS Code"
echo "2. Press ⌘+Shift+P"
echo "3. Type: 'Shell Command: Install code command in PATH'"
echo "4. Press Enter"
echo "5. Run this script again: ./auto_install_gitlens.sh"
echo ""
echo "After installation:"
echo "- Reload VS Code (⌘+R)"
echo "- Open GitLens (⌘+Shift+G or click GitLens icon)"
echo "- See GITLENS_WALKTHROUGH.md for full guide"


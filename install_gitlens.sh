#!/bin/bash
# Install GitLens Extension for VS Code

echo "============================================================"
echo "🔍 Installing GitLens Extension"
echo "============================================================"
echo ""

# Check if VS Code CLI is available
if ! command -v code &> /dev/null; then
    echo "⚠️  VS Code CLI not found in PATH"
    echo ""
    echo "Please install manually:"
    echo "1. Open VS Code"
    echo "2. Go to Extensions (⌘+Shift+X)"
    echo "3. Search for 'GitLens'"
    echo "4. Click Install"
    echo ""
    echo "Or add VS Code to PATH:"
    echo "1. Open VS Code"
    echo "2. Press ⌘+Shift+P"
    echo "3. Type 'Shell Command: Install code command in PATH'"
    echo "4. Press Enter"
    exit 1
fi

echo "📦 Installing GitLens extension..."
code --install-extension eamodio.gitlens

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ GitLens installed successfully!"
    echo ""
    echo "🎯 Next Steps:"
    echo "1. Reload VS Code (⌘+R or Ctrl+R)"
    echo "2. Open GitLens sidebar (click GitLens icon or press ⌘+Shift+G)"
    echo "3. Start exploring your repository!"
    echo ""
    echo "📚 Guide: See GITLENS_WALKTHROUGH.md for complete documentation"
else
    echo ""
    echo "⚠️  Installation may have failed"
    echo "Try manual installation in VS Code:"
    echo "1. Extensions (⌘+Shift+X)"
    echo "2. Search 'GitLens'"
    echo "3. Click Install"
fi

echo ""
echo "============================================================"


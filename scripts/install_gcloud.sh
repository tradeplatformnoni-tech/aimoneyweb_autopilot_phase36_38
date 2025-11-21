#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ NeoLight Google Cloud SDK Installer                               ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

echo "🔍 Checking Google Cloud SDK installation..."

# Check if gcloud is installed
if command -v gcloud &> /dev/null; then
    echo "✅ gcloud is already installed"
    gcloud --version | head -1
    exit 0
fi

# Check if Homebrew is available
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install Homebrew first:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "📦 Installing Google Cloud SDK via Homebrew..."
brew install --cask google-cloud-sdk

# Add to PATH if not already there
if ! echo "$PATH" | grep -q "google-cloud-sdk"; then
    echo "📝 Adding Google Cloud SDK to PATH..."
    if [[ "$SHELL" == *"zsh"* ]]; then
        echo 'export PATH="/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin:$PATH"' >> ~/.zshrc
        echo 'export PATH="/opt/homebrew/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin:$PATH"' >> ~/.zshrc
    elif [[ "$SHELL" == *"bash"* ]]; then
        echo 'export PATH="/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin:$PATH"' >> ~/.bash_profile
        echo 'export PATH="/opt/homebrew/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin:$PATH"' >> ~/.bash_profile
    fi
fi

# Reload shell config
if [[ "$SHELL" == *"zsh"* ]]; then
    source ~/.zshrc 2>/dev/null || true
elif [[ "$SHELL" == *"bash"* ]]; then
    source ~/.bash_profile 2>/dev/null || true
fi

# Verify installation
if command -v gcloud &> /dev/null; then
    echo "✅ Google Cloud SDK installed successfully!"
    gcloud --version | head -1
    echo ""
    echo "🔐 Next steps:"
    echo "   1. Run: gcloud auth login"
    echo "   2. Run: gcloud config set account tradeplatformnoni@gmail.com"
    echo "   3. Run: gcloud projects create neolight-hybrid --name=\"NeoLight Hybrid\""
    echo "   4. Run: gcloud config set project neolight-hybrid"
else
    echo "⚠️  Installation completed, but gcloud not in PATH"
    echo "   Try opening a new terminal or run:"
    echo "   source ~/.zshrc  # or source ~/.bash_profile"
fi

#!/usr/bin/env bash
# Uninstall Docker Desktop from macOS
# Safe uninstall - removes Docker Desktop completely

set -euo pipefail

echo "🐳 Docker Desktop Uninstaller"
echo ""

# Colors
red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    yellow "ℹ️  Docker is not installed"
    exit 0
fi

echo "⚠️  WARNING: This will completely remove Docker Desktop"
echo "   - All containers will be removed"
echo "   - All images will be removed"
echo "   - All Docker data will be deleted"
echo ""
echo "✅ Current active deployment (Render) doesn't use Docker"
echo "✅ All agents are running in cloud (Render)"
echo "✅ Docker is not needed for current deployment"
echo ""
echo "Do you want to continue? (yes/no)"
read -r response

if [[ ! "$response" =~ ^[Yy][Ee][Ss]$ ]]; then
    yellow "Cancelled"
    exit 0
fi

echo ""
yellow "Step 1: Stopping Docker Desktop..."
osascript -e 'quit app "Docker"' 2>/dev/null || true
sleep 3

echo ""
yellow "Step 2: Removing Docker Desktop application..."
if [ -d "/Applications/Docker.app" ]; then
    rm -rf /Applications/Docker.app
    green "  ✅ Removed Docker.app"
else
    yellow "  ℹ️  Docker.app not found"
fi

echo ""
yellow "Step 3: Removing Docker data..."
if [ -d "$HOME/Library/Containers/com.docker.docker" ]; then
    rm -rf "$HOME/Library/Containers/com.docker.docker"
    green "  ✅ Removed Docker containers data"
fi

if [ -d "$HOME/Library/Application Support/Docker" ]; then
    rm -rf "$HOME/Library/Application Support/Docker"
    green "  ✅ Removed Docker application support"
fi

if [ -d "$HOME/.docker" ]; then
    rm -rf "$HOME/.docker"
    green "  ✅ Removed Docker config"
fi

echo ""
yellow "Step 4: Removing Docker command-line tools..."
# Docker might be installed via Homebrew
if command -v brew &> /dev/null; then
    if brew list docker 2>/dev/null | grep -q docker; then
        brew uninstall docker 2>/dev/null || true
        green "  ✅ Removed Docker via Homebrew"
    fi
fi

# Remove from PATH (if in .zshrc or .bash_profile)
if [ -f "$HOME/.zshrc" ]; then
    sed -i '' '/docker/d' "$HOME/.zshrc" 2>/dev/null || true
fi

if [ -f "$HOME/.bash_profile" ]; then
    sed -i '' '/docker/d' "$HOME/.bash_profile" 2>/dev/null || true
fi

echo ""
green "✅ Docker Desktop uninstalled successfully!"
echo ""
yellow "ℹ️  Note:"
echo "   - Dockerfile files are kept for future reference"
echo "   - If you need Docker for Fly.io in future, reinstall:"
echo "     brew install --cask docker"
echo "   - Current Render deployment continues to work (doesn't use Docker)"
echo ""

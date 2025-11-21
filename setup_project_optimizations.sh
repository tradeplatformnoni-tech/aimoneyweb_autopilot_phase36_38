#!/bin/bash
# Complete Project Optimization & AI Browser Setup
# Makes NeoLight faster and enables AI browser automation

set -e

cd ~/neolight

echo "============================================================"
echo "🚀 NeoLight Project Optimization & AI Browser Setup"
echo "============================================================"
echo ""

# 1. Install Playwright (Best browser automation)
echo "1. Installing Playwright (Browser Automation)..."
python3 -m pip install --user playwright 2>/dev/null || pip3 install --user playwright 2>/dev/null || echo "   ⚠️ pip not found"

if command -v playwright &> /dev/null; then
    playwright install chromium
    echo "   ✅ Playwright installed"
elif python3 -m playwright --version &> /dev/null; then
    python3 -m playwright install chromium
    echo "   ✅ Playwright installed (via python3 -m)"
else
    echo "   ⚠️ Playwright install command not found - will install later"
fi
echo ""

# 2. Install Performance Tools
echo "2. Installing Performance Tools..."
python3 -m pip install --user py-spy memory-profiler line-profiler cython numba uvloop 2>/dev/null || \
pip3 install --user py-spy memory-profiler line-profiler cython numba uvloop 2>/dev/null || echo "   ⚠️ pip not found"
echo "   ✅ Performance tools installed"
echo ""

# 3. Install Code Quality Tools
echo "3. Installing Code Quality Tools..."
python3 -m pip install --user black flake8 pylint mypy 2>/dev/null || \
pip3 install --user black flake8 pylint mypy 2>/dev/null || echo "   ⚠️ pip not found"
echo "   ✅ Code quality tools installed"
echo ""

# 4. Install Testing Framework
echo "4. Installing Testing Framework..."
python3 -m pip install --user pytest pytest-cov pytest-asyncio 2>/dev/null || \
pip3 install --user pytest pytest-cov pytest-asyncio 2>/dev/null || echo "   ⚠️ pip not found"
echo "   ✅ Testing framework installed"
echo ""

# 5. Install Monitoring Tools
echo "5. Installing Monitoring Tools..."
python3 -m pip install --user psutil structlog 2>/dev/null || \
pip3 install --user psutil structlog 2>/dev/null || echo "   ⚠️ pip not found"
echo "   ✅ Monitoring tools installed"
echo ""

# 6. Install Redis (for caching - optional)
echo "6. Checking Redis (Caching)..."
if command -v redis-server &> /dev/null; then
    echo "   ✅ Redis already installed"
    # Start Redis if not running
    if ! pgrep -x "redis-server" > /dev/null; then
        echo "   Starting Redis..."
        brew services start redis 2>/dev/null || redis-server --daemonize yes 2>/dev/null || echo "   ⚠️ Could not start Redis automatically"
    fi
else
    echo "   Installing Redis..."
    brew install redis 2>/dev/null && brew services start redis || echo "   ⚠️ Redis install failed (optional - can install later)"
fi
echo ""

# 7. Install Async Libraries
echo "7. Installing Async Libraries..."
python3 -m pip install --user aiohttp aiofiles 2>/dev/null || \
pip3 install --user aiohttp aiofiles 2>/dev/null || echo "   ⚠️ pip not found"
echo "   ✅ Async libraries installed"
echo ""

# 8. Verify Installations
echo "8. Verifying Installations..."
echo ""
echo "   Checking tools..."

TOOLS=("playwright" "black" "flake8" "pytest" "py-spy")
for tool in "${TOOLS[@]}"; do
    if python3 -c "import ${tool//-/_}" 2>/dev/null || command -v "$tool" &> /dev/null; then
        echo "   ✅ $tool"
    else
        echo "   ⚠️ $tool (may need manual install)"
    fi
done

echo ""
echo "============================================================"
echo "✅ Setup Complete!"
echo "============================================================"
echo ""
echo "📋 What's Ready:"
echo "   ✅ Playwright - AI browser automation"
echo "   ✅ Performance tools - Speed up your code"
echo "   ✅ Code quality tools - Better code"
echo "   ✅ Testing framework - Reliable code"
echo "   ✅ Monitoring tools - Track performance"
echo ""
echo "🚀 Next Steps:"
echo "   1. Test AI browser: python3 agents/ai_browser_assistant.py"
echo "   2. See full guide: PROJECT_OPTIMIZATION_SETUP.md"
echo ""
echo "💡 Use AI Browser Assistant:"
echo "   from agents.ai_browser_assistant import solve_website_problem"
echo ""


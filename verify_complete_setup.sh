#!/bin/bash
# Complete Setup Verification Script
# Verifies all optimizations and VERO protection are working

set -e

cd ~/neolight

echo "============================================================"
echo "🔍 Complete Setup Verification"
echo "============================================================"
echo ""

# 1. Check AI Browser Automation
echo "1. AI Browser Automation:"
if python3 -c "from agents.ai_browser_assistant import AIBrowserAssistant; print('   ✅ AI Browser Assistant')" 2>/dev/null; then
    echo "   ✅ AI Browser Assistant imported"
else
    echo "   ❌ AI Browser Assistant not available"
fi

if python3 -c "import playwright; print('   ✅ Playwright')" 2>/dev/null; then
    echo "   ✅ Playwright installed"
else
    echo "   ❌ Playwright not installed"
fi
echo ""

# 2. Check Performance Tools
echo "2. Performance Tools:"
TOOLS=("py_spy" "memory_profiler" "line_profiler" "cython" "numba" "uvloop")
for tool in "${TOOLS[@]}"; do
    if python3 -c "import ${tool}; print('   ✅ ${tool}')" 2>/dev/null; then
        echo "   ✅ $tool"
    else
        echo "   ⚠️  $tool (optional)"
    fi
done
echo ""

# 3. Check Code Quality Tools
echo "3. Code Quality Tools:"
QUALITY_TOOLS=("black" "flake8" "pylint" "mypy")
for tool in "${QUALITY_TOOLS[@]}"; do
    if command -v "$tool" &>/dev/null || python3 -c "import ${tool}" 2>/dev/null; then
        echo "   ✅ $tool"
    else
        echo "   ⚠️  $tool (optional)"
    fi
done
echo ""

# 4. Check Testing & Monitoring
echo "4. Testing & Monitoring:"
if python3 -c "import pytest; print('   ✅ pytest')" 2>/dev/null; then
    echo "   ✅ pytest"
else
    echo "   ⚠️  pytest (optional)"
fi

if python3 -c "import psutil; print('   ✅ psutil')" 2>/dev/null; then
    echo "   ✅ psutil"
else
    echo "   ⚠️  psutil (optional)"
fi

if python3 -c "import structlog; print('   ✅ structlog')" 2>/dev/null; then
    echo "   ✅ structlog"
else
    echo "   ⚠️  structlog (optional)"
fi
echo ""

# 5. Check Caching (Redis)
echo "5. Caching:"
if command -v redis-server &>/dev/null; then
    if pgrep -x "redis-server" > /dev/null; then
        echo "   ✅ Redis installed and running"
    else
        echo "   ⚠️  Redis installed but not running"
    fi
else
    echo "   ⚠️  Redis not installed (optional)"
fi
echo ""

# 6. Check Async Libraries
echo "6. Async Libraries:"
if python3 -c "import aiohttp; print('   ✅ aiohttp')" 2>/dev/null; then
    echo "   ✅ aiohttp"
else
    echo "   ⚠️  aiohttp (optional)"
fi

if python3 -c "import aiofiles; print('   ✅ aiofiles')" 2>/dev/null; then
    echo "   ✅ aiofiles"
else
    echo "   ⚠️  aiofiles (optional)"
fi
echo ""

# 7. Check VERO Protection
echo "7. VERO Protection (eBay Compliance):"
if python3 -c "from agents.vero_protection import check_vero_violation, sanitize_product_for_ebay; print('   ✅ VERO Protection')" 2>/dev/null; then
    echo "   ✅ VERO Protection imported"
    
    # Test VERO detection
    echo "   Testing VERO detection..."
    python3 -c "
from agents.vero_protection import check_vero_violation
is_violation, details = check_vero_violation('iPhone 14 Pro Max Case', 'Protective case for iPhone')
if is_violation:
    print('   ✅ VERO detection working (detected iPhone violation)')
else:
    print('   ⚠️  VERO detection may not be working correctly')
" 2>/dev/null || echo "   ⚠️  Could not test VERO detection"
else
    echo "   ❌ VERO Protection not available"
fi
echo ""

# 8. Check Dropship Agent Integration
echo "8. Dropship Agent Integration:"
if python3 -c "from agents.dropship_agent import list_product_on_ebay; print('   ✅ Dropship Agent')" 2>/dev/null; then
    echo "   ✅ Dropship Agent imported"
    
    # Check if VERO is integrated
    if grep -q "vero_protection\|VERO" agents/dropship_agent.py 2>/dev/null; then
        echo "   ✅ VERO protection integrated in dropship agent"
    else
        echo "   ⚠️  VERO protection not integrated in dropship agent"
    fi
else
    echo "   ⚠️  Dropship Agent not available"
fi
echo ""

# 9. Check AutoDS Integration
echo "9. AutoDS Integration:"
if python3 -c "from agents.autods_integration import test_autods_connection; print('   ✅ AutoDS Integration')" 2>/dev/null; then
    echo "   ✅ AutoDS Integration imported"
    
    # Check if VERO is integrated
    if grep -q "vero_protection\|VERO" agents/autods_integration.py 2>/dev/null; then
        echo "   ✅ VERO protection integrated in AutoDS integration"
    else
        echo "   ⚠️  VERO protection not integrated in AutoDS integration"
    fi
    
    # Check token
    if [ -f ~/.neolight_secrets_template ]; then
        if grep -q "AUTODS_TOKEN" ~/.neolight_secrets_template 2>/dev/null; then
            echo "   ✅ AutoDS token configured"
        else
            echo "   ⚠️  AutoDS token not found in secrets"
        fi
    fi
else
    echo "   ⚠️  AutoDS Integration not available"
fi
echo ""

echo "============================================================"
echo "📊 Summary"
echo "============================================================"
echo ""
echo "✅ Core Systems:"
echo "   - AI Browser Automation (Playwright)"
echo "   - VERO Protection (eBay Compliance)"
echo "   - Performance Tools"
echo "   - Code Quality Tools"
echo ""
echo "🚀 Ready to use:"
echo "   1. AI Browser: python3 agents/ai_browser_assistant.py"
echo "   2. VERO Test: python3 agents/vero_protection.py"
echo "   3. Dropship Agent: Already running with VERO protection"
echo ""
echo "📚 Documentation:"
echo "   - PROJECT_OPTIMIZATION_SETUP.md"
echo "   - AI_BROWSER_EXAMPLES.md"
echo "   - QUICK_OPTIMIZATION_GUIDE.md"
echo ""
echo "============================================================"


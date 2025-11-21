#!/bin/bash
# Check installed development tools

echo "🔍 NeoLight Development Tools Status"
echo "====================================="
echo ""

echo "📦 AI SDKs:"
python3 -m pip show openai anthropic mistralai google-generativeai groq 2>/dev/null | grep -E "^Name:" | sed 's/^/  ✅ /' || echo "  ❌ Not installed"

echo ""
echo "🔧 Code Quality:"
python3 -m pip show mypy black ruff pylint flake8 bandit 2>/dev/null | grep -E "^Name:" | sed 's/^/  ✅ /' || echo "  ❌ Not installed"

echo ""
echo "🧪 Testing:"
python3 -m pip show pytest pytest-cov pytest-asyncio 2>/dev/null | grep -E "^Name:" | sed 's/^/  ✅ /' || echo "  ❌ Not installed"

echo ""
echo "⚡ Performance:"
python3 -m pip show memory-profiler line-profiler py-spy pyinstrument 2>/dev/null | grep -E "^Name:" | sed 's/^/  ✅ /' || echo "  ❌ Not installed"

echo ""
echo "💻 Development:"
python3 -m pip show ipython rich typer 2>/dev/null | grep -E "^Name:" | sed 's/^/  ✅ /' || echo "  ❌ Not installed"

echo ""
echo "📊 Data Tools:"
python3 -m pip show pandas numpy scipy 2>/dev/null | grep -E "^Name:" | sed 's/^/  ✅ /' || echo "  ❌ Not installed"

echo ""


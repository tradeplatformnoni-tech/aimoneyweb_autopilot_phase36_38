#!/usr/bin/env bash
# NeoLight Cloud Independence Audit Script
# Finds remaining localhost dependencies and missing RENDER_MODE checks

set -e

ROOT_DIR="${1:-$(pwd)}"
cd "$ROOT_DIR"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  NeoLight Cloud Independence Audit                              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

ERRORS=0
WARNINGS=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}❌ ERROR:${NC} $1"
    ERRORS=$((ERRORS + 1))
}

warn() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

success() {
    echo -e "${GREEN}✅${NC} $1"
}

# ============================================================================
# CHECK 1: Search for localhost references
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 1: Searching for localhost references..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

LOCALHOST_REFS=$(grep -rn "localhost" agents/ trader/ execution/ --include="*.py" 2>/dev/null | \
    grep -v ".pyc" | \
    grep -v "backup" | \
    grep -v "#" | \
    grep -v "if not RENDER_MODE" | \
    grep -v "RENDER_MODE" | \
    grep -v "if not.*RENDER_MODE" || true)

if [ -z "$LOCALHOST_REFS" ]; then
    success "No unguarded localhost references found"
else
    error "Found localhost references without RENDER_MODE guard:"
    echo "$LOCALHOST_REFS"
    echo ""
fi

# ============================================================================
# CHECK 2: Search for hardcoded HTTP calls
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 2: Searching for hardcoded HTTP calls..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

HTTP_REFS=$(grep -rn "http://" agents/ trader/ execution/ --include="*.py" 2>/dev/null | \
    grep -v ".pyc" | \
    grep -v "backup" | \
    grep -v "https://api." | \
    grep -v "https://www." | \
    grep -v "#" || true)

if [ -z "$HTTP_REFS" ]; then
    success "No hardcoded HTTP calls found"
else
    warn "Found potential hardcoded HTTP calls (review manually):"
    echo "$HTTP_REFS" | head -10
    echo ""
fi

# ============================================================================
# CHECK 3: Files WITHOUT RENDER_MODE check
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 3: Files missing RENDER_MODE detection..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MISSING_RENDER_MODE=0

for file in agents/*.py trader/*.py execution/*.py; do
    if [ -f "$file" ]; then
        if ! grep -q "RENDER_MODE" "$file"; then
            error "Missing RENDER_MODE: $file"
            MISSING_RENDER_MODE=$((MISSING_RENDER_MODE + 1))
        fi
    fi
done

if [ $MISSING_RENDER_MODE -eq 0 ]; then
    success "All agent files have RENDER_MODE detection"
fi

# ============================================================================
# CHECK 4: Files WITH RENDER_MODE check
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 4: Files WITH RENDER_MODE detection..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RENDER_MODE_FILES=$(grep -l "RENDER_MODE" agents/*.py trader/*.py execution/*.py 2>/dev/null || true)

if [ -n "$RENDER_MODE_FILES" ]; then
    echo "$RENDER_MODE_FILES" | while read -r file; do
        success "$(basename "$file")"
    done
else
    warn "No files found with RENDER_MODE detection"
fi

# ============================================================================
# CHECK 5: QuoteService offline mode verification
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 5: QuoteService offline mode verification..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "trader/quote_service.py" ]; then
    if grep -q "use_stale_cache" trader/quote_service.py; then
        success "QuoteService has use_stale_cache parameter"
    else
        error "QuoteService missing use_stale_cache parameter"
    fi

    if grep -q "OFFLINE MODE" trader/quote_service.py || grep -q "offline mode" trader/quote_service.py; then
        success "QuoteService has offline mode logging"
    else
        warn "QuoteService missing offline mode logging"
    fi
else
    error "trader/quote_service.py not found"
fi

# ============================================================================
# CHECK 6: External API timeout handling
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CHECK 6: External API timeout handling..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for requests.get/post calls without timeout
NO_TIMEOUT=$(grep -rn "requests\.\(get\|post\)" agents/ trader/ --include="*.py" 2>/dev/null | \
    grep -v "timeout=" | \
    grep -v ".pyc" | \
    grep -v "backup" || true)

if [ -z "$NO_TIMEOUT" ]; then
    success "All API calls appear to have timeout handling"
else
    warn "Found API calls without explicit timeout (review manually):"
    echo "$NO_TIMEOUT" | head -10
    echo ""
fi

# ============================================================================
# SUMMARY
# ============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Audit Summary                                                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    success "All checks passed! System is cloud-independent ✅"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    warn "Found $WARNINGS warning(s) - review recommended"
    exit 0
else
    error "Found $ERRORS error(s) and $WARNINGS warning(s)"
    echo ""
    echo "Next steps:"
    echo "1. Fix localhost references (add RENDER_MODE guards)"
    echo "2. Add RENDER_MODE detection to missing files"
    echo "3. Verify QuoteService offline mode"
    exit 1
fi

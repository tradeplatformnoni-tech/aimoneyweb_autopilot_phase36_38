# Offline Agent Failures & Cloud Deployment - Problem Statement for Claude 4.5

## 🎯 System Overview

**NeoLight** is a fully autonomous, self-healing trading research + execution mesh designed to operate 24/7 in the cloud without requiring local WiFi connectivity.

### Current Architecture

- **Primary Deployment**: Render cloud (`https://neolight-autopilot-python.onrender.com`)
- **Backup Deployment**: Google Cloud Run (`neolight-failover` service in `us-central1` region)
- **CDN/Proxy**: Cloudflare Workers (proxies requests to Google Cloud Run with API key auth)
- **Local System**: macOS development environment (backup only)
- **Communication**: File-based state sharing (`~/neolight/state/`, `~/neolight/runtime/`)
- **State Sync**: Google Drive via rclone + Google Cloud Storage bucket (when configured)

### Core Agents (8 total)

1. `intelligence_orchestrator.py` - Brain/orchestrator (generates risk_scaler, confidence)
2. `smart_trader.py` - Main trading loop (paper trading)
3. `ml_pipeline.py` - Auto-trains ML models every 6 hours
4. `strategy_research.py` - Ranks and optimizes trading strategies
5. `market_intelligence.py` - Multi-source sentiment analysis (Reddit, Twitter, News)
6. `sports_analytics_agent.py` - Sports betting predictions
7. `sports_betting_agent.py` - Paper trading for sports bets
8. `dropship_agent.py` - Multi-platform dropshipping automation

---

## ⚠️ Problem Statement

### Primary Issue

**When the local machine goes offline (WiFi disconnected), the system fails despite being deployed to Render cloud.**

### Expected Behavior

- System should operate **100% independently** in Render cloud
- Local WiFi disconnection should have **zero impact** on cloud operations
- Cloud agents should continue running and processing without any local dependencies
- All communication should be file-based or via Render's internal network (no localhost)

### Actual Behavior

- System fails when local machine goes offline
- Errors related to localhost connections
- Circuit breakers open due to network failures
- Agents stop processing when offline

---

## 🔍 Root Causes Identified

### 1. Localhost Dependencies (✅ All Fixed)

**Status**: All fixed - comprehensive RENDER_MODE detection added to all agents

**Fixed Files**:

- ✅ `execution/router.py` - Has `RENDER_MODE` detection, skips localhost when `RENDER_MODE=true`
- ✅ `agents/phase_5700_5900_capital_governor.py` - Has `RENDER_MODE` detection, skips dashboard on Render
- ✅ `agents/phase_5600_hive_telemetry.py` - Has `RENDER_MODE` detection
- ✅ `agents/atlas_bridge.py` - Has `RENDER_MODE` detection
- ✅ `trader/smart_trader.py` - **JUST FIXED**: Added `RENDER_MODE` detection, skips dashboard on Render (line 1346)

**Remaining Issues**:

- ✅ **All localhost dependencies fixed!** (trader/smart_trader.py was the last one)

**Files with RENDER_MODE Detection Pattern**:

```python
RENDER_MODE = os.getenv("RENDER_MODE", "false").lower() == "true"
DASHBOARD_URL = os.getenv(
    "NEOLIGHT_DASHBOARD_URL",
    "http://localhost:8100" if not RENDER_MODE else None
)
# Then skip dashboard calls when RENDER_MODE is True
```

---

### 2. QuoteService Circuit Breaker (Fixed, Needs Verification)

**File**: `trader/quote_service.py`

**Problem**: When offline, `QuoteService` attempts to fetch quotes from external APIs (Alpaca, Finnhub, TwelveData, AlphaVantage, RapidAPI, Yahoo). All API calls fail when offline. After 5 failures, the circuit breaker opens, stopping the system.

**Fix Implemented**:

- Added `use_stale_cache=True` parameter to `get_quote()` method
- Modified cache checking to return stale cache when offline
- Updated `trader/smart_trader.py` to pass `use_stale_cache=True` and handle stale cache gracefully

**Code Changes**:

```python
# trader/quote_service.py - get_quote method
def get_quote(self, symbol: str, max_age: int = 60, use_stale_cache: bool = True) -> Optional[ValidatedQuote]:
    """
    Get validated quote (cached or fresh).

    Args:
        use_stale_cache: If True, use stale cache when offline (network failures)
    """
    # Check cache first (even if stale, useful when offline)
    with self._lock:
        cached = self._cache.get(symbol)
        if cached:
            if not cached.is_stale(max_age):
                return cached  # Fresh cache
            elif use_stale_cache:
                # Stale but available - use it when offline
                logger.debug(f"📦 Using stale cache for {symbol} (offline mode)")
                return cached

    # Try to fetch fresh (will fail gracefully if offline)
    fresh_quote = self._fetch_fresh(symbol)
    if fresh_quote:
        return fresh_quote

    # If fetch failed and we have stale cache, return it (offline mode)
    if use_stale_cache and cached:
        age_seconds = cached.age_seconds
        logger.debug(f"🌐 Offline: Using stale cache for {symbol} (age: {age_seconds:.0f}s)")
        return cached

    return None
```

**Issue**: Need to verify this fix is actually in the codebase and working correctly.

---

### 3. External API Dependencies (Graceful Degradation Needed)

**External APIs Used**:

- **Alpaca** (`https://api.alpaca.markets`) - Primary quote source
- **Finnhub** (`https://finnhub.io/api/v1`) - Secondary quote source
- **TwelveData** (`https://api.twelvedata.com`) - Tertiary quote source
- **AlphaVantage** (`https://www.alphavantage.co/query`) - Quaternary quote source
- **RapidAPI** (`https://alpha-vantage.p.rapidapi.com`) - Quinary quote source (for indexes/funds)
- **Yahoo Finance** (via yfinance library) - Final fallback
- **Telegram API** (`https://api.telegram.org`) - Notifications
- **ESPN** (web scraping) - Sports data
- **Reddit API** - Market intelligence
- **Twitter API** - Market intelligence
- **NewsAPI** - Market intelligence

**Expected Behavior**:

- All API calls should have proper timeout handling (5-10 seconds max)
- All API failures should be caught and logged gracefully
- System should continue operating with cached/stale data when APIs fail
- Circuit breakers should NOT open for temporary network issues when cache is available

**Current Implementation**:

- `QuoteService` has cascading fallback (Alpaca → Finnhub → TwelveData → AlphaVantage → RapidAPI → Yahoo)
- Cache mechanism exists but may not be used correctly when offline
- Circuit breaker may open prematurely when network fails

---

### 4. RENDER_MODE Environment Variable

**Current Status**:

- Render cloud sets `RENDER_MODE=true` environment variable
- Some agents check this, some don't
- Need comprehensive audit of all agents

**Environment Variables in Render**:

```bash
RENDER_MODE=true
TRADING_MODE=PAPER_TRADING_MODE
PYTHONPATH=/opt/render/project/src
```

**Expected Pattern**:
All agents should check `RENDER_MODE` and:

1. Skip localhost connections when `RENDER_MODE=true`
2. Use Render paths (`/opt/render/project/src`) instead of local paths (`~/neolight`)
3. Skip dashboard pushes/pulls when on Render (file-based communication instead)
4. Use environment variables for service URLs instead of hardcoded localhost

---

## 📋 Files to Review/Fix

### High Priority (Critical for Offline Operation)

1. ✅ **`trader/smart_trader.py`** - **FIXED**: Added `RENDER_MODE` detection, skips dashboard on Render

2. **`trader/quote_service.py`**
   - Verify `use_stale_cache` implementation is correct
   - Ensure circuit breaker doesn't open when using stale cache

3. **All agent files** (8 agents listed above)
   - Audit for localhost references
   - Ensure all have `RENDER_MODE` detection
   - Ensure all use environment variables for URLs

### Medium Priority (Enhancement)

4. **External API call handlers**
   - Add comprehensive timeout handling
   - Ensure graceful degradation with cache
   - Prevent circuit breaker from opening unnecessarily

5. **Error handling and logging**
   - Improve offline mode error messages
   - Add clear indicators when operating in offline/cached mode

---

## 🔧 Implementation Details

### Render Deployment Configuration (Primary)

**File**: `render_app_multi_agent.py`

**Key Features**:

- FastAPI app runs on port 8080 (Render default)
- All agents run in background threads
- Health endpoint at `/health`
- Agent status at `/agents` and `/agents/{agent_name}`

**Agent Startup**:

```python
# Agents defined in AGENTS dictionary
AGENTS = {
    "intelligence_orchestrator": {
        "script": ROOT / "agents" / "intelligence_orchestrator.py",
        "priority": 1,
        "required": True,
    },
    # ... other agents
}
```

**State Directory**:

- Render: `/opt/render/project/src/state/`
- Local: `~/neolight/state/`

### Google Cloud Run Deployment Configuration (Backup)

**File**: `cloud-run/app.py`

**Key Features**:

- FastAPI supervisor with API key authentication
- Circuit breaker pattern (prevents activation spam)
- Multi-endpoint health checks
- Process output streaming
- Graceful shutdown handling
- State sync from Google Cloud Storage bucket on startup

**Deployment**:

- **Build**: `cloud-run/cloudbuild.yaml` (Cloud Build)
- **Dockerfile**: `cloud-run/Dockerfile`
- **Image**: `gcr.io/$PROJECT_ID/neolight-failover:latest`
- **Region**: `us-central1` (Chicago)
- **Scaling**: Min 0, Max 1 (standby mode, activates on failover)

**State Sync**:

- Reads from Google Cloud Storage bucket (`NL_BUCKET`)
- Syncs state files via `cloud-run/sync-state.sh` on startup
- Uses `gsutil` to sync `state/` and `runtime/` directories

**Security**:

- API key authentication via `X-API-Key` header
- API key stored in Secret Manager
- Circuit breaker prevents excessive activations

### Cloudflare Workers Configuration (CDN/Proxy)

**Files**: `cloudflare_worker_*.js`, `CLOUDFLARE_SETUP_GUIDE.md`

**Purpose**:

- Proxies requests to Google Cloud Run service
- Injects API key header automatically
- Adds CDN layer for better performance
- Handles request forwarding with proper headers

**Features**:

- Automatic API key injection (from environment variables)
- Request forwarding to Cloud Run URL
- IP forwarding (`X-Forwarded-For`, `X-Real-IP`)
- Error handling and retries

### File-Based Communication

**Agent Communication Pattern**:

1. Intelligence Orchestrator writes to `runtime/atlas_brain.json`
2. SmartTrader reads from `state/pnl_history.csv` and writes trades
3. Atlas Bridge reads from `runtime/atlas_brain.json` (file-based, not HTTP)
4. All agents read/write to shared state files

**No HTTP Required**: Agents communicate via files, not localhost HTTP endpoints.

---

## ✅ What's Working

### Already Fixed

1. ✅ `execution/router.py` - Has `RENDER_MODE` detection
2. ✅ `agents/phase_5700_5900_capital_governor.py` - Has `RENDER_MODE` detection
3. ✅ `agents/phase_5600_hive_telemetry.py` - Has `RENDER_MODE` detection
4. ✅ `agents/atlas_bridge.py` - Has `RENDER_MODE` detection
5. ✅ QuoteService offline mode support (needs verification)

### Render Deployment (Primary)

- ✅ Render app is configured and deployed
- ✅ Health endpoint responds: `curl https://neolight-autopilot-python.onrender.com/health`
- ✅ Agents are configured to run in background threads
- ✅ File-based state sharing works

### Google Cloud Run Deployment (Backup)

- ✅ Cloud Run service configured (`neolight-failover`)
- ✅ Docker image builds successfully (`cloud-run/Dockerfile`)
- ✅ Cloud Build pipeline configured (`cloud-run/cloudbuild.yaml`)
- ✅ State bucket configured (Google Cloud Storage)
- ✅ API key stored in Secret Manager
- ✅ Standby mode (scales to 0 when not needed)

### Cloudflare Configuration

- ✅ Cloudflare Workers configured for proxying
- ✅ API key injection working
- ✅ Request forwarding to Cloud Run service

---

## 🎯 Goal

**Achieve 100% cloud independence**: The system should operate completely in Render cloud without any local dependencies. When local WiFi is disconnected, cloud agents should continue running flawlessly using:

1. Cached data when external APIs are unavailable
2. File-based communication (no localhost HTTP calls)
3. Graceful degradation for all external dependencies
4. Proper `RENDER_MODE` detection across all components

---

## 🔍 Questions for Claude 4.5

1. **Comprehensive Audit**: Can you audit all agent files and identify any remaining localhost dependencies or missing `RENDER_MODE` checks?

2. **QuoteService Fix Verification**: Can you verify the `use_stale_cache` implementation in `trader/quote_service.py` is correct and that the circuit breaker logic properly handles offline mode?

3. **Best Practices**: What are the best practices for ensuring cloud-first architecture with graceful offline degradation?

4. **Circuit Breaker Logic**: How should circuit breakers behave when cache is available? Should they remain closed when using stale cache, or open only when both fresh fetch AND cache are unavailable?

5. **Testing Strategy**: How can we test offline behavior in Render cloud environment? (Since Render itself requires internet, how do we simulate offline conditions?)

6. **Agent Communication**: Are there any remaining HTTP dependencies between agents that should be converted to file-based communication?

---

## 📊 Current System State

### Render Cloud Status (Primary)

- **URL**: `https://neolight-autopilot-python.onrender.com`
- **Health Endpoint**: `/health`
- **Agents Endpoint**: `/agents`
- **Status**: ✅ Deployed and running

### Google Cloud Run Status (Backup/Failover)

- **Service**: `neolight-failover`
- **Region**: `us-central1` (Chicago)
- **Image**: `gcr.io/$PROJECT_ID/neolight-failover:latest`
- **State Bucket**: Google Cloud Storage bucket (configured via `NL_BUCKET`)
- **Status**: ✅ Configured (standby mode, scales to 0 when not needed)
- **Activation**: Automatic failover when Render/local fails
- **File**: `cloud-run/app.py` - FastAPI supervisor with API key auth

### Cloudflare Configuration (CDN/Proxy)

- **Workers & Pages**: Cloudflare Workers proxy requests to Google Cloud Run
- **Purpose**: Adds CDN layer, API key injection, and request forwarding
- **Status**: ✅ Configured (see `CLOUDFLARE_SETUP_GUIDE.md`)
- **Files**: `cloudflare_worker_*.js`, `scripts/auto_deploy_cloudflare.py`

### Local System Status

- **Path**: `~/neolight/`
- **State Dir**: `~/neolight/state/`
- **Runtime Dir**: `~/neolight/runtime/`
- **Status**: ⚠️ Should only be backup, not primary

### Environment Variables

**Render (Primary)**:

```bash
RENDER_MODE=true
TRADING_MODE=PAPER_TRADING_MODE
PYTHONPATH=/opt/render/project/src
PORT=8080
```

**Google Cloud Run (Backup)**:

```bash
TRADING_MODE=PAPER_TRADING_MODE
REQUIRE_AUTH=true
NL_BUCKET=gs://neolight-state-<timestamp>
CLOUD_RUN_API_KEY=<stored in Secret Manager>
```

---

## 📝 Additional Context

### Project Structure

```
neolight/
├── agents/                    # All agent scripts
│   ├── intelligence_orchestrator.py
│   ├── ml_pipeline.py
│   └── ...
├── trader/                    # Trading execution
│   ├── smart_trader.py        # Main trading loop
│   └── quote_service.py       # Quote fetching with cache
├── execution/                 # Execution routing
│   └── router.py              # Risk engine routing
├── cloud-run/                 # Google Cloud Run deployment
│   ├── app.py                 # FastAPI supervisor (backup)
│   ├── Dockerfile             # Container image
│   ├── cloudbuild.yaml        # Cloud Build configuration
│   └── sync-state.sh          # State sync script
├── cloudflare_worker_*.js     # Cloudflare Workers scripts
├── scripts/
│   └── auto_deploy_cloudflare.py  # Cloudflare deployment
├── state/                     # Shared state files
├── runtime/                   # Runtime state (atlas_brain.json)
├── logs/                      # Log files
├── render_app_multi_agent.py  # Render FastAPI app (primary)
└── CLOUDFLARE_SETUP_GUIDE.md  # Cloudflare setup instructions
```

### Technology Stack

- **Python 3.12+**
- **FastAPI** (Render and Cloud Run web services)
- **Circuit Breaker Pattern** (utils/circuit_breaker.py)
- **File-based state** (JSON, CSV files)
- **Google Cloud Storage** (state bucket for Cloud Run backup)
- **Cloudflare Workers** (JavaScript runtime for CDN/proxy)
- **Multi-source quote fetching** (Alpaca, Finnhub, etc.)
- **Containerization** (Docker for Cloud Run deployment)

---

## 🚀 Next Steps Request

1. **Complete Audit**: Identify all remaining localhost dependencies and missing `RENDER_MODE` checks
2. **Fix Remaining Issues**: Fix `trader/smart_trader.py` and any other files with localhost references
3. **Verify QuoteService**: Ensure offline mode works correctly with circuit breaker
4. **Comprehensive Testing**: Provide testing strategy for offline behavior
5. **Documentation**: Document the offline/cloud-first architecture pattern

---

**End of Problem Statement**

*This document contains all the details needed to diagnose and fix offline agent failures and ensure 100% cloud independence.*

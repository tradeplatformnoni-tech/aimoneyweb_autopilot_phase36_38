# NeoLight Wealth Mesh — Unified Architecture 🔥⚡️💫

## Mission Statement
Fully autonomous, self-healing trading research + execution mesh with live telemetry, idempotent guardians, and ROI-phased growth targeting $1M in 2 years through a **multi-agent, multi-sector ecosystem** spanning trading, arbitrage, e-commerce, sports, collectibles, luxury goods, content creation, and healthcare AI.

## Core Architecture Layers

| Layer | Technology | Function |
|--------|-------------|----------|
| Application | FastAPI + React | Live trading dashboard & multi-agent monitoring |
| Intelligence | Python + Go + Reinforcement Learning | AI trading, prediction, and evolution |
| Containerization | Docker / Kubernetes | Distributed orchestration |
| CI/CD | GitHub Actions + Argo CD | Automated build + deploy |
| Monitoring | Prometheus + Grafana + Loki | Metrics + logs |
| Healing | AutoFix + AutoPatch + Guardian AI | Self-repair & rollback |
| Data Integration | Atlas API Layer | External market & macro data fusion |
| Strategy | Capital Governor + Hedge Engine | Smart reallocation + protection |

---

## Core Trading Agents (Foundation Layer)

### 1. Intelligence Orchestrator (`agents/intelligence_orchestrator.py`)
- **Purpose**: Central heartbeat service that coordinates system-wide intelligence signals across ALL agents
- **Outputs**: 
  - `runtime/atlas_brain.json` — risk_scaler (0.4-1.2) and confidence (0.05-0.9)
  - `state/intelligence_summary.json` — lightweight summary for dashboard
- **Interval**: Configurable via `NEOLIGHT_ORCH_INTERVAL` (default: 300s, tuned: 120s)
- **Behavior**: Long-running service loop; never exits unless fatal error
- **Integration**: Drives risk scaling for trading, betting, arbitrage, and e-commerce agents

### 2. Weights Bridge (`agents/weights_bridge.py`)
- **Purpose**: Normalizes Strategy Lab outputs into trader-consumable allocations
- **Inputs**: `runtime/strategy_weights.json` (from Strategy Lab)
- **Outputs**: `runtime/allocations_override.json` with normalized weights
- **Constraints**: Per-asset caps (max 35%), minimums (2%), sum-to-1 normalization
- **Behavior**: Watches source file; updates on changes every 5s

### 3. Guardian Supervisor (`neo_light_fix.sh`, `scripts/run_guardian_v13.sh`)
- **Purpose**: Ensures all agents stay alive with exponential backoff and auto-repair
- **Features**:
  - Single-instance lock protection (`runtime/.guardian.lock`)
  - Exponential backoff (2s → 60s max)
  - LLM code-fix hook after 3 consecutive failures (`scripts/code_fix_hook.sh`)
  - Live status API (`dashboard/status_endpoint.py` on port 8100)
- **Versions**:
  - v23.1 (main): Enhanced with failure counter and repair hooks
  - v13 (compatible launcher): Simplified, non-destructive alternative

### 4. Knowledge Integrator (`agents/knowledge_integrator.py`)
- **Purpose**: Aggregates external signals (Twitter/Reddit/GitHub) if API keys present
- **Outputs**: `state/knowledge_snap.json` with timestamp and source status
- **Behavior**: Graceful no-op if keys missing; env-driven activation

### 5. SmartTrader (`trader/smart_trader.py`)
- **Purpose**: Autonomous trading loop with integrated safety and signal handling
- **Asset Classes**: Crypto (BTC-USD, ETH-USD), Equities (SPY, QQQ), Commodities (GLD, SLV), Forex pairs
- **Features**:
  - Graceful shutdown (SIGINT/SIGTERM handlers)
  - Daily reset logic
  - Stateful tracking (daily PnL, alerts, streaks)
  - Spread-aware execution (no-trade if spread too wide)
  - Consumes `runtime/allocations_override.json` for position sizing
- **Integration**: Receives risk_scaler from orchestrator for dynamic position sizing

### 6. Risk Governor (Phase 101-120)
- **Purpose**: Caps exposure by volatility regime; scales allocations by risk_scaler
- **Features**: Daily/weekly VaR gates; hard stops on extreme volatility spikes
- **Integration**: Consumes `runtime/atlas_brain.json` for risk scaling decisions

### 7. Drawdown Guard (Phase 121-130)
- **Purpose**: Monitors equity curve; triggers slowdowns/pauses at MDD thresholds
- **Thresholds**: Soft stops at -5%, -10%, -15%; hard stop at -20%
- **Integration**: Pauses all agents (trading, betting, arbitrage) on hard stop

### 8. Allocator (Phase 131-140)
- **Purpose**: Converts intelligence signals + constraints into target portfolio weights
- **Constraints**: Per-asset caps (≤35%), minimums (≥2%)
- **Integration**: Outputs feed SmartTrader and other capital-intensive agents

### 9. Neural Tuner (Phase 91-100)
- **Purpose**: Periodic model tuning; sensitivity tests; walk-forward validation
- **Integration**: Retrains models for trading, sports analytics, and healthcare prediction agents

---

## Revenue Agents (Expansion Layer - Phases 23-40)

### 10. Dropshipping Agent (Phase 25-27)
- **Purpose**: Continuously scrapes trending niches for underpriced products; lists at markup
- **Sources**: AliExpress, Alibaba, CJ Dropshipping, Zendrop, Amazon/eBay via AutoDS
- **Platforms**: Shopify stores, eBay, Amazon, Etsy, Facebook Marketplace
- **Automation**: AutoDS, DSers, CJdropshipping (sourcing, fulfillment, pricing)
- **Integration**: 
  - Receives risk_scaler for inventory investment decisions
  - Outputs profit data to `state/revenue_by_agent.json`
  - Uses Knowledge Integrator signals for trending product detection
- **Data Files**: `state/dropship_listings.json`, `state/dropship_profit.csv`
- **Target Margin**: 15-60% per product

### 11. Ticket Arbitrage Agent (Phase 27-30)
- **Purpose**: Scans primary-ticket sites (Ticketmaster, Eventbrite) for sold-out/underpriced listings; relists on secondary marketplaces
- **Platforms**: StubHub, SeatGeek, Vivid Seats, TickPick
- **Tools**: Python scripts with Selenium, Ticketmaster API
- **Integration**:
  - Uses risk_scaler to determine ticket purchase budget
  - Monitors Knowledge Integrator for high-demand event signals
  - Outputs to `state/ticket_arbitrage.csv`
- **Target ROI**: 20-40% per ticket cycle

### 12. Sports Analytics Agent (Phase 30-33)
- **Purpose**: Gathers sports data and trains prediction models for NFL, NBA, MLB, etc.
- **Data Sources**: Sportradar, Stats LLC, TheRundown, iSportsFeed, Kaggle datasets
- **ML Models**: Python scikit-learn, TensorFlow (~70% accuracy target)
- **Integration**:
  - Feeds predictions to Sports-Betting Agent
  - Uses Neural Tuner for model optimization
  - Outputs to `state/sports_predictions.json`
- **Data Files**: `state/sports_models/`, `state/sports_predictions.json`

### 13. Sports-Betting Agent (Phase 33-35)
- **Purpose**: Places bets on sportsbooks/betting exchanges using predictions from analytics agent
- **Platforms**: Betfair (exchange), Pinnacle, DraftKings, FanDuel
- **Strategies**: Arbitrage, Kelly-criterion bankroll management
- **Integration**:
  - Consumes `state/sports_predictions.json` from Sports Analytics Agent
  - Uses risk_scaler and bankroll management from Risk Governor
  - RL optimization (PPO, DQN) for bet sizing
  - Outputs to `state/sports_betting_pnl.csv`
- **Target Edge**: 1-2% hold advantage over thousands of bets

### 14. Collectibles Agent (Phase 35-37)
- **Purpose**: Monitors drops and trends for high-demand collectibles (sneakers, trading cards, NFTs)
- **SNEAKERS**:
  - Platforms: StockX, GOAT, Flight Club APIs
  - Strategy: Limited-edition releases using "sneaker bots"
- **TRADING CARDS**:
  - Platforms: eBay, TCGPlayer, Cardmarket
  - Strategy: Underpriced vintage/rookie cards via price APIs
- **NFTs**:
  - Platforms: OpenSea, Magic Eden
  - Strategy: On-chain analytics for undervalued tokens
- **Integration**:
  - Uses Knowledge Integrator for trend signals
  - Risk Governor limits per-item investment
  - Outputs to `state/collectibles_inventory.json`, `state/collectibles_pnl.csv`
- **Target ROI**: 20-40% per collectible cycle

### 15. Luxury Goods Agent (Phase 37-40)
- **Purpose**: Arbitrages high-end luxury items (watches, jewelry, designer fashion, female luxury products)
- **Platforms**: eBay luxury section, Chrono24, TheRealReal, Vestiaire
- **Tools**: Price databases (WatchCharts), machine vision for counterfeit detection
- **Integration**:
  - Authenticity checks (Entrupy, expert services)
  - Risk Governor for high-value item limits
  - Outputs to `state/luxury_inventory.json`, `state/luxury_pnl.csv`
- **Target Margin**: 30-60% on authenticated, high-demand items

---

## Parallel Track Agents (Content + Healthcare)

### 16. Content Creation Agent (Parallel Track)
- **Purpose**: High-engagement niche content (lo-fi music, global sports highlights, popular science/psychology)
- **Platforms**: YouTube, TikTok, Instagram Reels, Spotify
- **Monetization**: Ad revenue, affiliate marketing, sponsorships, merchandise, digital products, lead generation
- **Integration**:
  - Uses Knowledge Integrator for trending topics
  - Outputs revenue to `state/content_revenue.csv`
  - Cross-promotes other NeoLight agents (builds brand)
- **Data Files**: `state/content_analytics.json`

### 17. AI Healthcare Agent (Parallel Track)
- **Purpose**: Solves clinical problems with AI prototypes using open datasets
- **Problem Areas**: Logistics/operations (supply-chain, scheduling), clinical analytics (note summarization, sepsis/readmission prediction)
- **Data Sources**: MIMIC-III database, PhysioNet 2019 Challenge, Kaggle health datasets
- **Revenue Models**: SaaS subscriptions, consulting projects, licensing/partnering, career payoff
- **Integration**:
  - Uses Neural Tuner for model optimization
  - Outputs to `state/healthcare_projects.json`, `state/healthcare_revenue.csv`
- **Prototypes**: Inventory management, AI scheduler, clinical note summarizer, readmission/sepsis models

---

## Phase Scripts (Research + Risk + Ops)

### Neural Tuner (91-100)
- Model tuning and sensitivity analysis
- Walk-forward validation to prevent overfitting
- **Serves**: Trading models, sports analytics, healthcare prediction models

### Risk Governor (101-120)
- Volatility-based exposure caps
- Daily/weekly VaR gates
- Hard stops on extreme volatility spikes
- **Serves**: All capital-intensive agents (trading, betting, arbitrage, luxury)

### Drawdown Guard (121-130)
- Equity curve monitoring
- MDD soft-stop tiers (5%, 10%, 15%)
- Hard-stop at 20% with recovery mode
- **Serves**: Global pause for all agents on hard stop

### Allocator (131-140)
- Converts intelligence signals + constraints into target weights
- Enforces per-asset caps (≤35%) and minimums (≥2%)
- Portfolio drift detection
- **Serves**: Trading, betting bankroll allocation

### Telemetry (141-150)
- Metrics collection and snapshots
- Performance tracking (equity curve, MDD, Sharpe)
- Optional Telegram alerts
- **Serves**: All agents; unified reporting

---

## Dashboard & API Layer

### Status API (`dashboard/status_endpoint.py`)
- **Endpoint**: GET `/status` on port 8100
- **Response**: 
  - `system`: CPU, memory, disk, uptime
  - `guardian.logs`: File mtimes for all `.log` files
  - `guardian.agents`: Process list filtered for core agents
  - **NEW**: `revenue_by_agent`: Aggregated revenue from all agents
- **Framework**: FastAPI with psutil integration

### Atlas Dashboard (`phases/phase_41_50_atlas_dashboard.sh`)
- Extended charts and panels
- Multi-agent revenue dashboard
- Optional integration with Seyenoni spec

---

## Schedulers & Operations

### Schedule All (`scripts/schedule_all.sh`)
- Runs orchestrator + knowledge integrator every 4 hours
- Appends to logs with timestamps

### Launch All (`launch_all.sh`)
- Convenience launcher for full stack
- Starts: Guardian, Dashboard, Risk Governor, Drawdown Guard, Allocator, Neural Tuner, Trader, Atlas Feedback, Drive Sync
- **Extended**: Can launch dropshipping, sports, collectibles agents on schedule

---

## Data & State Contracts

### Input Files
- `runtime/strategy_weights.json` — Strategy Lab outputs (weights per symbol)
- `state/knowledge_snap.json` — Knowledge Integrator aggregations (optional)
- **NEW**: `state/trending_products.json` — Dropshipping product trends
- **NEW**: `state/event_schedule.json` — Ticket arbitrage event data
- **NEW**: `state/sports_odds.json` — Real-time sports odds feeds

### Output Files (Core)
- `runtime/atlas_brain.json` — Risk scaler and confidence metrics
- `state/intelligence_summary.json` — Lightweight summary for dashboard
- `runtime/allocations_override.json` — Normalized allocation targets
- `state/pnl_history.csv` — Append-only trade fills
- `state/performance_metrics.csv` — Rolling equity curve
- `state/wealth_trajectory.json` — Daily wealth trajectory

### Output Files (Revenue Agents)
- `state/revenue_by_agent.json` — Aggregated revenue by agent type
- `state/dropship_listings.json` — Active dropshipping listings
- `state/dropship_profit.csv` — Dropshipping P&L
- `state/ticket_arbitrage.csv` — Ticket arbitrage transactions
- `state/sports_predictions.json` — Sports analytics model outputs
- `state/sports_betting_pnl.csv` — Sports betting P&L
- `state/collectibles_inventory.json` — Collectibles holdings
- `state/collectibles_pnl.csv` — Collectibles P&L
- `state/luxury_inventory.json` — Luxury goods holdings
- `state/luxury_pnl.csv` — Luxury goods P&L
- `state/content_revenue.csv` — Content monetization revenue
- `state/healthcare_revenue.csv` — Healthcare AI revenue

### Logs
- `logs/intelligence_orchestrator.log`
- `logs/smart_trader.log`
- `logs/weights_bridge.log`
- `logs/dashboard_v3.log`
- `logs/guardian_stdout.log`
- **NEW**: `logs/dropship_agent.log`
- **NEW**: `logs/ticket_arbitrage.log`
- **NEW**: `logs/sports_analytics.log`
- **NEW**: `logs/sports_betting.log`
- **NEW**: `logs/collectibles_agent.log`
- **NEW**: `logs/luxury_agent.log`
- **NEW**: `logs/content_agent.log`
- **NEW**: `logs/healthcare_agent.log`

---

## Reliability & Guardrails

### Idempotency
- All scripts safe to re-run
- Lock files prevent duplicate instances
- State files are append-only or timestamped

### Error Handling
- Exponential backoff on failures (2s → 60s max)
- After 3 consecutive failures: invoke `scripts/code_fix_hook.sh` (Cursor/DeepSeek integration)
- Fail fast, log to `logs/*.log`

### Health Monitoring
- Status API provides real-time system health
- Port healing on startup (kills processes on 8090-8110)
- Process monitoring via `kill -0` checks
- **NEW**: Agent-specific health checks (API connectivity, data freshness)

### Security
- No destructive actions without caps
- Allocations clamped [0.02, 0.35]
- Local-only dashboard by default (auth + TLS recommended for remote)
- **NEW**: Authenticity verification for luxury goods and collectibles

---

## Agent Integration Matrix

| Agent | Consumes | Produces | Risk Control | Capital Source |
|-------|----------|----------|--------------|----------------|
| Intelligence Orchestrator | None (system heartbeat) | atlas_brain.json, intelligence_summary.json | N/A | N/A |
| SmartTrader | allocations_override.json, atlas_brain.json | pnl_history.csv, performance_metrics.csv | Risk Governor, Drawdown Guard | Trading capital |
| Dropshipping Agent | knowledge_snap.json (trends), risk_scaler | dropship_profit.csv, dropship_listings.json | Max inventory cap | Profit reinvestment |
| Ticket Arbitrage | event_schedule.json, risk_scaler | ticket_arbitrage.csv | Per-event budget limit | Profit reinvestment |
| Sports Analytics | Sportradar/Stats APIs | sports_predictions.json | Model validation | Operating costs |
| Sports-Betting | sports_predictions.json, atlas_brain.json | sports_betting_pnl.csv | Kelly criterion, bankroll mgmt | Betting bankroll |
| Collectibles Agent | knowledge_snap.json (trends), risk_scaler | collectibles_pnl.csv, collectibles_inventory.json | Per-item cap, authenticity | Profit reinvestment |
| Luxury Goods Agent | WatchCharts/price APIs, risk_scaler | luxury_pnl.csv, luxury_inventory.json | High-value limits, auth checks | Profit reinvestment |
| Content Agent | knowledge_snap.json (trending topics) | content_revenue.csv, content_analytics.json | Time allocation only | Minimal (organic growth) |
| Healthcare Agent | MIMIC-III, PhysioNet datasets | healthcare_revenue.csv, healthcare_projects.json | Project scope limits | Consulting/SaaS revenue |

---

## Environment & Dependencies

### Python
- Version: 3.9-3.12 supported
- Virtual environment: `venv/` directory
- Required packages:
  - `fastapi`, `uvicorn`, `psutil` (core API)
  - `pandas`, `yfinance` (data/backtesting)
  - `plotly` (visualization)
  - `gTTS`, `playsound3` (optional alerts)
  - **NEW**: `selenium`, `requests` (web scraping for dropshipping/tickets)
  - **NEW**: `scikit-learn`, `tensorflow` (ML for sports/healthcare)
  - **NEW**: `betfairlightweight` (sports betting API)
  - **NEW**: `shopify-python-api` (dropshipping automation)

### Configuration
- `NEOLIGHT_ORCH_INTERVAL` — Orchestrator heartbeat interval (default: 300s)
- `NEOLIGHT_STARTING_EQUITY` — Starting capital (default: 10000)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — Optional Telegram alerts
- `TWITTER_BEARER_TOKEN`, `REDDIT_CLIENT_ID`, `REDDIT_SECRET`, `GITHUB_TOKEN` — Optional knowledge integrator
- **NEW**: `SHOPIFY_API_KEY`, `SHOPIFY_PASSWORD` — Dropshipping store access
- **NEW**: `BETFAIR_API_KEY`, `BETFAIR_PASSWORD` — Sports betting API
- **NEW**: `SPORTRADAR_API_KEY` — Sports data feeds
- **NEW**: `STOCKX_API_KEY`, `GOAT_API_KEY` — Collectibles market data

---

## Coding Standards (from `.cursorrules`)

- Python 3.12+, use `Optional[T]` instead of `type|None`
- Fail fast, log errors to `logs/*.log`
- Never break idempotency: scripts must be re-runnable
- Small PR-sized changes; keep diffs readable
- Minimum test: `python -m py_compile` passes for changed Python files

---

## File Structure

```
neolight/
├── agents/              # Brain/orchestrator/watchers
│   ├── intelligence_orchestrator.py
│   ├── weights_bridge.py
│   ├── knowledge_integrator.py
│   ├── dropship_agent.py           # NEW
│   ├── ticket_arbitrage_agent.py   # NEW
│   ├── sports_analytics_agent.py   # NEW
│   ├── sports_betting_agent.py     # NEW
│   ├── collectibles_agent.py       # NEW
│   ├── luxury_agent.py             # NEW
│   ├── content_agent.py            # NEW
│   └── healthcare_agent.py         # NEW
├── trader/              # SmartTrader loop and broker interfaces
│   └── smart_trader.py
├── phases/              # Phase scripts (research/risk/ops)
│   ├── phase_91_100_neural_tuner.py
│   ├── phase_101_120_risk_governor.sh
│   ├── phase_121_130_drawdown_guard.sh
│   ├── phase_131_140_allocator.py
│   └── phase_141_150_telemetry.sh
├── dashboard/           # Live FastAPI dashboard
│   └── status_endpoint.py
├── scripts/             # Guardians, schedulers, auto-heal
│   ├── schedule_all.sh
│   ├── run_guardian_v13.sh
│   └── code_fix_hook.sh
├── backend/             # Ledger engine, portfolio management
├── state/               # Persistent state files (all agents)
├── runtime/             # Runtime outputs (brain, allocations)
├── logs/                # All log files (all agents)
└── neo_light_fix.sh     # Main Guardian supervisor (v23.1)
```

---

## Integration Points

1. **Cursor IDE**: `.cursorrules` provides guardrails for AI-assisted coding
2. **DeepSeek/LLM Repair**: `scripts/code_fix_hook.sh` invoked after 3 failures
3. **Strategy Lab**: Produces `runtime/strategy_weights.json` → consumed by Weights Bridge
4. **Atlas Dashboard**: Optional frontend consuming Status API and phase outputs
5. **Telegram**: Optional alerts via backend/ledger_engine.py
6. **NEW**: **AutoDS/Shopify**: Dropshipping automation integrations
7. **NEW**: **Betfair/Pinnacle**: Sports betting API integrations
8. **NEW**: **StockX/GOAT**: Collectibles market data APIs
9. **NEW**: **MIMIC-III/PhysioNet**: Healthcare open datasets

---

## Master Phase Plan Alignment

- **Phases 1-10**: Unified Autopilot Foundation (current status)
- **Phases 11-30**: Multi-Agent Expansion (trading + dropshipping + tickets + sports)
- **Phases 31-45**: Profit Layer Scaling (collectibles + luxury + healthcare)
- **Phases 46-60+**: Autonomous Intelligence (full self-management)

---

**Last Updated**: 2025-10-31  
**Guardian Version**: v23.1 (with v13 compatible launcher)  
**Active Agents**: 17 (7 core + 10 revenue agents)  
**Status**: Operational with 120s orchestrator interval  
**Target**: $1M in 24 months via multi-agent revenue diversification


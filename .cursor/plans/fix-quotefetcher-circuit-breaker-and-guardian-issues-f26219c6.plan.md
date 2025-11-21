<!-- f26219c6-2338-47c2-ac87-c368cd4b91b0 54c9ae11-fb80-4e4f-abfd-0e0e4b868b4a -->
# 2-Month Parallel Development Plan for Wealth Mesh (CORRECTED PRIORITIES)

## Overview

While paper trading trains for 2 months, we can simultaneously:

1. **PRIORITY 1**: Enhance training/optimization systems (improve trading performance)
2. **PRIORITY 2**: Multi-platform dropshipping agent (FREE platforms, skip Shopify/AutoDS)
3. **PRIORITY 3**: Ticket arbitrage agent
4. **PRIORITY 4**: Luxury goods agent
5. **PRIORITY 5**: Collectibles agent
6. **PRIORITY 6**: Healthcare AI agent

## Month 1: Training & Revenue Agents

### Week 1: Training & Optimization Enhancements (PRIORITY 1)

#### 1. Enhanced Backtesting System

**File**: `backend/replay_engine.py` (exists, needs enhancement)
**Actions**:

- Add walk-forward optimization
- Implement Monte Carlo simulation
- Add transaction cost modeling (slippage, fees)
- Create backtest comparison tool
- Schedule daily backtests on historical data

**Expected Time**: 6-8 hours

#### 2. Strategy Optimization Loop

**File**: `agents/strategy_research.py` (exists, needs enhancement)
**Actions**:

- Add parameter optimization (grid search, Bayesian optimization)
- Implement strategy scoring and ranking
- Create strategy retirement logic (auto-disable underperforming)
- Add strategy correlation analysis
- Output optimized strategies to `runtime/strategy_weights.json`

**Expected Time**: 6-8 hours

#### 3. ML Pipeline Enhancement

**File**: `agents/ml_pipeline.py` (exists, needs enhancement)
**Actions**:

- Add automated model selection (XGBoost, LSTM, Transformer)
- Implement hyperparameter tuning with Optuna
- Add ensemble model creation
- Create model performance tracking
- Schedule daily retraining on new data

**Expected Time**: 8-10 hours

#### 4. Sports Analytics Agent (Quick Win - FREE)

**File**: `agents/sports_analytics_agent.py` (already exists)
**Setup**:

- Check if Sportradar API key already exists in environment
- If not, get free Sportradar API key from sportradar.com
- Export `SPORTRADAR_API_KEY` environment variable

**Actions**:

- Verify existing Sportradar API key (if any)
- Implement Sportradar API integration in `agents/sports_analytics_agent.py`
- Add prediction model training (scikit-learn RandomForest)
- Connect to Sports Betting Agent when ready
- Output predictions to `state/sports_predictions.json`

**Expected Time**: 4-6 hours

### Week 2: Multi-Platform Dropshipping Agent (PRIORITY 2)

#### 5. Multi-Platform Dropshipping (Skip Shopify/AutoDS)

**File**: `agents/dropship_agent.py` (enhance to support free platforms)
**Strategy**: Skip Shopify/AutoDS (doesn't make money) - Use FREE platforms instead

**FREE Platforms (No Monthly Fees)**:

- **Etsy** - $0.20 per listing (FREE account)
- **Mercari** - 10% commission (FREE account)
- **Poshmark** - 20% commission (FREE account)
- **TikTok Shop** - Variable commission (FREE account)
- **Facebook Marketplace** - FREE (no fees)
- **Depop** - 10% commission (FREE account)

**Actions**:

- Enhance `agents/dropship_agent.py` to support multiple free platforms
- Implement platform-specific APIs (Etsy, Mercari, Poshmark, TikTok Shop)
- Create unified listing system (list same product on all platforms)
- Skip Shopify/AutoDS integration (not profitable)
- Monitor revenue across all platforms
- Output to `state/dropship_profit.csv`

**Expected Time**: 12-16 hours

### Week 3: Ticket Arbitrage Agent (PRIORITY 3)

#### 6. Ticket Arbitrage Agent

**File**: `agents/ticket_arbitrage_agent.py` (already exists, needs enhancement)
**Platforms**:

- **Primary**: Ticketmaster, Eventbrite (scan for sold-out/underpriced)
- **Secondary**: StubHub, SeatGeek, Vivid Seats, TickPick (relist)

**Setup**:

- Ticketmaster API (requires application - selective approval)
- Alternative: Manual monitoring first, automate later

**Actions**:

- Enhance `agents/ticket_arbitrage_agent.py` with Ticketmaster API (if available)
- Implement manual monitoring workflow (if API not available)
- Add event signal detection from Knowledge Integrator
- Create price monitoring and arbitrage detection
- Implement relisting on secondary marketplaces
- Add risk limits per event
- Output to `state/ticket_arbitrage.csv`

**Expected Time**: 10-14 hours

### Week 4: Luxury Goods Agent (PRIORITY 4)

#### 7. Luxury Goods Agent

**File**: `agents/luxury_agent.py` (needs to be created)
**Platforms**:

- **eBay luxury section** - Use AutoDS as middleware (workaround for suspended account)
- **Chrono24** - Watches (API if available, or manual monitoring)
- **TheRealReal** - Luxury fashion (manual monitoring)
- **Vestiaire** - Designer items (manual monitoring)

**eBay Suspension Workaround**:

- Use AutoDS as middleware: NeoLight → AutoDS API → eBay (old account `seakin67`)
- AutoDS acts as trusted firewall (eBay sees AutoDS activity, not raw bot)
- This may allow connection even with suspended account
- If that doesn't work, focus on other luxury platforms

**Actions**:

- Create `agents/luxury_agent.py`
- Implement price monitoring for watches, jewelry, designer fashion
- Add authenticity verification workflow
- Create inventory management system
- Add risk limits for high-value items
- Implement eBay connection via AutoDS middleware (suspension workaround)
- Output to `state/luxury_pnl.csv`

**Expected Time**: 12-16 hours

## Month 2: Collectibles & Healthcare

### Week 5-6: Collectibles Agent (PRIORITY 5)

#### 8. Collectibles Agent

**File**: `agents/collectibles_agent.py` (needs to be created)
**Platforms**:

- **Alternative platforms** (eBay account suspended):
- **TCGPlayer** - Trading cards (free API available)
- **Cardmarket** - Trading cards (Europe, free API)
- **StockX** - Sneakers (limited API, requires partnership)
- **GOAT** - Sneakers (manual monitoring)
- **Facebook Marketplace** - Trading cards, collectibles (FREE)

**eBay Workaround**:

- If AutoDS middleware works for luxury, use same approach for collectibles
- Otherwise, focus on alternative platforms above

**Actions**:

- Create `agents/collectibles_agent.py`
- Implement TCGPlayer API integration (trading cards)
- Implement Cardmarket API integration (trading cards)
- Add price monitoring and arbitrage detection
- Add to `neo_light_fix.sh` guardian script
- Output to `state/collectibles_pnl.csv`

**Expected Time**: 8-12 hours

### Week 7-8: Healthcare AI Agent (PRIORITY 6)

#### 9. Healthcare AI Agent

**File**: `agents/healthcare_agent.py` (needs to be created)
**Data Sources**:

- MIMIC-III database (free, requires application)
- PhysioNet 2019 Challenge (free)
- Kaggle health datasets (free)

**Actions**:

- Create `agents/healthcare_agent.py`
- Implement clinical note summarization model
- Build readmission prediction model
- Create sepsis prediction model
- Add project tracking to `state/healthcare_projects.json`
- Target: Build portfolio for consulting/SaaS opportunities

**Expected Time**: 20-30 hours

## Implementation Priorities (CORRECTED ORDER)

### Priority 1: Training & Optimization (Improve Trading Performance)

1. Enhanced Backtesting System (improves trading)
2. Strategy Optimization Loop (improves performance)
3. ML Pipeline Enhancement (improves predictions)
4. Sports Analytics Agent (FREE, quick win - supports betting)

### Priority 2: Multi-Platform Dropshipping Agent

5. Multi-Platform Dropshipping Agent (Etsy, Mercari, Poshmark, TikTok Shop)

- Skip Shopify/AutoDS (doesn't make money)
- Use FREE platforms only

### Priority 3: Ticket Arbitrage Agent

6. Ticket Arbitrage Agent (before luxury)

- Ticketmaster API (if available)
- Manual monitoring workflow (if API not available)

### Priority 4: Luxury Goods Agent

7. Luxury Goods Agent (after ticket agent)

- eBay via AutoDS middleware (suspension workaround)
- Alternative platforms (Chrono24, TheRealReal, Vestiaire)

### Priority 5: Collectibles Agent

8. Collectibles Agent (after luxury)

- Alternative platforms (TCGPlayer, Cardmarket)
- eBay workaround if AutoDS middleware works

### Priority 6: Healthcare AI Agent

9. Healthcare AI Agent (last revenue agent)

- Clinical AI prototypes
- Build portfolio for consulting/SaaS

## File Changes Required

### New Files to Create (In Priority Order)

1. `agents/ticket_arbitrage_agent.py` - Ticket arbitrage (enhance existing, PRIORITY 3)
2. `agents/luxury_agent.py` - Luxury goods arbitrage (watches, jewelry, designer fashion, PRIORITY 4)
3. `agents/collectibles_agent.py` - Trading cards arbitrage (TCGPlayer, Cardmarket, PRIORITY 5)
4. `agents/healthcare_agent.py` - Clinical AI prototypes (PRIORITY 6)

### Files to Enhance (In Priority Order)

1. `backend/replay_engine.py` - Add walk-forward, Monte Carlo (PRIORITY 1)
2. `agents/strategy_research.py` - Add parameter optimization (PRIORITY 1)
3. `agents/ml_pipeline.py` - Add auto-model selection, tuning (PRIORITY 1)
4. `agents/sports_analytics_agent.py` - Add Sportradar API integration (check if API key exists, PRIORITY 1)
5. `agents/dropship_agent.py` - Enhance to support free multi-platform strategy (Etsy, Mercari, Poshmark, TikTok Shop, skip Shopify, PRIORITY 2)
6. `agents/ticket_arbitrage_agent.py` - Enhance with Ticketmaster API or manual workflow (PRIORITY 3)
7. `neo_light_fix.sh` - Add new agents to guardian (ticket, luxury, collectibles, healthcare)

## Next Steps (CORRECTED PRIORITY ORDER)

### Week 1: Training & Optimization (PRIORITY 1)

1. **Day 1-2**: Enhanced Backtesting System

- Add walk-forward optimization
- Implement Monte Carlo simulation
- Add transaction cost modeling

2. **Day 3-4**: Strategy Optimization Loop

- Add parameter optimization
- Implement strategy scoring and ranking
- Create strategy retirement logic

3. **Day 5**: ML Pipeline Enhancement

- Add automated model selection
- Implement hyperparameter tuning
- Add ensemble model creation

4. **Day 6-7**: Sports Analytics Agent

- Check if Sportradar API key exists
- If exists: Start immediately
- If not: Get free API key, then implement

### Week 2: Multi-Platform Dropshipping (PRIORITY 2)

5. **Day 1-4**: Enhance Dropshipping Agent

- Implement Etsy API integration
- Implement Mercari API integration
- Implement Poshmark API integration
- Implement TikTok Shop API integration
- Skip Shopify/AutoDS (not profitable)
- Create unified multi-platform listing system

### Week 3: Ticket Arbitrage Agent (PRIORITY 3)

6. **Day 1-3**: Enhance Ticket Arbitrage Agent

- Implement Ticketmaster API (if available)
- Create manual monitoring workflow (if API not available)
- Add event signal detection
- Implement relisting on secondary marketplaces

### Week 4: Luxury Goods Agent (PRIORITY 4)

7. **Day 1-4**: Build Luxury Goods Agent

- Create `agents/luxury_agent.py`
- Implement price monitoring for watches, jewelry, fashion
- Try eBay connection via AutoDS middleware (suspension workaround)
- Add alternative luxury platforms (Chrono24, TheRealReal, Vestiaire)

### Month 2: Collectibles & Healthcare (PRIORITY 5-6)

8. **Week 1-2**: Collectibles Agent (PRIORITY 5)

- Create `agents/collectibles_agent.py`
- Implement TCGPlayer API integration
- Implement Cardmarket API integration
- Try eBay workaround if AutoDS middleware worked for luxury

9. **Week 3-4**: Healthcare AI Agent (PRIORITY 6)

- Create `agents/healthcare_agent.py`
- Implement clinical models
- Build portfolio for consulting/SaaS opportunities

## Success Metrics

### Revenue Agents

- **Sports Analytics**: Running, generating predictions
- **Dropshipping**: $500+/month profit (free platforms)
- **Ticket Arbitrage**: 5+ profitable trades/month
- **Luxury Goods**: 3+ authenticated items/month
- **Collectibles**: 10+ profitable trades/month
- **Healthcare**: 1-2 prototype models complete

### Trading Improvements

- **Backtesting**: 10+ strategies tested with walk-forward
- **Strategy Optimization**: 20%+ Sharpe improvement
- **ML Pipeline**: 5%+ prediction accuracy improvement
- **Monte Carlo**: Risk-adjusted return estimates

## Key Decisions

1. **Skip Shopify/AutoDS**: Doesn't make money - use FREE multi-platform strategy instead
2. **eBay Suspension**: Use AutoDS middleware as workaround for `seakin67` account
3. **Priority Order**: Training first, then revenue agents in specified order
4. **Ticket Before Luxury**: Ticket arbitrage has lower barriers to entry
5. **Check Sportradar API**: Verify if key already exists before requesting new one

### To-dos (CORRECTED PRIORITY ORDER)

**PRIORITY 1: Training & Optimization**

- [ ] Enhance backtesting system: Add walk-forward optimization, Monte Carlo simulation, transaction cost modeling (PRIORITY 1.1)
- [ ] Enhance strategy research: Add parameter optimization, strategy scoring, retirement logic (PRIORITY 1.2)
- [ ] Enhance ML pipeline: Add auto-model selection, hyperparameter tuning, ensemble models (PRIORITY 1.3)
- [ ] Activate Sports Analytics Agent: Check if Sportradar API key exists, implement API integration, add prediction model training (PRIORITY 1.4)

**PRIORITY 2: Multi-Platform Dropshipping Agent**

- [ ] Enhance Dropshipping Agent: Implement Etsy, Mercari, Poshmark, TikTok Shop API integrations, skip Shopify/AutoDS (PRIORITY 2.1)

**PRIORITY 3: Ticket Arbitrage Agent**

- [ ] Enhance Ticket Arbitrage Agent: Implement Ticketmaster API (if available) or manual monitoring workflow, add event signal detection (PRIORITY 3.1)

**PRIORITY 4: Luxury Goods Agent**

- [ ] Build Luxury Goods Agent: Create agent file, implement price monitoring for watches/jewelry/fashion, try eBay via AutoDS middleware, add alternative platforms (PRIORITY 4.1)

**PRIORITY 5: Collectibles Agent**

- [ ] Build Collectibles Agent: Create agent file, implement TCGPlayer and Cardmarket API integrations, try eBay workaround if AutoDS middleware works (PRIORITY 5.1)

**PRIORITY 6: Healthcare AI Agent**

- [ ] Build Healthcare AI Agent: Create agent file, implement clinical models (note summarization, readmission, sepsis), set up data pipelines (PRIORITY 6.1)

**Lower Priority (Month 2+)**

- [ ] Create walk-forward optimizer: Build framework, implement rolling windows, add validation
- [ ] Enhance portfolio optimization: Add Black-Litterman, hierarchical risk parity, regime-aware optimization
- [ ] Enhance risk management: Improve VaR/CVaR, add stress testing, implement risk attribution
- [ ] Build Content Creation Agent: Create agent file, implement content generation, add platform APIs

### To-dos

- [ ] Activate Sports Analytics Agent: Get Sportradar API key, implement API integration, add prediction model training
- [ ] Set up Dropshipping Agent: Create Shopify store, configure AutoDS, test integration
- [ ] Build eBay Collectibles Agent: Create agent file, implement eBay API integration, add to guardian
- [ ] Enhance backtesting system: Add walk-forward optimization, Monte Carlo simulation, transaction cost modeling
- [ ] Enhance strategy research: Add parameter optimization, strategy scoring, retirement logic
- [ ] Enhance ML pipeline: Add auto-model selection, hyperparameter tuning, ensemble models
- [ ] Build Healthcare AI Agent: Create agent file, implement clinical models, set up data pipelines
- [ ] Build Content Creation Agent: Create agent file, implement content generation, add platform APIs
- [ ] Build Luxury Goods Agent: Create agent file, implement price monitoring, add authenticity checks
- [ ] Create walk-forward optimizer: Build framework, implement rolling windows, add validation
- [ ] Enhance portfolio optimization: Add Black-Litterman, hierarchical risk parity, regime-aware optimization
- [ ] Enhance risk management: Improve VaR/CVaR, add stress testing, implement risk attribution
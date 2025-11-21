# Revenue Agents Activation Guide

## 🛒 Dropshipping Agent Activation

### When Can You Start?
**Status**: Code is ready, but needs API connections

### Required API Keys & Setup

#### 1. **Shopify Store** (Primary Platform)
```bash
export SHOPIFY_API_KEY="your_shopify_api_key"
export SHOPIFY_PASSWORD="your_shopify_password"
export SHOPIFY_STORE="your-store-name.myshopify.com"
```

**How to Get Shopify API Credentials:**
1. Go to your Shopify admin panel
2. Settings → Apps and sales channels → Develop apps
3. Create app → Admin API access scopes
4. Generate API credentials

**Cost**: Shopify Basic Plan ($29/month)

---

#### 2. **AutoDS Integration** (Automation)
- Sign up at AutoDS.com
- Connect your Shopify store
- AutoDS handles product imports, pricing, fulfillment
- **Cost**: $19-49/month depending on plan

---

#### 3. **AliExpress / Alibaba** (Product Sourcing)
- No API needed - AutoDS handles this
- Or manually use AliExpress Dropshipping Center
- **Cost**: Free (pay per product ordered)

---

#### 4. **Temu / Shein** (Alternative Sources)
- **Temu**: No official API yet - would need web scraping (legal risks)
- **Shein**: No public API - manual sourcing only
- **Recommendation**: Start with AliExpress/Shopify, expand later

---

### Activation Steps

1. **Enable Revenue Agents**:
```bash
export NEOLIGHT_ENABLE_REVENUE_AGENTS=true
bash ~/neolight/neo_light_fix.sh
```

2. **Configure Shopify**:
   - Set environment variables above
   - Create Shopify store (if not done)
   - Install AutoDS app

3. **Configure AutoDS**:
   - Connect to Shopify
   - Set up product import rules
   - Configure pricing markup (20-50%)

4. **Start Dropshipping Agent**:
   - Agent will auto-start when Guardian launches revenue agents
   - Monitors `state/trending_products.json` (from knowledge_integrator)
   - Lists products on Shopify automatically

---

## 🎫 Ticket Arbitrage Agent

### When Can You Start?
**Status**: Needs Ticketmaster API access (limited availability)

### Required Setup

#### Ticketmaster API
- **Application Required**: Submit app to Ticketmaster Developer Program
- **Access**: Not guaranteed - selective approval
- **Alternative**: Use web scraping (higher risk, legal concerns)

**Recommendation**: Start manually, automate later once profitable

---

## ⚽ Sports Betting Agent

### When Can You Start?
**Status**: Requires sportsbook accounts and API access

### Required Setup

#### Betfair Exchange (Recommended)
```bash
export BETFAIR_API_KEY="your_key"
export BETFAIR_PASSWORD="your_password"
export BETFAIR_APP_KEY="your_app_key"
```

**Steps:**
1. Create Betfair account (verify identity)
2. Fund account (minimum varies by region)
3. Apply for API access via Betfair Developer Portal
4. Get API credentials

**Legal Note**: Check your jurisdiction - sports betting may be restricted

---

#### Alternative: DraftKings / FanDuel
- Limited/no public API
- Manual betting required
- **Recommendation**: Start with Betfair if available

---

## 🏀 Sports Analytics Agent

### When Can You Start?
**Status**: Ready to start (needs Sportradar API key)

### Required Setup

```bash
export SPORTRADAR_API_KEY="your_key"
```

**How to Get:**
1. Sign up at Sportradar.com
2. Request API access (free tier available)
3. Get API key for sports data feeds

**Cost**: Free tier available, paid tiers for more data

---

## 📦 Collectibles Agent

### When Can You Start?
**Status**: Needs marketplace API access

### Required APIs

#### StockX (Sneakers)
- **API**: Limited availability - requires partnership
- **Alternative**: Use StockX web app manually

#### GOAT (Sneakers)
- **API**: Not publicly available
- **Alternative**: Manual monitoring

#### eBay (Trading Cards)
- **API**: eBay Developer Program (free)
- **Steps**: 
  1. Register at developer.ebay.com
  2. Get App ID and Cert ID
  3. Set up OAuth tokens

---

## 💎 Luxury Goods Agent

### When Can You Start?
**Status**: Needs marketplace API access

### Required Setup

#### Chrono24 (Watches)
- **API**: Requires partnership application
- **Alternative**: Manual monitoring

#### TheRealReal / Vestiaire
- **API**: Not publicly available
- **Alternative**: Manual sourcing

---

## 🚀 Quick Start Guide

### Step 1: Start with Easiest (Sports Analytics)
```bash
export SPORTRADAR_API_KEY="your_key"  # Free tier available
bash ~/neolight/neo_light_fix.sh
```

### Step 2: Activate Dropshipping (Most Profitable)
```bash
# Set Shopify credentials
export SHOPIFY_API_KEY="your_key"
export SHOPIFY_PASSWORD="your_password"
export SHOPIFY_STORE="your-store.myshopify.com"

# Enable revenue agents
export NEOLIGHT_ENABLE_REVENUE_AGENTS=true
bash ~/neolight/neo_light_fix.sh
```

### Step 3: Add Others As You Get API Access

---

## 📊 Revenue Agent Readiness Matrix

| Agent | Code Ready | API Available | Difficulty | Estimated Setup Time |
|-------|-----------|---------------|------------|---------------------|
| Sports Analytics | ✅ | ✅ Free | Easy | 30 minutes |
| Dropshipping | ✅ | ✅ Paid | Medium | 2-4 hours |
| Sports Betting | ✅ | ⚠️ Restricted | Hard | 1-2 days |
| Ticket Arbitrage | ✅ | ❌ Limited | Hard | Manual first |
| Collectibles | ✅ | ⚠️ Limited | Medium | 1 day |
| Luxury Goods | ✅ | ❌ Limited | Hard | Manual first |

---

## 🎯 Recommended Activation Order

1. **Sports Analytics** (Easiest, free API)
2. **Dropshipping** (Most profitable, $29/month Shopify)
3. **Collectibles (eBay)** (Free API, manual at first)
4. **Sports Betting** (If legal in your jurisdiction)
5. **Luxury/Tickets** (Require partnerships)

---

## 💡 Quick Wins (Can Start Today)

### 1. Sports Analytics Agent
- Free Sportradar API key
- Starts analyzing sports data immediately
- Feeds predictions to sports betting agent (when ready)

### 2. eBay Trading Cards (Manual First)
- Free eBay API
- Can start monitoring cards immediately
- Manual execution until profitable, then automate

### 3. Dropshipping (Shopify + AutoDS)
- $29/month Shopify + $19/month AutoDS = $48/month
- Can start listing products today
- AutoDS handles most automation

---

**Bottom Line**: You can start **Sports Analytics** and **Dropshipping** agents **today** with minimal setup. Others require more API access or partnerships.


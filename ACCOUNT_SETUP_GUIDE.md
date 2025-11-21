# Account Setup Guide for NeoLight Services

## ⚠️ Important: Account Creation

**I cannot create accounts for you** - I don't have access to external services' signup systems. However, I can guide you through the process and help you configure them once you have credentials.

---

## 🔑 Services That Need Accounts

### **Free Accounts (Start Today)**

#### 1. **FRED API (Federal Reserve Data)**
- **URL**: https://fred.stlouisfed.org/
- **Steps**:
  1. Sign up (free account)
  2. Go to Account → API Keys
  3. Generate API key
  4. Set: `export FRED_API_KEY="your_key"`

#### 2. **NewsAPI (Financial News)**
- **URL**: https://newsapi.org/
- **Steps**:
  1. Sign up (free tier: 100 requests/day)
  2. Get API key from dashboard
  3. Set: `export NEWS_API_KEY="your_key"`

#### 3. **Reddit API (Sentiment Analysis)**
- **URL**: https://www.reddit.com/prefs/apps
- **Steps**:
  1. Log in to Reddit
  2. Create app at reddit.com/prefs/apps
  3. Get Client ID and Secret
  4. Set:
     ```bash
     export REDDIT_CLIENT_ID="your_id"
     export REDDIT_SECRET="your_secret"
     ```

#### 4. **Sportradar (Sports Analytics)**
- **URL**: https://sportradar.com/developers
- **Steps**:
  1. Sign up for free tier
  2. Get API key
  3. Set: `export SPORTRADAR_API_KEY="your_key"`

#### 5. **eBay API (Collectibles)**
- **URL**: https://developer.ebay.com/
- **Steps**:
  1. Register developer account
  2. Create app
  3. Get App ID and Cert ID
  4. Set:
     ```bash
     export EBAY_APP_ID="your_id"
     export EBAY_CERT_ID="your_cert"
     ```

---

### **Paid Services (Monthly Costs)**

#### 6. **Shopify Store (Dropshipping)**
- **URL**: https://www.shopify.com/
- **Cost**: $29/month (Basic Plan)
- **Steps**:
  1. Sign up for 14-day free trial
  2. Choose store name (e.g., "yourstore.myshopify.com")
  3. Complete store setup
  4. Go to Settings → Apps and sales channels → Develop apps
  5. Create app → Admin API access scopes
  6. Get API Key and Password
  7. Set:
     ```bash
     export SHOPIFY_API_KEY="your_api_key"
     export SHOPIFY_PASSWORD="your_api_password"
     export SHOPIFY_STORE="yourstore.myshopify.com"
     ```

#### 7. **AutoDS (Dropshipping Automation)**
- **URL**: https://www.autods.com/
- **Cost**: $19-49/month (Starter Plan: $19)
- **Steps**:
  1. Sign up for AutoDS
  2. Connect to your Shopify store
  3. Connect to AliExpress/Alibaba
  4. Configure product import rules
  5. Set pricing markup (30-50%)
  6. Enable auto-fulfillment

#### 8. **Betfair (Sports Betting)**
- **URL**: https://www.betfair.com/
- **Cost**: Free (but need to fund account)
- **Legal**: Check your jurisdiction
- **Steps**:
  1. Create account (verify identity required)
  2. Fund account
  3. Apply for API access: https://docs.developer.betfair.com/
  4. Get API Key, Username, Password
  5. Set:
     ```bash
     export BETFAIR_API_KEY="your_key"
     export BETFAIR_USERNAME="your_username"
     export BETFAIR_PASSWORD="your_password"
     ```

---

## 💳 Payment Information Needed

### **Where Money Goes:**

#### Trading Profits:
- **Paper Trading**: Currently simulated (no real money)
- **Live Trading**: Would go to your broker account (Alpaca, Interactive Brokers, etc.)
- **Withdrawal**: You set up bank account in broker dashboard

#### Dropshipping Revenue:
- **Shopify Payments**: Money goes to your Shopify Payments account
- **Payout**: Transferred to your linked bank account (set up in Shopify Settings → Payments)
- **Frequency**: Daily, weekly, or monthly (your choice)

#### Sports Betting:
- **Betfair**: Winnings stay in Betfair account
- **Withdrawal**: Transfer to your bank account (set up in Betfair account settings)

---

## 🔧 Configuration After Account Creation

Once you have all credentials, add them to your shell profile:

```bash
# Add to ~/.zshrc or ~/.bash_profile
export FRED_API_KEY="your_fred_key"
export NEWS_API_KEY="your_newsapi_key"
export REDDIT_CLIENT_ID="your_reddit_id"
export REDDIT_SECRET="your_reddit_secret"
export SPORTRADAR_API_KEY="your_sportradar_key"
export SHOPIFY_API_KEY="your_shopify_key"
export SHOPIFY_PASSWORD="your_shopify_password"
export SHOPIFY_STORE="yourstore.myshopify.com"
export BETFAIR_API_KEY="your_betfair_key"
export BETFAIR_USERNAME="your_username"
export BETFAIR_PASSWORD="your_password"

# Then reload:
source ~/.zshrc  # or source ~/.bash_profile
```

---

## 📋 Quick Setup Checklist

### Today (Free):
- [ ] FRED API account
- [ ] NewsAPI account
- [ ] Reddit app creation
- [ ] Sportradar account

### This Week (Paid):
- [ ] Shopify store ($29/month)
- [ ] AutoDS subscription ($19/month)
- [ ] Connect AutoDS to Shopify

### When Ready:
- [ ] Betfair account + API (if legal in your area)
- [ ] eBay Developer account (for collectibles)

---

**Note**: I cannot actually create these accounts for you, but I can help you configure them once you have the credentials. The process is straightforward - most take 5-15 minutes to set up.


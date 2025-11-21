# Shopify API Setup - Fix 403 Errors

## Problem
Getting `403 Forbidden` when creating products via API.

## Solution
Your Shopify Admin API access token needs proper permissions.

## Step-by-Step Fix

### 1. Go to Shopify Admin
1. Log in to: https://trendytreasure-market.myshopify.com/admin
2. Go to **Settings** → **Apps and sales channels**
3. Click **Develop apps** (at bottom)

### 2. Create Admin API App
1. Click **Create an app**
2. Name: `NeoLight Automation`
3. Click **Create app**

### 3. Configure API Scopes
1. Click **Configure Admin API scopes**
2. Enable these scopes:
   - ✅ `read_products`
   - ✅ `write_products`
   - ✅ `read_orders`
   - ✅ `write_orders`
   - ✅ `read_inventory`
   - ✅ `write_inventory`
   - ✅ `read_fulfillments`
   - ✅ `write_fulfillments`
3. Click **Save**

### 4. Install App & Get Access Token
1. Click **Install app**
2. Confirm installation
3. Copy the **Admin API access token** (starts with `shpat_`)

### 5. Update Environment Variables
```bash
# Add to ~/.neolight_secrets
export SHOPIFY_STORE="trendytreasure-market.myshopify.com"
export SHOPIFY_ACCESS_TOKEN="shpat_YOUR_NEW_TOKEN_HERE"
```

### 6. Test API Access
```bash
cd ~/neolight
source ~/.neolight_secrets
source venv/bin/activate
python3 scripts/shopify_edit.py info
```

---

## Quick Test (After Setup)

```bash
# Should return store info without 403 error
curl -X GET \
  "https://trendytreasure-market.myshopify.com/admin/api/2024-01/shop.json" \
  -H "X-Shopify-Access-Token: YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

---

## Alternative: Use Private App (Legacy Method)

If Admin API apps don't work, use Private Apps:

1. Go to **Settings** → **Apps and sales channels**
2. Click **Develop apps** → **Allow private app development**
3. Create **Private app**
4. Enable same scopes as above
5. Copy access token

---

## After Fixing Token

Run product creator again:
```bash
cd ~/neolight
source ~/.neolight_secrets
source venv/bin/activate
python3 agents/automated_product_creator.py
```


# eBay API Setup - Complete Step-by-Step Guide 🔑

## 🎯 **How to Get eBay API Keys (App ID & Cert ID)**

---

## 📋 **STEP-BY-STEP INSTRUCTIONS**

### **Step 1: Go to eBay Developer Portal**

**URL:** https://developer.ebay.com/

**Or:** https://developer.ebay.com/my/keys

---

### **Step 2: Sign In / Register**

1. Click **"Sign in"** (top right)
2. If you don't have account:
   - Click **"Register"**
   - Use your eBay account OR create new developer account
   - **Recommended:** Use your existing eBay seller account

---

### **Step 3: Create Application**

1. After signing in, go to: **"My Account"** → **"Keys"**
   
   **OR directly:** https://developer.ebay.com/my/keys

2. Click **"Create App Key"** or **"Create a new app key"**

3. Fill out the form:

   **App Name:** 
   ```
   NeoLight Dropshipping Bot
   ```
   (or any name you want)

   **App Purpose:**
   ```
   Manage eBay listings and orders automatically
   ```

   **Developer Program Membership:**
   - **Production:** For live, real accounts (select this)
   - **Sandbox:** For testing (skip for now)

   **App Type:**
   - Select **"eBay Application"**

4. Click **"Continue"** or **"Create"**

---

### **Step 4: Get Your Credentials**

After creating the app, you'll see **TWO important keys:**

#### **1. App ID (Client ID):**
```
Looks like: YourApp-PROD-abc123def456-abc-123
```

#### **2. Cert ID (Client Secret):**
```
Looks like: PROD-abc123def456-abc-123-xyz-789
```

**⚠️ IMPORTANT:**
- **Cert ID** is only shown ONCE when you create the app
- **Copy it immediately** or you'll need to regenerate!
- **Save both keys** in a secure place

---

### **Step 5: Configure API Permissions**

1. In the app details page, look for **"OAuth scopes"** or **"Permissions"**

2. Enable these scopes (checkboxes):
   - ✅ **https://api.ebay.com/oauth/api_scope/sell.inventory** (List/manage items)
   - ✅ **https://api.ebay.com/oauth/api_scope/sell.marketplace.account** (Account info)
   - ✅ **https://api.ebay.com/oauth/api_scope/sell.fulfillment** (Manage orders)

3. **Save** the changes

---

### **Step 6: Get OAuth Token (Required for API Calls)**

eBay uses OAuth 2.0, so you need a token:

1. Go to: **"OAuth Tokens"** in your app dashboard

2. Click **"Generate Token"**

3. Select scopes:
   - ✅ sell.inventory
   - ✅ sell.marketplace.account
   - ✅ sell.fulfillment

4. Copy the **Access Token** (long string)

**Note:** Access tokens expire (usually 2 hours)
- You'll need to refresh it periodically
- Or use the refresh token to get new access tokens automatically

---

## 📝 **What You Need to Give Me:**

After completing the steps, provide:

```bash
EBAY_APP_ID="YourApp-PROD-abc123def456-abc-123"
EBAY_CERT_ID="PROD-abc123def456-abc-123-xyz-789"
EBAY_ACCESS_TOKEN="v^1.1#i^1#p^1#r^0#I^3#f^0#t^..."  # Get this separately
EBAY_REFRESH_TOKEN="v^1.1#i^1#p^1#..."  # For auto-refresh
```

**Or just the App ID and Cert ID if you prefer - I can help generate tokens.**

---

## 🔧 **Alternative: Quick Setup Link**

**Direct link to create keys:**
https://developer.ebay.com/my/keys

**If you're already logged in, it goes straight to key creation!**

---

## ⚠️ **Important Notes:**

### **1. Production vs Sandbox:**
- **Production:** Real eBay account, real sales (USE THIS)
- **Sandbox:** Testing only (skip unless testing)

### **2. Account Type:**
- **Personal:** Free, limited API calls
- **Business:** More API calls, better limits

**For dropshipping, Business account is better** (but start with Personal if free)

### **3. API Limits:**
- **Personal:** 5,000 calls per day
- **Business:** 25,000+ calls per day

**For automation, 5,000/day is usually enough!**

---

## 🎯 **Quick Checklist:**

- [ ] Signed in to eBay Developer Portal
- [ ] Created new app
- [ ] Got App ID (Client ID)
- [ ] Got Cert ID (Client Secret) - **SAVED IT!**
- [ ] Generated OAuth Access Token
- [ ] Enabled required permissions/scopes
- [ ] Copied all credentials

---

## 🚀 **After You Get Keys:**

Add them to your secure file:

```bash
nano ~/.neolight_secrets_template
```

Add:
```bash
export EBAY_APP_ID="your_app_id_here"
export EBAY_CERT_ID="your_cert_id_here"
export EBAY_ACCESS_TOKEN="your_token_here"
```

Or just send them to me and I'll configure everything!

---

## 💡 **Troubleshooting:**

### **"I can't find Cert ID":**
- It's shown ONCE when you create the app
- If you missed it, you need to **regenerate** it
- Go to app settings → Regenerate Cert ID

### **"Access Token expired":**
- Tokens expire every 2 hours
- Use Refresh Token to get new one
- Or regenerate in dashboard

### **"API calls not working":**
- Check OAuth scopes are enabled
- Verify App ID and Cert ID are correct
- Make sure using Production keys (not Sandbox)

---

## 📚 **eBay API Documentation:**

**Official Docs:** https://developer.ebay.com/api-docs/static/overview/index.html

**Quick Reference:**
- **Inventory API:** Manage products/listings
- **Fulfillment API:** Manage orders
- **Account API:** Get account info

---

**That's it! Once you have the App ID and Cert ID, you're ready to automate eBay listings!** 🚀


# AutoDS API Key Setup Guide 🔑

## 🎯 **Quick Setup**

After completing the AutoDS → eBay transition, get your API key to connect NeoLight.

---

## 📋 **STEP-BY-STEP: Get AutoDS API Key**

### **Step 1: Log into AutoDS**

1. Go to: https://www.autods.com/
2. Sign in with your AutoDS account

### **Step 2: Navigate to API Settings**

**Option A: Settings Menu**
- Click **"Settings"** (top right or sidebar)
- Look for **"API"**, **"Developer"**, or **"Integrations"**
- Click on it

**Option B: Search**
- Use AutoDS search bar (if available)
- Type: **"API"** or **"API Key"**

**Option C: Direct URL** (if available)
- https://www.autods.com/settings/api
- Or: https://www.autods.com/account/api

### **Step 3: Generate API Key**

1. Click **"Generate API Key"** or **"Create API Key"**
2. Give it a name: `NeoLight Integration` (or any name you prefer)
3. **Copy the API key immediately** - it's only shown once!

**⚠️ IMPORTANT:**
- API keys are shown only once
- Copy it to a secure location immediately
- If you lose it, you'll need to regenerate

### **Step 4: Note API Permissions**

AutoDS API typically allows:
- ✅ Read products/listings
- ✅ Read orders
- ✅ Create listings (may require permission)
- ✅ Update inventory

Verify which permissions are enabled for your key.

---

## 🔧 **STEP-BY-STEP: Configure NeoLight**

### **Step 1: Add API Key to Environment**

```bash
# Open your secrets file
nano ~/.neolight_secrets_template

# Add AutoDS API key
export AUTODS_API_KEY="your_api_key_here"

# Save and exit (Ctrl+X, Y, Enter)
```

### **Step 2: Load Environment Variables**

```bash
# Load the secrets
source ~/.neolight_secrets_template

# Verify it's loaded
echo $AUTODS_API_KEY
```

### **Step 3: Set Platform Preference**

```bash
# Set to use eBay (via AutoDS) - recommended for safety
export DROPSHIP_PLATFORM="ebay"

# Or use Shopify if preferred
# export DROPSHIP_PLATFORM="shopify"
```

### **Step 4: Test Connection**

```bash
cd ~/neolight

# Test AutoDS connection
python3 -c "from agents.autods_integration import test_autods_connection; test_autods_connection()"
```

**Expected Output:**
```
============================================================
AutoDS API Integration Test
============================================================

1. Testing connection...
[autods_integration] ✅ Connected to AutoDS API
[autods_integration] Account: YourAccountName

2. Getting connected stores...
[autods_integration] Found 1 connected stores
   - ebay: seakin67

✅ AutoDS integration test complete!
```

---

## 📝 **Environment Variables Reference**

Add these to `~/.neolight_secrets_template`:

```bash
# AutoDS API (Required for eBay automation)
export AUTODS_API_KEY="your_autods_api_key_here"

# Platform preference
export DROPSHIP_PLATFORM="ebay"  # or "shopify"

# eBay account info (for reference, not required for API)
export EBAY_USERNAME="seakin67"
```

---

## ✅ **Verification Checklist**

After setup:

- [ ] AutoDS API key generated
- [ ] API key saved to `~/.neolight_secrets_template`
- [ ] Environment variable loaded (`echo $AUTODS_API_KEY` shows key)
- [ ] `DROPSHIP_PLATFORM="ebay"` set
- [ ] Test connection script runs successfully
- [ ] eBay store visible in test output

---

## 🆘 **Troubleshooting**

### **"I can't find API settings in AutoDS"**

**Possible reasons:**
1. Your plan doesn't include API access
   - **Solution:** Contact AutoDS support to enable API
   - Or upgrade to a plan that includes API

2. API settings in different location
   - **Solution:** Check all Settings submenus
   - Contact AutoDS support for exact location

3. API not available yet
   - **Solution:** Some accounts need API approval
   - Contact support to request API access

### **"API key not working / connection failed"**

1. **Verify key is correct:**
   ```bash
   echo $AUTODS_API_KEY
   # Should show your key (not empty)
   ```

2. **Check key format:**
   - Should be a long string (usually 32+ characters)
   - No spaces or extra characters

3. **Test manually:**
   ```bash
   # Try direct API call (adjust endpoint if needed)
   curl -H "Authorization: Bearer $AUTODS_API_KEY" \
        https://api.autods.com/v1/account
   ```

4. **Check AutoDS API documentation:**
   - Base URL might be different
   - Endpoint paths might vary
   - Update `agents/autods_integration.py` if needed

### **"eBay store not found"**

**Possible reasons:**
1. eBay account not connected in AutoDS
   - **Solution:** Go back to Step 3 in transition guide
   - Reconnect eBay account

2. Store connection expired
   - **Solution:** Reconnect eBay account in AutoDS

### **"Import product failed"**

1. **Check permissions:**
   - API key may not have "create listings" permission
   - Contact AutoDS support to enable

2. **Verify product ID:**
   - Product must exist in AutoDS catalog
   - Search must return valid product

3. **Check AutoDS settings:**
   - Auto-fulfillment must be enabled
   - Profit settings must be configured

---

## 📚 **API Documentation**

**AutoDS API Docs:**
- Check AutoDS dashboard → Help → API Documentation
- Or contact AutoDS support for API documentation URL

**Note:** AutoDS API endpoints may vary. The integration script (`agents/autods_integration.py`) uses standard REST API patterns. If endpoints differ, update the script accordingly.

---

## 🎯 **What Happens After Setup**

Once API key is configured:

1. **NeoLight can:**
   - Search products in AutoDS catalog
   - Import products to eBay (via AutoDS)
   - Monitor orders from eBay
   - Track revenue and profits

2. **AutoDS handles:**
   - All eBay API calls (safe middleware)
   - Rate limiting
   - Listing format compliance
   - Auto-fulfillment when orders come in

3. **You:**
   - Monitor dashboard
   - Adjust settings as needed
   - Scale up gradually

---

## 🔒 **Security Best Practices**

1. **Never commit API keys to git:**
   - Keep in `~/.neolight_secrets_template` (already gitignored)
   - Don't share API keys publicly

2. **Rotate keys periodically:**
   - Generate new key every 3-6 months
   - Revoke old keys in AutoDS settings

3. **Monitor API usage:**
   - Check AutoDS dashboard for unusual activity
   - Set up alerts if available

---

## ✅ **Quick Reference**

```bash
# Set up API key
export AUTODS_API_KEY="your_key"
export DROPSHIP_PLATFORM="ebay"

# Test connection
python3 agents/autods_integration.py

# Run dropship agent
python3 agents/dropship_agent.py
```

---

**That's it! Once your API key is configured, NeoLight can safely automate eBay through AutoDS!** 🚀


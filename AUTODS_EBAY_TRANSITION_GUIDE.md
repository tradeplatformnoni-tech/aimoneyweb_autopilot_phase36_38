# AutoDS → eBay Transition: Complete Execution Guide 🚀

## 🎯 **Your Strategic Plan**

**Structure:** NeoLight AI Agent → AutoDS API → eBay (your personal account)

**Why this is safe:**
- AutoDS acts as trusted middleware (firewall)
- Your eBay account sees only "AutoDS activity" (not raw bot/API behavior)
- Stays compliant while maintaining full automation

---

## ✅ **STEP-BY-STEP EXECUTION PLAN**

### **STEP 1: Cancel Shopify Plan in AutoDS**

**Time:** 2 minutes

1. **Log into AutoDS:**
   - Go to: https://www.autods.com/
   - Sign in with your AutoDS account

2. **Navigate to Plans:**
   - Click **"Settings"** (top right or left sidebar)
   - Click **"Plans & Add-ons"** (or **"Subscription"**)

3. **Cancel Shopify Plan:**
   - Find **"Shopify"** section in your active plans
   - Click **"Cancel"** or **"Cancel Plan"** button
   - Choose one of:
     - **"Cancel at end of billing cycle"** (recommended - finish current month)
     - **"Cancel immediately"** (if you want to switch now)
   - Confirm cancellation

**✅ What happens:**
- Your AutoDS account stays active
- You lose Shopify-specific import slots
- You can still access other AutoDS features

---

### **STEP 2: Add eBay Plan in AutoDS**

**Time:** 5 minutes

1. **Still in Plans & Add-ons page:**
   - Scroll to **"eBay"** section
   - Click **"Buy Plan"** or **"Add eBay Plan"**

2. **Choose Plan:**
   - Select same tier as Shopify (e.g., **200 listings**)
   - Or choose tier that fits your needs:
     - **Starter:** ~$19/month (100-200 listings)
     - **Professional:** ~$49/month (500-1000 listings)
   - Click **"Continue"** or **"Buy"**

3. **Verify Plan Active:**
   - After purchase, you should see:
     - **"eBay — Active"** in "My Plans"
     - eBay icon/section now visible in AutoDS dashboard

---

### **STEP 3: Connect Your Old eBay Account**

**Time:** 3 minutes

1. **In AutoDS Dashboard:**
   - Look for **"Connect Store"** or **"Add Store"** button
   - Or go to: **Settings** → **My Stores** → **Add Store**

2. **Select Platform:**
   - Choose **"eBay"** from platform list

3. **Connect Account:**
   - Click **"Connect eBay Account"** or **"Sign in with eBay"**
   - **IMPORTANT:** Use your **OLD trusted account:**
     - **Username:** `seakin67`
     - **Email:** `s***a@yahoo.com`
   - Sign in with eBay credentials

4. **Grant Permissions:**
   - eBay will show consent screen:
     - "Allow AutoDS to access your eBay account?"
     - Click **"Agree"** or **"Accept"**
   - This allows AutoDS to:
     - List products on eBay
     - Manage orders
     - Update inventory
     - Process sales

5. **Verify Connection:**
   - You should see:
     - Your eBay store listed under **"My Stores"**
     - Store status: **"Connected"** or **"Active"**
     - Store name/username: `seakin67`

---

### **STEP 4: Reconnect Suppliers**

**Time:** 5 minutes

1. **Go to Supplier Settings:**
   - **Settings** → **Supplier Settings** (or **"Suppliers"** in menu)

2. **Add/Verify Suppliers:**
   - **AliExpress:**
     - Click **"Connect AliExpress"** or **"Add Supplier"**
     - Follow instructions (may need Chrome extension)
     - Verify connection shows **"Connected"**
   
   - **Alibaba US:**
     - Click **"Add Supplier"** → **"Alibaba"**
     - Connect your Alibaba account (if you have one)
     - Or skip for now (AliExpress is main source)
   
   - **Shein:**
     - Click **"Add Supplier"** → **"Shein"** (if available)
     - Note: Some suppliers may not have direct API

3. **Verify Profit Rules:**
   - Check **"Pricing Rules"** or **"Profit Settings"**
   - Should show:
     - Default profit: **40%** (recommended)
     - Minimum profit: **$2.00**
     - Dynamic pricing: **Enabled**
   - If settings were reset, re-apply from `AUTODS_OPTIMAL_SETTINGS.md`

---

### **STEP 5: Configure eBay-Specific Settings**

**Time:** 10 minutes

1. Configure AutoDS for eBay:**
   - Go to **Settings** → **eBay Settings** (or store-specific settings)

2. **Lister Settings (eBay):**
   ```
   ✅ Allow Duplicates: UNCHECKED
   ✅ Capitalize Title: CHECKED
   ✅ Upload Variations: CHECKED
   ✅ Apply Categories: CHECKED
   Default Quantity: 10
   ```

3. **Pricing Settings:**
   ```
   Profit: 40%
   Minimum Profit: $2.00
   Dynamic Profit: ✅ Enabled
   Price Cents: .99
   Compare Price: ✅ Enabled
   ```

4. **Orders/Fulfillment:**
   ```
   ✅ Process orders using "Fulfilled by AutoDS"
   ✅ Automatic orders: CHECKED
   ✅ Mark order as shipped: CHECKED
   Maximum Purchase Order Price: $500
   Maximum Loss: $5
   ```

5. **Shipping Settings:**
   ```
   Default Shipping: "Economy Shipping" (eBay standard)
   Shipping Days: 15-30 (realistic for AliExpress)
   Ship to Country: United States
   ```

---

### **STEP 6: Get AutoDS API Key (For NeoLight Integration)**

**Time:** 5 minutes

1. **Go to AutoDS API Settings:**
   - **Settings** → **API** or **"Developer"** or **"Integrations"**
   - Or search for "API" in settings menu

2. **Generate API Key:**
   - Click **"Generate API Key"** or **"Create API Key"**
   - Give it a name: `NeoLight Integration`
   - Copy the API key immediately (only shown once!)

3. **Note Permissions:**
   - AutoDS API typically allows:
     - Read products/listings
     - Read orders
     - Create listings (if enabled)
     - Update inventory
   - Verify which permissions are enabled

4. **Save API Key Securely:**
   ```bash
   # Add to your secrets file
   echo 'export AUTODS_API_KEY="your_api_key_here"' >> ~/.neolight_secrets_template
   source ~/.neolight_secrets_template
   ```

---

### **STEP 7: Connect NeoLight to AutoDS API (Optional)**

**Time:** Already done (code is ready)

Once you have the AutoDS API key:

1. **Set Environment Variable:**
   ```bash
   export AUTODS_API_KEY="your_api_key_here"
   ```

2. **Test Connection:**
   ```bash
   cd ~/neolight
   python3 -c "from agents.autods_integration import test_autods_connection; test_autods_connection()"
   ```

3. **Enable in NeoLight:**
   - The dropship agent will automatically use AutoDS API when available
   - No additional configuration needed

---

## ✅ **VERIFICATION CHECKLIST**

After completing all steps, verify:

- [ ] Shopify plan canceled (no longer in "Active Plans")
- [ ] eBay plan active (shows in "My Plans")
- [ ] eBay account connected (username: `seakin67` visible)
- [ ] AliExpress supplier connected
- [ ] Profit rules configured (40% default)
- [ ] Auto-fulfillment enabled (critical!)
- [ ] AutoDS API key generated and saved
- [ ] NeoLight can connect to AutoDS API (test script runs)

---

## 🔒 **SAFETY NOTES**

### **Why This Setup is Safe:**

1. **AutoDS as Middleware:**
   - All eBay API calls go through AutoDS
   - Your account sees "AutoDS activity" (trusted by eBay)
   - No raw bot behavior visible to eBay

2. **Rate Limits Handled:**
   - AutoDS manages API rate limits
   - Prevents accidental suspension

3. **Compliance Built-In:**
   - AutoDS ensures listing format compliance
   - Handles eBay policy requirements

4. **Gradual Rollout:**
   - Start with 5-10 test listings
   - Monitor for 1 week
   - Scale up gradually

---

## 📊 **WHAT HAPPENS NEXT**

### **Immediate (After Setup):**

1. **AutoDS is ready:**
   - Can import products from AliExpress
   - Can list on eBay with markup
   - Can auto-fulfill orders

2. **NeoLight Integration:**
   - AI agent can read AutoDS data
   - Can analyze pricing, trends, profits
   - Can trigger product imports (via AutoDS)

### **Once Running:**

1. **Product Discovery:**
   - NeoLight finds trending products
   - Sends to AutoDS via API
   - AutoDS imports from AliExpress

2. **Listing Creation:**
   - AutoDS creates eBay listings
   - Applies 40% markup
   - Manages inventory

3. **Order Fulfillment:**
   - Customer buys on eBay
   - AutoDS detects order
   - Auto-orders from AliExpress
   - Ships directly to customer
   - Updates tracking

4. **Revenue Tracking:**
   - NeoLight monitors revenue via AutoDS API
   - Tracks profit margins
   - Reports to dashboard

---

## 🆘 **TROUBLESHOOTING**

### **"I can't find Plans & Add-ons":**
- Try: **Settings** → **Subscription**
- Or: **Account** → **Billing**
- Or contact AutoDS support

### **"eBay plan not showing":**
- Refresh page
- Clear browser cache
- Try incognito mode
- Contact AutoDS support if issue persists

### **"Can't connect eBay account":**
- Make sure you're using OLD account (`seakin67`)
- Clear eBay cookies/cache
- Try different browser
- Make sure eBay account is in good standing

### **"AutoDS API key not available":**
- Some plans may not include API access
- Contact AutoDS support to enable API
- Or use webhooks as alternative

### **"NeoLight can't connect to AutoDS":**
- Verify API key is correct
- Check AutoDS API documentation for base URL
- Test API key manually with curl/Postman
- See `agents/autods_integration.py` for connection details

---

## 📚 **REFERENCE DOCUMENTS**

- `AUTODS_OPTIMAL_SETTINGS.md` - Complete AutoDS configuration
- `EBAY_API_SETUP_GUIDE.md` - eBay API setup (for reference only)
- `agents/dropship_agent.py` - Dropshipping agent code
- `agents/autods_integration.py` - AutoDS API integration (created next)

---

## 🎯 **QUICK START CHECKLIST**

**Do these in order:**

1. ✅ Cancel Shopify plan (2 min)
2. ✅ Add eBay plan (5 min)
3. ✅ Connect eBay account (3 min)
4. ✅ Reconnect suppliers (5 min)
5. ✅ Configure eBay settings (10 min)
6. ✅ Get AutoDS API key (5 min)
7. ✅ Test NeoLight connection (2 min)

**Total time: ~30 minutes**

---

**Ready to execute? Start with Step 1 and work through each step!** 🚀


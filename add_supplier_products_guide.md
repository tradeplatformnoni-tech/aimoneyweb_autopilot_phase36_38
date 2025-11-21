# 📦 Add Products Using Supplier URLs/IDs - Complete Guide

## 🎯 **Workflow Overview**

The script follows this exact workflow:
1. ✅ Login to AutoDS
2. ✅ Navigate to "Add Products"
3. ✅ Select "Multiple Products/Stores"
4. ✅ Paste Supplier URLs or Product IDs
5. ✅ Add as Draft
6. ✅ Import to eBay

---

## 🔗 **Your Suppliers**

The script uses these 5 suppliers:
- ✅ **AliExpress US**
- ✅ **AliExpress CN**
- ✅ **CJDropshipping US**
- ✅ **Alibaba US**
- ✅ **AutoDS Sourcing CN**

---

## 📋 **How to Use**

### **Option 1: Run with Example Data**

```bash
cd ~/neolight
python3 import_products_supplier_workflow.py
```

This will:
- Auto-login to AutoDS
- Navigate to Add Products
- Follow the exact workflow you described
- Use example supplier URLs (you can replace with real ones)

---

### **Option 2: Add Real Supplier URLs/IDs**

Edit the script and add your actual product URLs or IDs:

```python
TRENDING_PRODUCTS = [
    {
        "name": "Camera Lens",
        "supplier": "AliExpress US",
        "url_or_id": "https://www.aliexpress.com/item/4001234567890.html",  # Real URL
        "keywords": ["camera lens"]
    },
    {
        "name": "Phone Case",
        "supplier": "AliExpress CN",
        "url_or_id": "12345678",  # Or Product ID
        "keywords": ["phone case"]
    }
]
```

---

## 🛡️ **VERO Protection**

All products are automatically checked for VERO violations:
- ✅ Blocked keywords replaced (iPhone → smartphone, etc.)
- ✅ Your eBay account (seakin67-us) protected
- ✅ No manual intervention needed

---

## 📊 **Workflow Steps**

### **Step 1: Login** ✅
- Auto-detects login page
- Fills email/password
- Handles Google OAuth automatically

### **Step 2: Add Products** ✅
- Navigates to "Add Products" section
- Finds the page automatically

### **Step 3: Multiple Products/Stores** ✅
- Selects "Multiple Products/Stores" option
- Handles different page layouts

### **Step 4: Paste URLs/IDs** ✅
- Finds input field (textarea or input)
- Pastes supplier URLs or Product IDs
- Supports multiple products (one per line)

### **Step 5: Add as Draft** ✅
- Clicks "Add as Draft" button
- Saves products to drafts

### **Step 6: Import to eBay** ✅
- Navigates to drafts page
- Finds import buttons
- Imports all drafts to eBay

---

## 🔍 **Finding Supplier URLs/Product IDs**

### **From AliExpress:**
1. Go to product page
2. Copy full URL from address bar
   - Example: `https://www.aliexpress.com/item/4001234567890.html`

### **From AutoDS:**
1. Search for product in AutoDS catalog
2. Copy Product ID from URL or product details

### **From CJDropshipping:**
1. Find product in CJDropshipping
2. Copy product URL or ID

---

## ✅ **Expected Results**

After running:
- ✅ Products saved as drafts in AutoDS
- ✅ Products imported to eBay
- ✅ All VERO-protected
- ✅ Ready for sales

**Check:**
- AutoDS Dashboard → Products → Drafts
- AutoDS Dashboard → Listings → eBay
- eBay Store → Active Listings

---

## 🚨 **Troubleshooting**

### **Input Field Not Found:**
- Script will use JavaScript fallback
- Check screenshot: `step4_urls_pasted.png`

### **Multiple Products Option Not Found:**
- Script searches for multiple variations
- Check screenshot: `step3_multiple_selected.png`

### **Import Buttons Not Found:**
- Script tries multiple selectors
- May need to manually click in browser

---

## 📸 **Screenshots Saved**

The script saves screenshots at each step:
- `step1_login_complete.png`
- `step2_add_products_page.png`
- `step3_multiple_selected.png`
- `step4_urls_pasted.png`
- `step5_draft_added.png`
- `step6_ebay_import.png`

Check these if anything goes wrong!

---

## 🚀 **Ready to Run**

```bash
cd ~/neolight
python3 import_products_supplier_workflow.py
```

**The script will:**
- Auto-login
- Follow your exact workflow
- Use your 5 suppliers
- Import to eBay automatically
- Protect with VERO compliance

---

**Everything is automated! Just run the script and it will follow your exact workflow!** 🎉


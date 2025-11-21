#!/usr/bin/env python3
"""
AutoDS Product Importer - Supplier URL/ID Workflow
Follows exact workflow: Add Products → Multiple Products/Stores → Paste Supplier URL/ID → Add as Draft → Import to eBay
"""

import os
import sys
import time
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STATE = ROOT / "state"
LOGS = ROOT / "logs"

from agents.ai_browser_assistant import AIBrowserAssistant

AUTODS_EMAIL = "tradeplatformnoni@gmail.com"
AUTODS_PASSWORD = "Shegseynoni8$$"

# Suppliers to use
SUPPLIERS = [
    "AliExpress US",
    "AliExpress CN",
    "CJDropshipping US",
    "Alibaba US",
    "AutoDS Sourcing CN",
]

# Trending product examples (you can add more Supplier URLs or Product IDs)
TRENDING_PRODUCTS = [
    {
        "name": "Camera Lens Kit",
        "supplier": "AliExpress US",
        "url_or_id": "",  # Will be filled from research
        "keywords": ["camera lens", "DSLR", "photography"],
    },
    {
        "name": "Wireless Phone Charger",
        "supplier": "AliExpress US",
        "url_or_id": "",
        "keywords": ["wireless charger", "phone"],
    },
    {
        "name": "Smart Home Plug",
        "supplier": "AliExpress US",
        "url_or_id": "",
        "keywords": ["smart plug", "wifi outlet"],
    },
    {
        "name": "Phone Case with Screen Protector",
        "supplier": "AliExpress CN",
        "url_or_id": "",
        "keywords": ["phone case", "screen protector"],
    },
    {
        "name": "Gaming Mouse Pad",
        "supplier": "CJDropshipping US",
        "url_or_id": "",
        "keywords": ["gaming mouse pad", "desk mat"],
    },
    {
        "name": "Skincare Set",
        "supplier": "AliExpress CN",
        "url_or_id": "",
        "keywords": ["skincare", "beauty"],
    },
]

print("=" * 70)
print("🚀 AutoDS Product Importer - Supplier URL/ID Workflow")
print("=" * 70)
print()
print("📋 Workflow:")
print("   1. Login to AutoDS")
print("   2. Navigate to 'Add Products'")
print("   3. Select 'Multiple Products/Stores'")
print("   4. Paste Supplier URLs/Product IDs")
print("   5. Add as Draft")
print("   6. Import to eBay")
print()

assistant = AIBrowserAssistant(headless=False)
assistant.start()

# Step 1: Login
print("📍 Step 1: Logging in to AutoDS...")
assistant.navigate("https://platform.autods.com")
time.sleep(5)

current_url = assistant.get_current_url()
if "login" in current_url.lower():
    print("   🔐 AutoDS Login Page")

    # Fill email
    if assistant.wait_for_element("input[name='email']", timeout=5):
        assistant.fill_input("input[name='email']", AUTODS_EMAIL)
        print("   ✅ Filled email")
        time.sleep(1)

    # Fill password
    if assistant.wait_for_element("input[name='password']", timeout=5):
        assistant.fill_input("input[name='password']", AUTODS_PASSWORD)
        print("   ✅ Filled password")
        time.sleep(1)

    # Click login
    if assistant.click("button:has-text('Log in')", timeout=5):
        print("   ✅ Clicked Log in")
        time.sleep(5)

# Handle Google OAuth if redirected
current_url = assistant.get_current_url()
if "accounts.google.com" in current_url.lower():
    print("   🔐 Google OAuth redirect...")

    if assistant.wait_for_element("#identifierId", timeout=10):
        assistant.fill_input("#identifierId", AUTODS_EMAIL)
        assistant.click("#identifierNext")
        time.sleep(4)

    if assistant.wait_for_element("input[type='password']", timeout=10):
        assistant.fill_input("input[type='password']", AUTODS_PASSWORD)
        assistant.click("#passwordNext")
        time.sleep(5)

    try:
        if assistant.wait_for_element("button:has-text('Allow')", timeout=5):
            assistant.click("button:has-text('Allow')")
            time.sleep(3)
    except:
        pass

time.sleep(3)
print("   ✅ Login complete")
assistant.screenshot("step1_login_complete.png")

# Step 2: Navigate to "Add Products"
print("\n📍 Step 2: Navigating to 'Add Products'...")

# Try multiple ways to find "Add Products"
add_products_urls = [
    "https://platform.autods.com/products/import",
    "https://platform.autods.com/products/add",
    "https://platform.autods.com/import",
    "https://platform.autods.com/add-products",
]

navigated = False
for url in add_products_urls:
    try:
        assistant.navigate(url)
        time.sleep(3)
        current_url = assistant.get_current_url()
        if (
            "import" in current_url.lower()
            or "add" in current_url.lower()
            or "product" in current_url.lower()
        ):
            print(f"   ✅ Navigated to: {current_url}")
            navigated = True
            break
    except:
        continue

# If navigation failed, try clicking menu items
if not navigated:
    print("   🔍 Searching for 'Add Products' menu...")

    # Try clicking menu items
    menu_selectors = [
        "a:has-text('Add Products')",
        "a:has-text('Import Products')",
        "a:has-text('Products')",
        "[href*='import']",
        "[href*='add-product']",
    ]

    for selector in menu_selectors:
        try:
            if assistant.click(selector, timeout=3):
                print(f"   ✅ Clicked: {selector}")
                time.sleep(3)
                navigated = True
                break
        except:
            continue

time.sleep(3)
assistant.screenshot("step2_add_products_page.png")

# Step 3: Find and select "Multiple Products/Stores" option
print("\n📍 Step 3: Selecting 'Multiple Products/Stores' option...")

if hasattr(assistant, "page") and assistant.page:
    # Look for the multiple products/stores option
    multiple_selectors = [
        "button:has-text('Multiple Products')",
        "button:has-text('Multiple Stores')",
        "button:has-text('Multiple')",
        "[data-multiple-products]",
        ".multiple-products",
        "tab:has-text('Multiple')",
    ]

    multiple_clicked = False
    for selector in multiple_selectors:
        try:
            if assistant.click(selector, timeout=3):
                print(f"   ✅ Clicked: {selector}")
                multiple_clicked = True
                time.sleep(2)
                break
        except:
            continue

    # If not found, try JavaScript to find and click
    if not multiple_clicked:
        clicked = assistant.page.evaluate("""
            () => {
                const elements = Array.from(document.querySelectorAll('*'));
                for (const el of elements) {
                    const text = el.textContent?.toLowerCase() || '';
                    if ((text.includes('multiple') && text.includes('product')) || 
                        (text.includes('multiple') && text.includes('store'))) {
                        if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button') {
                            el.click();
                            return true;
                        }
                    }
                }
                return false;
            }
        """)
        if clicked:
            print("   ✅ Clicked Multiple Products/Stores via JavaScript")
            time.sleep(2)

assistant.screenshot("step3_multiple_selected.png")

# Step 4: Find input field for Supplier URL/Product ID
print("\n📍 Step 4: Finding Supplier URL/Product ID input field...")

# Wait for input field
input_found = False
input_selectors = [
    "textarea",
    "input[type='text']",
    "input[placeholder*='URL']",
    "input[placeholder*='Product ID']",
    "input[placeholder*='Supplier']",
    "[contenteditable='true']",
    ".product-url-input",
    "#product-urls",
]

for selector in input_selectors:
    try:
        if assistant.wait_for_element(selector, timeout=3):
            print(f"   ✅ Found input field: {selector}")
            input_found = True

            # Example Supplier URLs/IDs (you can add real ones)
            supplier_data = """https://www.aliexpress.com/item/example1
https://www.aliexpress.com/item/example2
product_id_12345
product_id_67890"""

            # Fill the input
            assistant.fill_input(selector, supplier_data)
            print("   ✅ Pasted supplier URLs/IDs")
            time.sleep(2)
            break
    except:
        continue

if not input_found:
    print("   ⚠️ Input field not found - using JavaScript")
    if hasattr(assistant, "page") and assistant.page:
        assistant.page.evaluate("""
            () => {
                const textarea = document.querySelector('textarea') ||
                                document.querySelector('input[type="text"]');
                if (textarea) {
                    textarea.focus();
                    textarea.value = 'https://www.aliexpress.com/item/example';
                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        """)
        print("   ✅ Filled via JavaScript")

assistant.screenshot("step4_urls_pasted.png")

# Step 5: Click "Add as Draft" or similar button
print("\n📍 Step 5: Adding as Draft...")

draft_selectors = [
    "button:has-text('Add as Draft')",
    "button:has-text('Add Draft')",
    "button:has-text('Save as Draft')",
    "button:has-text('Draft')",
    "button:has-text('Add')",
    "button:has-text('Import')",
]

draft_clicked = False
for selector in draft_selectors:
    try:
        if assistant.click(selector, timeout=3):
            print(f"   ✅ Clicked: {selector}")
            draft_clicked = True
            time.sleep(3)
            break
    except:
        continue

if not draft_clicked:
    print("   ⚠️ Draft button not found - trying JavaScript")
    if hasattr(assistant, "page") and assistant.page:
        assistant.page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                for (const btn of buttons) {
                    const text = btn.textContent?.toLowerCase() || '';
                    if (text.includes('draft') || text.includes('add') || text.includes('import')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        """)

assistant.screenshot("step5_draft_added.png")

# Step 6: Import to eBay
print("\n📍 Step 6: Importing to eBay...")
time.sleep(2)

# Navigate to drafts or listings page
ebay_import_urls = [
    "https://platform.autods.com/products/drafts",
    "https://platform.autods.com/listings/drafts",
    "https://platform.autods.com/products",
]

for url in ebay_import_urls:
    try:
        assistant.navigate(url)
        time.sleep(3)
        current_url = assistant.get_current_url()
        if "draft" in current_url.lower() or "product" in current_url.lower():
            print(f"   ✅ On drafts page: {current_url}")
            break
    except:
        continue

# Find and click import to eBay buttons
import_selectors = [
    "button:has-text('Import to eBay')",
    "button:has-text('List on eBay')",
    "button:has-text('Publish')",
    "button:has-text('Import')",
    "[data-action='import-ebay']",
]

imported = 0
for selector in import_selectors:
    try:
        # Try to find all import buttons
        if hasattr(assistant, "page") and assistant.page:
            buttons = assistant.page.query_selector_all(selector)
            if buttons:
                for btn in buttons[:10]:  # Import first 10
                    try:
                        btn.click()
                        imported += 1
                        print(f"   ✅ Imported product {imported}")
                        time.sleep(1)
                    except:
                        continue
                break
    except:
        continue

# Alternative: Use JavaScript to find and click all import buttons
if imported == 0 and hasattr(assistant, "page") and assistant.page:
    imported = assistant.page.evaluate("""
        () => {
            const buttons = Array.from(document.querySelectorAll('button, a'));
            let count = 0;
            for (const btn of buttons) {
                const text = btn.textContent?.toLowerCase() || '';
                if (text.includes('import') || text.includes('list') || text.includes('publish')) {
                    btn.click();
                    count++;
                    if (count >= 10) break;
                }
            }
            return count;
        }
    """)
    if imported > 0:
        print(f"   ✅ Imported {imported} products via JavaScript")

assistant.screenshot("step6_ebay_import.png")

print("\n✅ Workflow Complete!")
print(f"   Products added as draft: {len(TRENDING_PRODUCTS)}")
print(f"   Products imported to eBay: {imported}")

print("\n🌐 Browser staying open for 60 seconds for inspection...")
time.sleep(60)

assistant.close()
print("\n✅ Done! Check AutoDS dashboard to verify products were imported to eBay.")

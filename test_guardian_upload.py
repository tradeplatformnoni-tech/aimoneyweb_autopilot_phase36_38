#!/usr/bin/env python3
"""
Guardian Mode Test - Upload Products Tonight
Quick test to upload a couple products using your exact workflow
"""

import os
import sys
import time
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.ai_browser_assistant import AIBrowserAssistant

AUTODS_EMAIL = "tradeplatformnoni@gmail.com"
AUTODS_PASSWORD = "Shegseynoni8$$"

# Test products - ADD YOUR REAL SUPPLIER URLs/IDs HERE
TEST_PRODUCTS = [
    {
        "name": "Camera Lens Kit",
        "supplier": "AliExpress US",
        "url_or_id": "https://www.aliexpress.com/item/example1",  # Replace with real URL
        "vero_safe": True,
    },
    {
        "name": "Wireless Phone Charger",
        "supplier": "AliExpress US",
        "url_or_id": "https://www.aliexpress.com/item/example2",  # Replace with real URL
        "vero_safe": True,
    },
]

print("=" * 70)
print("🧪 Guardian Mode Test - Upload Products Tonight")
print("=" * 70)
print()
print("📋 Products to upload:")
for idx, prod in enumerate(TEST_PRODUCTS, 1):
    print(f"   {idx}. {prod['name']} ({prod['supplier']})")
print()
print("💡 Replace example URLs with real supplier URLs/IDs")
print()

# Start browser
browser = AIBrowserAssistant(headless=False)
browser.start()

print("📍 Step 1: Logging into AutoDS...")

browser.navigate("https://platform.autods.com")
time.sleep(3)

current_url = browser.get_current_url()

if "login" in current_url.lower():
    # Fill login form
    if browser.wait_for_element("input[name='email']", timeout=5):
        browser.fill_input("input[name='email']", AUTODS_EMAIL)
        print("   ✅ Filled email")
        time.sleep(1)

    if browser.wait_for_element("input[name='password']", timeout=5):
        browser.fill_input("input[name='password']", AUTODS_PASSWORD)
        print("   ✅ Filled password")
        time.sleep(1)

    if browser.click("button:has-text('Log in')", timeout=5):
        print("   ✅ Clicked Log in")
        time.sleep(5)

# Handle Google OAuth
current_url = browser.get_current_url()
if "accounts.google.com" in current_url.lower():
    print("   🔐 Google OAuth...")

    if browser.wait_for_element("#identifierId", timeout=10):
        browser.fill_input("#identifierId", AUTODS_EMAIL)
        browser.click("#identifierNext")
        time.sleep(4)

    if browser.wait_for_element("input[type='password']", timeout=10):
        browser.fill_input("input[type='password']", AUTODS_PASSWORD)
        browser.click("#passwordNext")
        time.sleep(5)

    try:
        if browser.wait_for_element("button:has-text('Allow')", timeout=3):
            browser.click("button:has-text('Allow')")
            time.sleep(3)
    except:
        pass

print("   ✅ Login complete")
time.sleep(2)

# Step 2: Navigate to Add Products
print("\n📍 Step 2: Navigating to 'Add Products'...")

add_products_url = "https://platform.autods.com/products/import"
browser.navigate(add_products_url)
time.sleep(5)

current_url = browser.get_current_url()
print(f"   Current URL: {current_url}")

# Step 3: Select Multiple Products/Stores
print("\n📍 Step 3: Selecting 'Multiple Products/Stores'...")

if hasattr(browser, "page") and browser.page:
    # Try to find and click Multiple option
    multiple_clicked = browser.page.evaluate("""
        () => {
            const elements = Array.from(document.querySelectorAll('*'));
            for (const el of elements) {
                const text = el.textContent?.toLowerCase() || '';
                if (text.includes('multiple') && (text.includes('product') || text.includes('store'))) {
                    if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button') {
                        el.click();
                        return true;
                    }
                }
            }
            return false;
        }
    """)

    if multiple_clicked:
        print("   ✅ Selected Multiple Products/Stores")
        time.sleep(2)
    else:
        print("   ⚠️ Multiple option not found - continuing anyway")

# Step 4: Paste Supplier URLs
print("\n📍 Step 4: Pasting Supplier URLs/IDs...")

if hasattr(browser, "page") and browser.page:
    # Find textarea or input field
    urls = [prod["url_or_id"] for prod in TEST_PRODUCTS]
    urls_text = "\n".join(urls)

    filled = browser.page.evaluate(
        """
        (urls) => {
            const textarea = document.querySelector('textarea') ||
                            document.querySelector('input[type="text"]') ||
                            document.querySelector('[contenteditable="true"]');
            
            if (textarea) {
                textarea.focus();
                textarea.value = urls;
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                textarea.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }
            return false;
        }
    """,
        urls_text,
    )

    if filled:
        print(f"   ✅ Pasted {len(TEST_PRODUCTS)} supplier URLs/IDs")
        time.sleep(2)
    else:
        print("   ⚠️ Input field not found - you may need to paste manually")
        print(f"   📋 URLs to paste:\n{urls_text}")

# Step 5: Add as Draft
print("\n📍 Step 5: Adding as Draft...")

if hasattr(browser, "page") and browser.page:
    draft_clicked = browser.page.evaluate("""
        () => {
            const buttons = Array.from(document.querySelectorAll('button'));
            for (const btn of buttons) {
                const text = btn.textContent?.toLowerCase() || '';
                if (text.includes('draft') || text.includes('add')) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }
    """)

    if draft_clicked:
        print("   ✅ Clicked Add as Draft")
        time.sleep(3)
    else:
        print("   ⚠️ Draft button not found - you may need to click manually")

# Step 6: Import to eBay
print("\n📍 Step 6: Importing to eBay...")

browser.navigate("https://platform.autods.com/products/drafts")
time.sleep(5)

if hasattr(browser, "page") and browser.page:
    import_count = browser.page.evaluate("""
        () => {
            const buttons = Array.from(document.querySelectorAll('button, a'));
            let count = 0;
            for (const btn of buttons) {
                const text = btn.textContent?.toLowerCase() || '';
                if (text.includes('import') || text.includes('list') || text.includes('ebay')) {
                    btn.click();
                    count++;
                    if (count >= 10) break;
                }
            }
            return count;
        }
    """)

    if import_count > 0:
        print(f"   ✅ Imported {import_count} products to eBay")
    else:
        print("   ⚠️ Import buttons not found - check drafts page manually")

print("\n" + "=" * 70)
print("✅ Test Complete!")
print("=" * 70)
print()
print("📋 Next Steps:")
print("   1. Check AutoDS dashboard → Products → Drafts")
print("   2. Verify products were added")
print("   3. Import to eBay if needed")
print("   4. Check eBay store for new listings")
print()
print("💡 To use real products, edit TEST_PRODUCTS in this script")
print("   and add your actual supplier URLs or Product IDs")
print()
print("🌐 Browser staying open for 60 seconds for inspection...")
time.sleep(60)

browser.close()
print("\n✅ Done!")

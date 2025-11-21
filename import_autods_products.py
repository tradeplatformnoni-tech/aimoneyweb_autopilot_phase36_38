#!/usr/bin/env python3
"""
AutoDS Product Importer - Fixed with AutoDS Direct Login
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
from agents.vero_protection import check_vero_violation, sanitize_product_for_ebay

AUTODS_URL = "https://platform.autods.com/marketplace/hand-picked-products"
AUTODS_EMAIL = "tradeplatformnoni@gmail.com"
AUTODS_PASSWORD = "Shegseynoni8$$"

print("=" * 70)
print("🚀 AutoDS Product Importer - Full Auto-Control")
print("=" * 70)
print()

assistant = AIBrowserAssistant(headless=False)
assistant.start()

print("📍 Step 1: Opening AutoDS...")
assistant.navigate(AUTODS_URL)
time.sleep(5)

current_url = assistant.get_current_url()
print(f"   Current URL: {current_url}")

# Handle Google OAuth (AutoDS redirects directly to Google)
if "accounts.google.com" in current_url.lower() or "google.com" in current_url.lower():
    print("\n🔐 Step 2: Google OAuth Login Detected")
    print("   Filling Google login form...")

    try:
        # Fill email
        if assistant.wait_for_element(
            "#identifierId, input[type='email'], input[name='identifier']", timeout=10
        ):
            assistant.fill_input(
                "#identifierId, input[type='email'], input[name='identifier']", AUTODS_EMAIL
            )
            print(f"   ✅ Filled email: {AUTODS_EMAIL}")
            time.sleep(1)

            # Click Next
            if assistant.click(
                "#identifierNext, button[id='identifierNext'], button:has-text('Next')", timeout=5
            ):
                print("   ✅ Clicked Next")
                time.sleep(4)

        # Fill password
        if assistant.wait_for_element(
            "input[type='password'], #password, input[name='password']", timeout=10
        ):
            assistant.fill_input(
                "input[type='password'], #password, input[name='password']", AUTODS_PASSWORD
            )
            print("   ✅ Filled password")
            time.sleep(1)

            # Click Next/Sign in
            if assistant.click(
                "#passwordNext, button[id='passwordNext'], button:has-text('Next'), button:has-text('Sign in')",
                timeout=5,
            ):
                print("   ✅ Clicked Sign in")
                time.sleep(5)

        # Handle consent/allow screen
        try:
            if assistant.wait_for_element(
                "button:has-text('Allow'), button:has-text('Continue'), button:has-text('I agree')",
                timeout=5,
            ):
                assistant.click(
                    "button:has-text('Allow'), button:has-text('Continue'), button:has-text('I agree')"
                )
                print("   ✅ Clicked Allow/Continue")
                time.sleep(3)
        except:
            pass

        assistant.screenshot("after_google_login.png")

    except Exception as e:
        print(f"   ⚠️ Google login error: {e}")

# Check if on AutoDS login page (alternative method)
elif "login" in current_url.lower():
    print("\n🔐 Step 2: AutoDS Login Page Detected")

    if hasattr(assistant, "page") and assistant.page:
        # Try Method 1: Direct email/password login (faster)
        print("   Attempting direct email/password login...")

        try:
            # Find email field by name (AutoDS uses name="email")
            email_filled = False
            if assistant.wait_for_element(
                "input[name='email'], input[type='text'][placeholder*='Email']", timeout=5
            ):
                assistant.fill_input(
                    "input[name='email'], input[type='text'][placeholder*='Email']", AUTODS_EMAIL
                )
                print(f"   ✅ Filled email: {AUTODS_EMAIL}")
                email_filled = True
                time.sleep(1)
            else:
                # Try JavaScript fill
                assistant.page.evaluate(f"""
                    () => {{
                        const emailInput = document.querySelector('input[name="email"]') || 
                                         document.querySelector('input[type="text"][placeholder*="Email"]');
                        if (emailInput) {{
                            emailInput.value = '{AUTODS_EMAIL}';
                            emailInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}
                """)
                email_filled = True
                print("   ✅ Filled email via JavaScript")
                time.sleep(1)

            # Find password field
            password_filled = False
            if assistant.wait_for_element(
                "input[name='password'], input[type='password']", timeout=5
            ):
                assistant.fill_input(
                    "input[name='password'], input[type='password']", AUTODS_PASSWORD
                )
                print("   ✅ Filled password")
                password_filled = True
                time.sleep(1)
            else:
                # Try JavaScript fill
                assistant.page.evaluate(f"""
                    () => {{
                        const passInput = document.querySelector('input[name="password"]') || 
                                        document.querySelector('input[type="password"]');
                        if (passInput) {{
                            passInput.value = '{AUTODS_PASSWORD}';
                            passInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }}
                """)
                password_filled = True
                print("   ✅ Filled password via JavaScript")
                time.sleep(1)

            # Click "Log in" button
            login_clicked = False
            login_selectors = [
                "button:has-text('Log in')",
                "button:has-text('Login')",
                "button[type='submit']",
                ".ant-btn-primary",  # AutoDS uses Ant Design
                "button.ant-btn",
            ]

            for selector in login_selectors:
                try:
                    if assistant.click(selector, timeout=3):
                        print(f"   ✅ Clicked login button: {selector}")
                        login_clicked = True
                        time.sleep(5)
                        break
                except:
                    continue

            if not login_clicked:
                # Try JavaScript click
                assistant.page.evaluate("""
                    () => {
                        const loginBtn = document.querySelector('button:has-text("Log in")') ||
                                        document.querySelector('button[type="submit"]') ||
                                        document.querySelector('.ant-btn-primary');
                        if (loginBtn) {
                            loginBtn.click();
                        }
                    }
                """)
                print("   ✅ Clicked login via JavaScript")
                time.sleep(5)

            assistant.screenshot("after_direct_login.png")

        except Exception as e:
            print(f"   ⚠️ Direct login failed: {e}")
            print("   Trying Google login method...")

            # Method 2: Click "Log in with Google" button
            try:
                if assistant.click(
                    "button:has-text('Log in with Google'), button:has-text('Login with Google')",
                    timeout=5,
                ):
                    print("   ✅ Clicked 'Log in with Google' button")
                    time.sleep(3)

                    # Now handle Google OAuth
                    current_url = assistant.get_current_url()
                    if "accounts.google.com" in current_url.lower():
                        print("   🔐 Redirected to Google - handling OAuth...")

                        # Email field
                        if assistant.wait_for_element(
                            "#identifierId, input[type='email']", timeout=5
                        ):
                            assistant.fill_input("#identifierId, input[type='email']", AUTODS_EMAIL)
                            time.sleep(1)
                            assistant.click("#identifierNext, button:has-text('Next')")
                            time.sleep(3)

                        # Password field
                        if assistant.wait_for_element(
                            "input[type='password'], #password", timeout=5
                        ):
                            assistant.fill_input(
                                "input[type='password'], #password", AUTODS_PASSWORD
                            )
                            time.sleep(1)
                            assistant.click("#passwordNext, button:has-text('Next')")
                            time.sleep(5)

                        # Handle consent
                        try:
                            if assistant.wait_for_element(
                                "button:has-text('Allow'), button:has-text('Continue')", timeout=3
                            ):
                                assistant.click(
                                    "button:has-text('Allow'), button:has-text('Continue')"
                                )
                                time.sleep(3)
                        except:
                            pass
            except Exception as e2:
                print(f"   ⚠️ Google login also failed: {e2}")

# Wait and check if logged in
time.sleep(3)
current_url = assistant.get_current_url()
print(f"\n📍 Step 3: After login, URL: {current_url}")

# Handle Google OAuth redirect after AutoDS login
if "accounts.google.com" in current_url.lower():
    print("   🔐 Redirected to Google OAuth - completing login...")

    try:
        # Fill Google email
        if assistant.wait_for_element("#identifierId, input[type='email']", timeout=10):
            assistant.fill_input("#identifierId, input[type='email']", AUTODS_EMAIL)
            print("   ✅ Filled Google email")
            time.sleep(1)
            assistant.click("#identifierNext, button:has-text('Next')")
            time.sleep(4)

        # Fill Google password
        if assistant.wait_for_element("input[type='password'], #password", timeout=10):
            assistant.fill_input("input[type='password'], #password", AUTODS_PASSWORD)
            print("   ✅ Filled Google password")
            time.sleep(1)
            assistant.click("#passwordNext, button:has-text('Next')")
            time.sleep(5)

        # Handle consent
        try:
            if assistant.wait_for_element(
                "button:has-text('Allow'), button:has-text('Continue')", timeout=5
            ):
                assistant.click("button:has-text('Allow'), button:has-text('Continue')")
                print("   ✅ Clicked Allow")
                time.sleep(5)
        except:
            pass

        current_url = assistant.get_current_url()
        print(f"   After Google OAuth, URL: {current_url}")

    except Exception as e:
        print(f"   ⚠️ Google OAuth error: {e}")

# Navigate to marketplace
current_url = assistant.get_current_url()
if "login" not in current_url.lower() and "accounts.google.com" not in current_url.lower():
    print("   ✅ Login successful!")
else:
    print("   ⚠️ Still on login/OAuth page - checking status...")
    assistant.screenshot("login_status_check.png")

print("\n📍 Step 4: Navigating to marketplace...")
assistant.navigate(AUTODS_URL)
time.sleep(5)

current_url = assistant.get_current_url()
print(f"   Final URL: {current_url}")
assistant.screenshot("marketplace_final.png")

# Extract and import products
if "marketplace" in current_url.lower() or "platform.autods.com" in current_url.lower():
    print("\n📦 Step 5: Extracting products...")
    time.sleep(3)

    # Scroll down to load more products
    if hasattr(assistant, "page") and assistant.page:
        print("   Scrolling to load products...")
        for i in range(5):
            assistant.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            # Check if more products loaded
            product_count = assistant.page.evaluate("""
                () => {
                    return document.querySelectorAll('[data-product-id], .product-card, [class*="ProductCard"]').length;
                }
            """)
            print(f"      Found {product_count} products after scroll {i + 1}")
        time.sleep(3)

    if hasattr(assistant, "page") and assistant.page:
        try:
            products_data = assistant.page.evaluate("""
                () => {
                    const products = [];
                    
                    // Try multiple selectors
                    const selectors = [
                        '[data-product-id]',
                        '.product-card',
                        '[class*="ProductCard"]',
                        '[class*="product-card"]'
                    ];
                    
                    let cards = [];
                    for (const sel of selectors) {
                        cards = Array.from(document.querySelectorAll(sel));
                        if (cards.length > 0) break;
                    }
                    
                    // If still none, find any card-like elements
                    if (cards.length === 0) {
                        cards = Array.from(document.querySelectorAll('[class*="card"], [class*="item"]'))
                            .filter(el => {
                                const text = el.textContent || '';
                                return text.length > 20 && text.length < 500;
                            });
                    }
                    
                    cards.forEach((card, idx) => {
                        const titleEl = card.querySelector('h1, h2, h3, h4, h5, h6, [class*="title"], p') ||
                                        card;
                        const priceEl = card.querySelector('[class*="price"], [class*="Price"]');
                        const importBtn = card.querySelector('button, a');
                        
                        const title = titleEl?.textContent?.trim() || card.textContent?.trim()?.substring(0, 100) || `Product ${idx + 1}`;
                        
                        // Filter out promotional/educational items (but be less strict)
                        const skipKeywords = ['Store Setup', 'Academy', 'Ad Spend', 'TikTok'];
                        const shouldSkip = skipKeywords.some(keyword => title.toLowerCase().includes(keyword.toLowerCase()));
                        
                        // Only skip if it's clearly not a product
                        const isProduct = title.length > 5 && 
                                         !title.toLowerCase().includes('step') &&
                                         !title.toLowerCase().includes('academy');
                        
                        if (isProduct && !shouldSkip) {
                            products.push({
                                product_id: card.getAttribute('data-product-id') || `prod_${idx}`,
                                title: title,
                                price: priceEl?.textContent?.trim() || '',
                                has_button: !!importBtn
                            });
                        }
                    });
                    
                    return products.slice(0, 20);  // Limit to 20
                }
            """)

            print(f"   ✅ Found {len(products_data)} products")

            if products_data:
                print("\n📋 Products:")
                for idx, prod in enumerate(products_data[:10], 1):
                    print(f"   {idx}. {prod.get('title', 'Unknown')[:60]}")

                print("\n🔄 Step 6: Importing products...")

                imported = 0
                for idx, product in enumerate(products_data[:10], 1):
                    title = product.get("title", "Unknown")

                    # VERO check
                    is_violation, _ = check_vero_violation(title)
                    if is_violation:
                        sanitized = sanitize_product_for_ebay({"title": title})
                        if sanitized.get("title"):
                            title = sanitized["title"]

                    print(f"   [{idx}/10] {title[:50]}...")

                    # Try to click import button using JavaScript
                    clicked = assistant.page.evaluate(
                        """
                        (productTitle) => {
                            const elements = Array.from(document.querySelectorAll('*'));
                            for (const el of elements) {
                                if (el.textContent && el.textContent.includes(productTitle.substring(0, 30))) {
                                    const btn = el.closest('[class*="card"]')?.querySelector('button, a[class*="import"]') ||
                                               el.querySelector('button, a');
                                    if (btn && (btn.textContent?.includes('Import') || btn.textContent?.includes('Add'))) {
                                        btn.click();
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }
                    """,
                        product.get("title", ""),
                    )

                    if clicked:
                        imported += 1
                        print("      ✅ Import clicked")
                        time.sleep(2)
                    else:
                        print("      ⚠️ Import button not found")

                    time.sleep(1)

                print(f"\n✅ Import complete: {imported} products processed")
            else:
                print("   ⚠️ No products found - may need to scroll or filter")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback

            traceback.print_exc()
else:
    print("\n⚠️ Not on marketplace - login may have failed")
    print("   💡 Check browser window for manual login")

print("\n🌐 Browser staying open for 60 seconds...")
time.sleep(60)

assistant.close()
print("\n✅ Done!")

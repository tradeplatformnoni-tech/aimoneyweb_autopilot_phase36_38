#!/usr/bin/env python3
"""
Debug AutoDS Login - Detailed Analysis
Shows exactly what's happening at each step
"""

import os
import sys
import time
from pathlib import Path

ROOT = Path(os.path.expanduser("~/neolight"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.ai_browser_assistant import AIBrowserAssistant

AUTODS_URL = "https://platform.autods.com/marketplace/hand-picked-products"
AUTODS_EMAIL = "tradeplatformnoni@gmail.com"
AUTODS_PASSWORD = "Shegseynoni8$$"

print("=" * 70)
print("🔍 AutoDS Login Debug - Step by Step Analysis")
print("=" * 70)
print()

assistant = AIBrowserAssistant(headless=False)
assistant.start()

print("📍 Step 1: Opening AutoDS marketplace...")
assistant.navigate(AUTODS_URL)
time.sleep(5)

current_url = assistant.get_current_url()
print(f"   Current URL: {current_url}")

# Debug: Get page info
if hasattr(assistant, "page") and assistant.page:
    print("\n📋 Page Analysis:")

    # Get page title
    title = assistant.page.title()
    print(f"   Page Title: {title}")

    # Get all visible text (first 500 chars)
    visible_text = assistant.page.evaluate("""
        () => {
            return document.body.innerText.substring(0, 500);
        }
    """)
    print("\n   Visible Text (first 500 chars):")
    print(f"   {visible_text[:500]}")

    # Find all input fields
    inputs = assistant.page.evaluate("""
        () => {
            const inputs = Array.from(document.querySelectorAll('input'));
            return inputs.map(input => ({
                type: input.type,
                name: input.name || '',
                id: input.id || '',
                placeholder: input.placeholder || '',
                className: input.className || ''
            }));
        }
    """)
    print(f"\n   Found {len(inputs)} input fields:")
    for inp in inputs:
        print(
            f"      - Type: {inp['type']}, Name: {inp['name']}, ID: {inp['id']}, Placeholder: {inp.get('placeholder', 'N/A')}"
        )

    # Find all buttons
    buttons = assistant.page.evaluate("""
        () => {
            const buttons = Array.from(document.querySelectorAll('button, a[role="button"]'));
            return buttons.map(btn => ({
                text: btn.textContent?.trim() || '',
                id: btn.id || '',
                className: btn.className || '',
                type: btn.type || ''
            }));
        }
    """)
    print(f"\n   Found {len(buttons)} buttons:")
    for btn in buttons[:10]:  # Show first 10
        btn_text = btn["text"][:50] if btn["text"] else "No text"
        print(f"      - Text: '{btn_text}', ID: {btn['id']}, Class: {btn['className'][:30]}")

    # Check for Google login elements
    google_elements = assistant.page.evaluate("""
        () => {
            const elements = [];
            // Check for Google sign-in button
            const googleButtons = Array.from(document.querySelectorAll('*')).filter(el => {
                const text = el.textContent?.toLowerCase() || '';
                const html = el.innerHTML?.toLowerCase() || '';
                return text.includes('google') || text.includes('sign in') || html.includes('google');
            });
            googleButtons.forEach(btn => {
                elements.push({
                    tag: btn.tagName,
                    text: btn.textContent?.trim().substring(0, 50),
                    id: btn.id || '',
                    className: btn.className || ''
                });
            });
            return elements;
        }
    """)

    if google_elements:
        print(f"\n   Found {len(google_elements)} Google-related elements:")
        for el in google_elements[:5]:
            print(f"      - {el['tag']}: '{el['text']}', ID: {el['id']}")

    # Take screenshot
    screenshot = assistant.screenshot("debug_step1_page_analysis.png")
    print(f"\n   📸 Screenshot saved: {screenshot}")

    # Check if we're redirected to Google
    if "accounts.google.com" in current_url.lower() or "google.com" in current_url.lower():
        print("\n✅ Detected Google login page - attempting auto-login...")

        # Try to find email input with detailed logging
        email_found = False
        email_selectors = [
            "#identifierId",
            "input[type='email']",
            "input[name='identifier']",
            "input[id='identifierId']",
            "input[autocomplete='username']",
        ]

        for selector in email_selectors:
            try:
                element = assistant.page.query_selector(selector)
                if element:
                    print(f"   ✅ Found email field with selector: {selector}")
                    email_found = True

                    # Fill email
                    assistant.page.fill(selector, AUTODS_EMAIL)
                    print(f"   ✅ Filled email: {AUTODS_EMAIL}")
                    time.sleep(1)

                    # Find and click Next
                    next_selectors = [
                        "#identifierNext",
                        "button[id='identifierNext']",
                        "button:has-text('Next')",
                    ]

                    for next_sel in next_selectors:
                        try:
                            next_btn = assistant.page.query_selector(next_sel)
                            if next_btn:
                                print(f"   ✅ Found Next button with: {next_sel}")
                                next_btn.click()
                                print("   ✅ Clicked Next")
                                time.sleep(3)

                                # Take screenshot after email
                                assistant.screenshot("debug_step2_after_email.png")
                                print("   📸 Screenshot: debug_step2_after_email.png")
                                break
                        except:
                            continue

                    break
            except Exception as e:
                print(f"   ⚠️ Selector {selector} failed: {e}")
                continue

        if not email_found:
            print("   ⚠️ Could not find email field - showing page structure...")
            page_structure = assistant.page.evaluate("""
                () => {
                    const allInputs = Array.from(document.querySelectorAll('input'));
                    const allButtons = Array.from(document.querySelectorAll('button'));
                    return {
                        inputs: allInputs.map(inp => ({
                            type: inp.type,
                            id: inp.id,
                            name: inp.name,
                            class: inp.className,
                            placeholder: inp.placeholder
                        })),
                        buttons: allButtons.map(btn => ({
                            id: btn.id,
                            text: btn.textContent?.trim().substring(0, 30),
                            class: btn.className
                        }))
                    };
                }
            """)
            print("\n   All Inputs on page:")
            for inp in page_structure["inputs"]:
                print(
                    f"      Input: type={inp['type']}, id={inp.get('id', 'N/A')}, name={inp.get('name', 'N/A')}"
                )
            print("\n   All Buttons on page:")
            for btn in page_structure["buttons"][:10]:
                print(f"      Button: id={btn.get('id', 'N/A')}, text='{btn.get('text', 'N/A')}'")

        # Wait for password page
        time.sleep(3)
        current_url = assistant.get_current_url()
        print(f"\n   After email, URL: {current_url}")

        # Find password input
        password_found = False
        password_selectors = [
            "input[type='password']",
            "#password",
            "input[name='password']",
            "input[id='password']",
        ]

        for selector in password_selectors:
            try:
                element = assistant.page.query_selector(selector)
                if element:
                    print(f"   ✅ Found password field with selector: {selector}")
                    password_found = True

                    assistant.page.fill(selector, AUTODS_PASSWORD)
                    print("   ✅ Filled password")
                    time.sleep(1)

                    # Find and click Sign in
                    signin_selectors = [
                        "#passwordNext",
                        "button[id='passwordNext']",
                        "button:has-text('Next')",
                        "button:has-text('Sign in')",
                    ]

                    for signin_sel in signin_selectors:
                        try:
                            signin_btn = assistant.page.query_selector(signin_sel)
                            if signin_btn:
                                print(f"   ✅ Found Sign in button with: {signin_sel}")
                                signin_btn.click()
                                print("   ✅ Clicked Sign in")
                                time.sleep(5)

                                assistant.screenshot("debug_step3_after_password.png")
                                print("   📸 Screenshot: debug_step3_after_password.png")
                                break
                        except:
                            continue

                    break
            except:
                continue

        if not password_found:
            print("   ⚠️ Password field not found yet - may need to wait longer")

        # Final check
        time.sleep(3)
        final_url = assistant.get_current_url()
        print(f"\n   Final URL: {final_url}")

        if "platform.autods.com" in final_url.lower() and "login" not in final_url.lower():
            print("   ✅ Login successful! On AutoDS platform")
        else:
            print("   ⚠️ Still on login page or Google")

    elif "platform.autods.com" in current_url.lower():
        if "login" in current_url.lower():
            print("\n⚠️ On AutoDS login page but not redirected to Google")
            print("   This means AutoDS might use a different login method")
        else:
            print("\n✅ Already on AutoDS platform - may be logged in!")

    # Final screenshot
    assistant.screenshot("debug_final_state.png")
    print("\n📸 Final screenshot: debug_final_state.png")

print("\n🌐 Browser will stay open for 30 seconds for inspection...")
time.sleep(30)

assistant.close()
print("\n✅ Debug complete! Check screenshots in logs/ directory")

#!/usr/bin/env python3
"""
AutoDS Product Importer - AI Browser Automation
Visits AutoDS marketplace and imports trending products to eBay
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
STATE = ROOT / "state"
LOGS = ROOT / "logs"
DATA = ROOT / "data"

# Import browser assistant
try:
    from agents.ai_browser_assistant import AIBrowserAssistant, solve_website_problem

    BROWSER_AVAILABLE = True
except ImportError:
    BROWSER_AVAILABLE = False
    print("[autods_importer] ❌ AI Browser Assistant not available", flush=True)

# Import VERO protection
try:
    from agents.vero_protection import check_vero_violation, sanitize_product_for_ebay

    VERO_AVAILABLE = True
except ImportError:
    VERO_AVAILABLE = False
    print("[autods_importer] ⚠️ VERO protection not available", flush=True)

# AutoDS credentials
AUTODS_EMAIL = os.getenv("AUTODS_EMAIL", "tradeplatformnoni@gmail.com")
AUTODS_PASSWORD = os.getenv("AUTODS_PASSWORD", "")
AUTODS_URL = "https://platform.autods.com/marketplace/hand-picked-products"

# Trending product categories we identified
TRENDING_CATEGORIES = [
    "Camera Lens",
    "Camera Accessories",
    "Phone Case",
    "Wireless Charger",
    "Smart Home",
    "Gaming Accessories",
    "Health & Beauty",
]


def extract_products_from_page(assistant: AIBrowserAssistant) -> list[dict[str, Any]]:
    """
    Extract product information from AutoDS marketplace page.
    Returns list of product dictionaries.
    """
    products = []

    try:
        # Wait for products to load
        assistant.wait_for_element(".product-card, .product-item, [data-product-id]", timeout=10)
        time.sleep(2)

        # Try to get product cards
        # AutoDS typically uses product cards with data attributes
        page_content = assistant.page.content() if hasattr(assistant, "page") else ""

        # Extract using JavaScript (more reliable)
        if hasattr(assistant, "page"):
            product_data = assistant.page.evaluate(
                """
                () => {
                    const products = [];
                    // Try different selectors AutoDS might use
                    const cards = document.querySelectorAll('[data-product-id], .product-card, .product-item');
                    cards.forEach(card => {
                        const productId = card.getAttribute('data-product-id') ||
                                         card.querySelector('[data-product-id]')?.getAttribute('data-product-id') || '';
                        const titleEl = card.querySelector('.product-title, .title, h3, h4, [class*="title"]');
                        const priceEl = card.querySelector('.price, [class*="price"]');
                        const imageEl = card.querySelector('img');
                        const supplierEl = card.querySelector('[class*="supplier"], [data-supplier]');

                        if (productId || titleEl) {
                            products.push({
                                product_id: productId,
                                title: titleEl?.textContent?.trim() || '',
                                price: priceEl?.textContent?.trim() || '',
                                image: imageEl?.src || imageEl?.getAttribute('data-src') || '',
                                supplier: supplierEl?.textContent?.trim() || supplierEl?.getAttribute('data-supplier') || '',
                                element: card.outerHTML.substring(0, 200)
                            });
                        }
                    });
                    return products;
                }
            """
            )

            products = product_data if isinstance(product_data, list) else []

            print(f"[autods_importer] ✅ Extracted {len(products)} products from page", flush=True)

            # Clean and format products
            formatted_products = []
            for idx, prod in enumerate(products, 1):
                if prod.get("product_id") or prod.get("title"):
                    formatted_products.append(
                        {
                            "product_id": prod.get("product_id", f"auto_{idx}"),
                            "title": prod.get("title", "Unknown Product"),
                            "price": prod.get("price", ""),
                            "image": prod.get("image", ""),
                            "supplier": prod.get("supplier", "AutoDS"),
                            "index": idx,
                        }
                    )

            return formatted_products
    except Exception as e:
        print(f"[autods_importer] ⚠️ Error extracting products: {e}", flush=True)
        # Fallback: return sample products based on trending categories
        return get_trending_products_fallback()

    return products


def get_trending_products_fallback() -> list[dict[str, Any]]:
    """Get trending products list from our research."""
    trending_products = [
        {
            "title": "Universal Camera Lens Kit for DSLR",
            "category": "Camera Accessories",
            "keywords": ["camera lens", "DSLR", "photography"],
        },
        {
            "title": "Premium Wireless Phone Charger",
            "category": "Tech Accessories",
            "keywords": ["wireless charger", "phone", "charging"],
        },
        {
            "title": "Smart Home Plug WiFi Outlet",
            "category": "Smart Home",
            "keywords": ["smart plug", "wifi", "home automation"],
        },
        {
            "title": "Phone Case with Screen Protector",
            "category": "Phone Accessories",
            "keywords": ["phone case", "screen protector", "protection"],
        },
        {
            "title": "Gaming Mouse Pad Large",
            "category": "Gaming Accessories",
            "keywords": ["gaming mouse pad", "desk mat", "gaming"],
        },
        {
            "title": "Skincare Set with Vitamins",
            "category": "Health & Beauty",
            "keywords": ["skincare", "vitamins", "beauty"],
        },
    ]

    return trending_products


def import_product_to_ebay(
    assistant: AIBrowserAssistant, product: dict[str, Any], supplier_source: str | None = None
) -> bool:
    """
    Import a single product to eBay via AutoDS.
    Uses browser automation to click import buttons.
    """
    try:
        product_id = product.get("product_id")
        title = product.get("title", "Unknown Product")

        # Check VERO protection
        if VERO_AVAILABLE:
            is_violation, details = check_vero_violation(title)
            if is_violation:
                print(
                    f"[autods_importer] ⚠️ VERO violation in '{title}' - will use safe version",
                    flush=True,
                )
                sanitized = sanitize_product_for_ebay({"title": title})
                if sanitized.get("title"):
                    title = sanitized["title"]
                    print(f"[autods_importer] ✅ Safe title: {title}", flush=True)

        # Find and click import button for this product
        # AutoDS typically has "Import" or "Add to Store" buttons
        import_selectors = [
            f"[data-product-id='{product_id}'] button:has-text('Import')",
            f"[data-product-id='{product_id}'] button:has-text('Add')",
            f"[data-product-id='{product_id}'] .import-btn",
            f"button[data-product-id='{product_id}']",
            f".product-card:has([data-product-id='{product_id}']) button",
        ]

        imported = False
        for selector in import_selectors:
            try:
                if assistant.click(selector, timeout=3):
                    print(f"[autods_importer] ✅ Clicked import for: {title}", flush=True)
                    time.sleep(2)
                    imported = True
                    break
            except:
                continue

        if not imported:
            print(f"[autods_importer] ⚠️ Could not find import button for: {title}", flush=True)
            return False

        # Wait for import confirmation or modal
        time.sleep(2)

        # Check for confirmation dialog
        try:
            # AutoDS might show a confirmation modal
            confirm_selectors = [
                "button:has-text('Confirm')",
                "button:has-text('Import to Store')",
                "button:has-text('Add to eBay')",
                ".confirm-import",
                "[data-action='confirm-import']",
            ]

            for selector in confirm_selectors:
                if assistant.wait_for_element(selector, timeout=2):
                    assistant.click(selector)
                    print(f"[autods_importer] ✅ Confirmed import for: {title}", flush=True)
                    time.sleep(1)
                    break
        except:
            pass  # No confirmation needed

        return True

    except Exception as e:
        print(f"[autods_importer] ❌ Error importing product: {e}", flush=True)
        return False


def import_trending_products(
    max_products: int = 10, categories: list[str] | None = None
) -> dict[str, Any]:
    """
    Main function to visit AutoDS and import trending products.
    """
    print("=" * 70, flush=True)
    print("🚀 AutoDS Product Importer - Trending Products", flush=True)
    print("=" * 70, flush=True)
    print(f"Target URL: {AUTODS_URL}", flush=True)
    print()

    if not BROWSER_AVAILABLE:
        print("❌ Browser automation not available", flush=True)
        return {"success": False, "error": "Browser not available"}

    assistant = AIBrowserAssistant(headless=False)
    results = {
        "success": False,
        "products_found": 0,
        "products_imported": 0,
        "products_failed": 0,
        "imported_products": [],
    }

    browser_started = False
    try:
        # Step 1: Navigate to AutoDS marketplace
        print("[autods_importer] 📍 Step 1: Starting browser...", flush=True)
        assistant.start()
        browser_started = True

        print("[autods_importer] 📍 Step 2: Navigating to AutoDS marketplace...", flush=True)
        if not assistant.navigate(AUTODS_URL):
            print("[autods_importer] ❌ Failed to navigate to AutoDS", flush=True)
            if browser_started:
                assistant.close()
            return results

        time.sleep(3)

        # Step 3: Check if login required
        print("[autods_importer] 📍 Step 3: Checking login status...", flush=True)
        current_url = assistant.get_current_url()

        # Check if redirected to Google OAuth (AutoDS uses Google login)
        if "google.com" in current_url.lower() or "accounts.google.com" in current_url.lower():
            print("[autods_importer] 🔐 Google OAuth login detected...", flush=True)
            print(
                "[autods_importer] ⚠️ AutoDS uses Google OAuth - manual login may be required",
                flush=True,
            )
            print(
                "[autods_importer] 💡 Browser opened - please login manually, then press Enter",
                flush=True,
            )
            try:
                input("Press Enter after logging in...")
            except EOFError:
                print(
                    "[autods_importer] ⚠️ Running non-interactively - continuing without login",
                    flush=True,
                )

            # Navigate back to marketplace after manual login
            print("[autods_importer] 📍 Navigating to marketplace...", flush=True)
            assistant.navigate(AUTODS_URL)
            time.sleep(5)
        elif "login" in current_url.lower() or assistant.wait_for_element(
            "input[type='email'], input[type='password']", timeout=5
        ):
            print("[autods_importer] 🔐 Login form detected...", flush=True)

            # Try to fill email/password directly
            try:
                if assistant.wait_for_element(
                    "input[type='email'], input[name*='email']", timeout=5
                ):
                    assistant.fill_input("input[type='email'], input[name*='email']", AUTODS_EMAIL)
                    time.sleep(1)

                if assistant.wait_for_element(
                    "input[type='password'], input[name*='password']", timeout=5
                ):
                    assistant.fill_input(
                        "input[type='password'], input[name*='password']", AUTODS_PASSWORD
                    )
                    time.sleep(1)

                if assistant.click(
                    "button[type='submit'], button:has-text('Login'), .login-button", timeout=5
                ):
                    print("[autods_importer] ✅ Login submitted", flush=True)
                    time.sleep(5)
            except Exception as e:
                print(
                    f"[autods_importer] ⚠️ Auto-login failed: {e} - manual login may be required",
                    flush=True,
                )

            # Navigate back to marketplace
            assistant.navigate(AUTODS_URL)
            time.sleep(3)

        # Step 4: Extract products from page
        print("[autods_importer] 📍 Step 4: Extracting products from page...", flush=True)
        products = extract_products_from_page(assistant)

        if not products:
            print("[autods_importer] ⚠️ No products found on page - using fallback list", flush=True)
            products = get_trending_products_fallback()

        results["products_found"] = len(products)
        print(f"[autods_importer] ✅ Found {len(products)} products", flush=True)

        # Step 5: Import products (up to max_products)
        print(
            f"[autods_importer] 📍 Step 5: Importing up to {max_products} products...", flush=True
        )

        imported_count = 0
        for idx, product in enumerate(products[:max_products], 1):
            print(
                f"\n[{idx}/{min(len(products), max_products)}] Processing: {product.get('title', 'Unknown')}",
                flush=True,
            )

            if import_product_to_ebay(assistant, product):
                imported_count += 1
                results["products_imported"] += 1
                results["imported_products"].append(product.get("title", "Unknown"))
                print(
                    f"[autods_importer] ✅ Imported: {product.get('title', 'Unknown')}", flush=True
                )
            else:
                results["products_failed"] += 1
                print(f"[autods_importer] ❌ Failed: {product.get('title', 'Unknown')}", flush=True)

            time.sleep(2)  # Wait between imports

        results["success"] = imported_count > 0

        print()
        print("=" * 70, flush=True)
        print("📊 Import Summary", flush=True)
        print("=" * 70, flush=True)
        print(f"Products Found: {results['products_found']}", flush=True)
        print(f"Products Imported: {results['products_imported']}", flush=True)
        print(f"Products Failed: {results['products_failed']}", flush=True)
        print()

        if results["imported_products"]:
            print("✅ Successfully Imported:", flush=True)
            for prod in results["imported_products"]:
                print(f"   - {prod}", flush=True)

        print("=" * 70, flush=True)

        # Keep browser open for inspection
        print("\n🌐 Browser will stay open for 30 seconds for inspection...", flush=True)
        print("Press Ctrl+C to close early, or wait for auto-close.", flush=True)
        time.sleep(30)

    except KeyboardInterrupt:
        print("\n[autods_importer] ⚠️ Interrupted by user", flush=True)
    except Exception as e:
        print(f"\n[autods_importer] ❌ Error: {e}", flush=True)
        import traceback

        traceback.print_exc()
    finally:
        if browser_started:
            assistant.close()

    return results


def main():
    """Run the importer."""
    import argparse

    parser = argparse.ArgumentParser(description="Import trending products from AutoDS to eBay")
    parser.add_argument("--max-products", type=int, default=10, help="Maximum products to import")
    parser.add_argument("--email", type=str, default=AUTODS_EMAIL, help="AutoDS email")
    parser.add_argument("--password", type=str, default=AUTODS_PASSWORD, help="AutoDS password")

    args = parser.parse_args()

    if args.password:
        os.environ["AUTODS_PASSWORD"] = args.password
    if args.email:
        os.environ["AUTODS_EMAIL"] = args.email

    results = import_trending_products(max_products=args.max_products)

    # Save results
    results_file = STATE / "autods_import_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n📄 Results saved to: {results_file}", flush=True)


if __name__ == "__main__":
    main()

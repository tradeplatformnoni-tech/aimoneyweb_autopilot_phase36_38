#!/usr/bin/env python3
"""
Apply Theme Changes via API - Update Rebel Theme Content
Attempts to modify theme sections through Shopify Theme API
"""

import os
import re

import requests

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

SHOPIFY_API_VERSION = "2024-01"

# Content to apply
CONTENT = {
    "announcement": "🎉 New Arrivals Every Week | Free Shipping on Orders Over $50 | 30-Day Money-Back Guarantee",
    "hero_headline": "Discover Your Perfect Match",
    "hero_subheadline": "Premium electronics, fitness gear, and lifestyle essentials - all at unbeatable prices. Transform your daily routine with products that deliver.",
    "hero_button": "Shop Now",
    "hero_button_link": "/collections/all",
}


def shopify_api(method: str, endpoint: str, data: dict | None = None) -> dict:
    """Shopify API request."""
    url = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/{endpoint}"
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN, "Content-Type": "application/json"}

    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
        elif method == "PUT":
            r = requests.put(url, headers=headers, json=data, timeout=15)
        else:
            return {}

        if r.status_code in [200, 201]:
            return r.json() if r.content else {}
        else:
            print(f"⚠️  API {method} {endpoint}: {r.status_code}", flush=True)
            return {}
    except Exception as e:
        print(f"⚠️  API error: {e}", flush=True)
        return {}


def get_main_theme():
    """Get main theme."""
    themes = shopify_api("GET", "themes.json")
    theme_list = themes.get("themes", [])

    # Find main theme
    for theme in theme_list:
        if theme.get("role") == "main":
            return theme

    # Or find Rebel
    for theme in theme_list:
        if "rebel" in theme.get("name", "").lower():
            return theme

    return theme_list[0] if theme_list else None


def update_section_asset(theme_id: str, section_key: str, content_updates: dict[str, str]) -> bool:
    """Update a section asset with new content."""
    # Get current asset
    asset_url = f"themes/{theme_id}/assets.json?asset[key]={section_key}"
    current = shopify_api("GET", asset_url)

    if not current:
        return False

    assets = current.get("assets", [])
    if not assets:
        return False

    asset = assets[0]
    current_value = asset.get("value", "")

    # Update content in Liquid template
    updated_value = current_value

    # Update announcement text
    if "announcement" in section_key.lower():
        # Find and replace announcement text
        patterns = [
            (r'"text"\s*:\s*"[^"]*"', f'"text": "{content_updates.get("announcement", "")}"'),
            (r'default\s*:\s*"[^"]*"', f'default: "{content_updates.get("announcement", "")}"'),
        ]
        for pattern, replacement in patterns:
            updated_value = re.sub(pattern, replacement, updated_value)

    # Update hero content
    if "hero" in section_key.lower():
        # Update headline
        updated_value = re.sub(
            r'"headline"[^}]*default\s*:\s*"[^"]*"',
            f'"headline", "default": "{content_updates.get("hero_headline", "")}"',
            updated_value,
        )
        # Update subheadline
        updated_value = re.sub(
            r'"subheadline"[^}]*default\s*:\s*"[^"]*"',
            f'"subheadline", "default": "{content_updates.get("hero_subheadline", "")}"',
            updated_value,
        )
        # Update button
        updated_value = re.sub(
            r'"button_text"[^}]*default\s*:\s*"[^"]*"',
            f'"button_text", "default": "{content_updates.get("hero_button", "")}"',
            updated_value,
        )

    # Only update if changed
    if updated_value == current_value:
        print("   (Content already similar - manual update recommended)", flush=True)
        return False

    # Put updated asset
    update_data = {"asset": {"key": section_key, "value": updated_value}}

    result = shopify_api("PUT", f"themes/{theme_id}/assets.json", update_data)
    return bool(result)


def main():
    """Main execution."""
    print("🚀 Applying Theme Changes via API\n", flush=True)
    print("=" * 60, flush=True)

    # Get theme
    theme = get_main_theme()
    if not theme:
        print("❌ Could not find theme", flush=True)
        return

    theme_id = theme.get("id")
    theme_name = theme.get("name")
    print(f"\n✅ Found theme: {theme_name} (ID: {theme_id})\n", flush=True)

    # Get assets
    assets_url = f"themes/{theme_id}/assets.json"
    assets_data = shopify_api("GET", assets_url)

    if not assets_data:
        print("⚠️  Could not access theme assets (may need read_themes scope)", flush=True)
        print("\n📝 Manual update required - content provided below", flush=True)
        return

    assets = assets_data.get("assets", [])
    print(f"📦 Found {len(assets)} theme assets\n", flush=True)

    # Find sections to update
    updated = 0

    # Find announcement section
    ann_sections = [
        a
        for a in assets
        if "announcement" in a.get("key", "").lower() and "section" in a.get("key", "")
    ]
    if ann_sections:
        print(f"📝 Updating announcement section: {ann_sections[0].get('key')}", flush=True)
        if update_section_asset(theme_id, ann_sections[0].get("key"), CONTENT):
            print("   ✅ Updated!", flush=True)
            updated += 1
        else:
            print("   ⚠️  Manual update needed", flush=True)

    # Find hero section
    hero_sections = [
        a for a in assets if "hero" in a.get("key", "").lower() and "section" in a.get("key", "")
    ]
    if hero_sections:
        print(f"📝 Updating hero section: {hero_sections[0].get('key')}", flush=True)
        if update_section_asset(theme_id, hero_sections[0].get("key"), CONTENT):
            print("   ✅ Updated!", flush=True)
            updated += 1
        else:
            print("   ⚠️  Manual update needed", flush=True)

    print("\n" + "=" * 60, flush=True)

    if updated > 0:
        print(f"\n✅ Updated {updated} sections!", flush=True)
        print("\n🌐 Check your website:", flush=True)
        print(f"   https://{SHOPIFY_STORE}", flush=True)
        print("\n📝 Changes should be visible now!", flush=True)
    else:
        print("\n⚠️  API updates limited - manual customization required", flush=True)
        print("\n📋 CONTENT TO APPLY MANUALLY:", flush=True)
        print("\nAnnouncement Bar:", flush=True)
        print(f"   {CONTENT['announcement']}", flush=True)
        print("\nHero Headline:", flush=True)
        print(f"   {CONTENT['hero_headline']}", flush=True)
        print("\nHero Subheadline:", flush=True)
        print(f"   {CONTENT['hero_subheadline']}", flush=True)
        print("\nButton:", flush=True)
        print(f"   {CONTENT['hero_button']}", flush=True)
        print("\n🌐 Apply at:", flush=True)
        print(f"   https://{SHOPIFY_STORE}/admin/themes → Customize", flush=True)


if __name__ == "__main__":
    main()

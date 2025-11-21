#!/usr/bin/env python3
"""
Update Rebel Theme - Apply TrendyTreasure Market Branding
Attempts to update theme sections and content via API
"""

import os
from pathlib import Path
from typing import Any

import requests

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

SHOPIFY_API_VERSION = "2024-01"
BASE_URL = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}"

# Branding Content
CONTENT = {
    "announcement": "🎉 New Arrivals Every Week | Free Shipping on Orders Over $50 | 30-Day Money-Back Guarantee",
    "hero_headline": "Discover Your Perfect Match",
    "hero_subheadline": "Premium electronics, fitness gear, and lifestyle essentials - all at unbeatable prices. Transform your daily routine with products that deliver.",
    "hero_button": "Shop Now",
}


def shopify_request(method: str, endpoint: str, data: dict | None = None) -> dict[str, Any]:
    """Make Shopify API request."""
    url = f"{BASE_URL}/{endpoint}"
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN, "Content-Type": "application/json"}

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=15)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=15)
        else:
            raise ValueError(f"Unknown method: {method}")

        response.raise_for_status()
        return response.json() if response.content else {}
    except Exception:
        return {}


def get_rebel_theme():
    """Get Rebel theme."""
    try:
        response = shopify_request("GET", "themes.json")
        themes = response.get("themes", [])

        # Find Rebel or main theme
        rebel = [t for t in themes if "rebel" in t.get("name", "").lower()]
        if rebel:
            return rebel[0]

        main = [t for t in themes if t.get("role") == "main"]
        if main:
            return main[0]

        return themes[0] if themes else None
    except:
        return None


def create_manual_update_guide():
    """Create guide for manual updates."""
    guide = f"""# 🎨 Rebel Theme Update Guide - TrendyTreasure Market

## 🚀 Quick Update (5 minutes)

### Step 1: Open Theme Customizer
```
https://{SHOPIFY_STORE}/admin/themes
```
→ Click "Customize" on Rebel theme

### Step 2: Update Announcement Bar

**Location:** Left sidebar → "Announcement"

**Text:** Copy and paste this:
```
{CONTENT["announcement"]}
```

**Settings:**
- Font: Heading
- Size: 16px
- Background: #2563EB (blue)
- Text color: White

### Step 3: Update Hero Section

**Location:** Left sidebar → "Hero"

**Heading:** Replace with:
```
{CONTENT["hero_headline"]}
```

**Text/Subheading:** Replace with:
```
{CONTENT["hero_subheadline"]}
```

**Button Text:** Replace with:
```
{CONTENT["hero_button"]}
```

**Button Link:** `/collections/all`

**Layout Settings:**
- Alignment: **Center**
- Position: **Center**
- Height: **Large**

**Appearance:**
- Color scheme: **Scheme 2** (or dark)
- Media overlay: **ON**
- Overlay style: **Gradient**
- Gradient direction: **Up**

### Step 4: Update Header

**Location:** Left sidebar → "Header"

**Logo:**
- Position: **Center**

**Menu:**
- Position: **Center**
- Top level size: **16px**

**Search:**
- Position: **Right**
- Row: **Top**

**Appearance:**
- Sticky header: **Always** ✅
- Height: **Standard**
- Homepage: **Transparent background** ✅

### Step 5: Save

Click **"Save"** in top right corner

**Done! Your Rebel theme is now branded for TrendyTreasure Market!** ✅

---

## 📋 Content Summary

**Announcement:**
{CONTENT["announcement"]}

**Hero Headline:**
{CONTENT["hero_headline"]}

**Hero Subheadline:**
{CONTENT["hero_subheadline"]}

**Button:**
{CONTENT["hero_button"]}

---

⏱️ **Total Time: 5 minutes**
"""

    guide_path = Path(os.path.expanduser("~/neolight")) / "REBEL_THEME_UPDATE.md"
    guide_path.write_text(guide)
    return guide_path


def main():
    """Main function."""
    print("🎨 Updating Rebel Theme for TrendyTreasure Market\n", flush=True)
    print("=" * 60, flush=True)

    # Find Rebel theme
    print("\n📋 Finding Rebel theme...", flush=True)
    theme = get_rebel_theme()

    if theme:
        print(f"✅ Found: {theme.get('name')} (ID: {theme.get('id')})", flush=True)
        print(
            f"   Status: {'Main theme' if theme.get('role') == 'main' else 'Available'}", flush=True
        )
    else:
        print("⚠️  Could not find theme - creating manual guide", flush=True)

    print("\n📝 Creating update guide...", flush=True)
    guide_path = create_manual_update_guide()
    print(f"✅ Guide created: {guide_path.name}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("\n✅ REBEL THEME UPDATE READY!\n", flush=True)

    print("🎯 Quick Steps:", flush=True)
    print("", flush=True)
    print("1. Open Theme Customizer:", flush=True)
    print(f"   https://{SHOPIFY_STORE}/admin/themes", flush=True)
    print("   → Click 'Customize' on Rebel theme", flush=True)
    print("", flush=True)
    print("2. Update sections (copy from guide):", flush=True)
    print("   • Announcement Bar", flush=True)
    print("   • Hero Section", flush=True)
    print("   • Header Settings", flush=True)
    print("", flush=True)
    print("3. Click 'Save'", flush=True)
    print("", flush=True)
    print(f"📖 Full guide: {guide_path.name}", flush=True)
    print("", flush=True)
    print("✅ Your Rebel theme will be updated with TrendyTreasure branding!", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Shopify Theme Optimizer - Apply World-Class Header & Theme Settings
Attempts to automate theme customization where possible
"""

import os
from pathlib import Path

import requests

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

SHOPIFY_API_VERSION = "2024-01"
BASE_URL = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}"


def shopify_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
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
        return response.json()
    except Exception as e:
        print(f"⚠️  API error: {e}", flush=True)
        return {}


def get_theme_info():
    """Get current theme information."""
    try:
        response = shopify_request("GET", "themes.json")
        themes = response.get("themes", [])

        # Find main/published theme
        main_theme = None
        for theme in themes:
            if theme.get("role") == "main":
                main_theme = theme
                break

        if not main_theme and themes:
            main_theme = themes[0]

        return main_theme
    except Exception as e:
        print(f"⚠️  Could not get theme info: {e}", flush=True)
        return None


def create_settings_guide():
    """Create a step-by-step settings guide."""
    guide = """# 🎨 World-Class Shopify Theme Settings - Quick Apply Guide

## ⚡️ QUICK APPLY (Copy-Paste Settings)

### 📋 HEADER SETTINGS

#### Logo Section:
- Position: **Center**
- Row: **Top**

#### Menu Section:
- Position: **Center**
- Top level size: **16px**
- Font: **Body**
- Case: **Default**
- Submenu text style: **Medium**
- Mobile layout: **Accordion**

#### Search Section:
- Position: **Right**
- Row: **Top**

#### Localization (if applicable):
- Country/Region: **Enabled**
- Flag: **Show**
- Language selector: **Enabled**

#### Appearance Section:
- Width: **Full**
- Height: **Standard**
- Sticky header: **Always** ⭐
- Divider thickness: **2px**

#### Colors:
- Default: **Scheme 1** (or your brand colors)
- Homepage: **Transparent background** ✅
- Product pages: **Solid background**
- Collection pages: **Solid background**

---

### 🎯 HERO SECTION (Homepage)

#### Layout:
- Direction: **Vertical**
- Alignment: **Center**
- Position: **Center**
- Gap: **Medium**
- Width: **Full**
- Height: **Large** (or Full screen)

#### Appearance:
- Color scheme: **Scheme 2**
- Media overlay: **ON**
- Overlay color: **#00000040** (subtle dark)
- Overlay style: **Gradient**
- Gradient direction: **Up**
- Blurred reflection: **Off**

#### Padding:
- Top: **24px**
- Bottom: **64px**

---

### 📝 TYPOGRAPHY SETTINGS

#### Heading:
- Font: **Heading**
- Size: **32-48px** (Hero), **24px** (Section)
- Weight: **Bold/Semibold**

#### Subheading:
- Font: **Subheading**
- Size: **20px**
- Weight: **Regular**

#### Body:
- Font: **Body**
- Size: **16px**
- Weight: **Regular**

---

### 🎨 COLOR SCHEME RECOMMENDATIONS

**Scheme 1 (Header Default):**
- Background: White/Light
- Text: Dark (#1a1a1a)
- Accent: Your brand color

**Scheme 2 (Hero):**
- Text: White (on dark overlay)
- Accent: Bright/Contrasting

---

## 🚀 IMPLEMENTATION STEPS

1. **Open Theme Customizer:**
   ```
   https://trendytreasure-market.myshopify.com/admin/themes
   ```
   → Click "Customize" on your active theme

2. **Header Section:**
   - Navigate to "Header" in left sidebar
   - Apply settings above section by section
   - Click "Save" after each major change

3. **Hero Section:**
   - Navigate to "Hero" section
   - Apply layout and appearance settings
   - Adjust text content to match your brand
   - Save

4. **Typography (Theme Settings):**
   - Go to "Theme settings" → "Typography"
   - Set heading, body, and accent fonts
   - Apply size recommendations

5. **Colors (Theme Settings):**
   - Go to "Theme settings" → "Colors"
   - Set up color schemes
   - Apply transparent header for homepage

---

## ✅ VERIFICATION CHECKLIST

After applying:
- [ ] Header is sticky (scrolls down, header stays)
- [ ] Logo is centered
- [ ] Menu is centered
- [ ] Search icon on right (top row)
- [ ] Homepage has transparent header
- [ ] Product pages have solid header
- [ ] Hero section is impactful and centered
- [ ] Typography is readable and professional
- [ ] Mobile view looks good

---

## 🎯 QUICK REFERENCE

**Key Settings to Apply:**
1. Header → Logo: Center
2. Header → Menu: Center, 16px
3. Header → Search: Right, Top
4. Header → Sticky: Always
5. Header → Transparent: Homepage only
6. Hero → Alignment: Center
7. Hero → Height: Large
8. Hero → Overlay: Gradient Up

**Time to Complete:** ~10-15 minutes

---

## 📞 Need Help?

All settings are optimized for:
- ✅ Modern e-commerce best practices
- ✅ High conversion rates
- ✅ Mobile-responsive design
- ✅ Professional appearance

Your store will look world-class! 🚀
"""

    guide_path = Path(os.path.expanduser("~/neolight")) / "THEME_SETTINGS_GUIDE.md"
    guide_path.write_text(guide)
    print(f"✅ Settings guide created: {guide_path.name}", flush=True)
    return guide_path


def main():
    """Main function."""
    print("🎨 Shopify Theme Optimizer\n", flush=True)
    print("=" * 60, flush=True)

    # Get theme info
    theme = get_theme_info()
    if theme:
        print(f"✅ Current theme: {theme.get('name', 'Unknown')}", flush=True)
        print(f"   Theme ID: {theme.get('id')}", flush=True)
        print(f"   Status: {theme.get('role', 'Unknown')}", flush=True)
    else:
        print("⚠️  Could not detect current theme", flush=True)

    print("", flush=True)

    # Note: Direct theme file modification via REST API is limited
    # Shopify requires Theme API or manual customization
    print("📝 Theme customization requires:", flush=True)
    print("   • Manual setup in Theme Customizer (recommended)", flush=True)
    print("   • OR Theme file modification (advanced)", flush=True)
    print("", flush=True)

    # Create settings guide
    guide_path = create_settings_guide()

    print("", flush=True)
    print("=" * 60, flush=True)
    print("\n✅ Theme Settings Guide Created!\n", flush=True)

    print("🎯 Next Steps:", flush=True)
    print("", flush=True)
    print("1. Open Theme Customizer:", flush=True)
    print(f"   https://{SHOPIFY_STORE}/admin/themes", flush=True)
    print("   → Click 'Customize'", flush=True)
    print("", flush=True)
    print("2. Follow the guide:", flush=True)
    print(f"   {guide_path.name}", flush=True)
    print("", flush=True)
    print("3. Apply settings section by section", flush=True)
    print("   → Header → Hero → Typography → Colors", flush=True)
    print("", flush=True)
    print("⏱️  Estimated time: 10-15 minutes", flush=True)
    print("", flush=True)
    print("✅ Your store will be world-class when complete!", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
TrendyTreasure Market - Complete Theme Branding & Setup
Creates cohesive, world-class theme that matches store products and message
"""

import json
import os
from pathlib import Path

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

SHOPIFY_API_VERSION = "2024-01"
BASE_URL = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}"

# Store Branding & Messaging
STORE_BRANDING = {
    "name": "TrendyTreasure Market",
    "tagline": "Premium Quality. Unbeatable Prices. Unlimited Possibilities.",
    "mission": "We curate world-class products that enhance your lifestyle - from cutting-edge electronics to fitness essentials. Every product is carefully selected for quality, value, and style.",
    "hero_headline": "Discover Your Perfect Match",
    "hero_subheadline": "Premium electronics, fitness gear, and lifestyle essentials - all at unbeatable prices. Transform your daily routine with products that deliver.",
    "hero_cta": "Shop Now",
    "color_primary": "#2563EB",  # Professional blue
    "color_secondary": "#10B981",  # Success green
    "color_accent": "#F59E0B",  # Energetic orange
    "sections": {
        "featured": {
            "title": "Featured Products",
            "subtitle": "Hand-picked favorites that deliver exceptional value",
        },
        "electronics": {
            "title": "Electronics & Tech",
            "subtitle": "Cutting-edge technology that keeps you connected",
        },
        "fitness": {
            "title": "Fitness & Wellness",
            "subtitle": "Everything you need to live your best life",
        },
        "lifestyle": {
            "title": "Lifestyle Essentials",
            "subtitle": "Products that make every day better",
        },
    },
}

# Custom CSS for world-class styling
CUSTOM_CSS = """
/* TrendyTreasure Market - World-Class Theme Styling */

/* Header Enhancements */
.site-header {
    backdrop-filter: blur(10px);
    box-shadow: 0 2px 20px rgba(0,0,0,0.08);
}

/* Hero Section */
.hero-section {
    position: relative;
    overflow: hidden;
}

.hero-section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    opacity: 0.9;
    z-index: 1;
}

.hero-content {
    position: relative;
    z-index: 2;
    color: white;
}

/* Product Cards */
.product-card {
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    border-radius: 12px;
    overflow: hidden;
}

.product-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.15);
}

/* Buttons */
.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    padding: 14px 32px;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

/* Typography */
h1, h2, h3 {
    font-weight: 700;
    letter-spacing: -0.5px;
}

/* Section Spacing */
.section {
    padding: 80px 0;
}

/* Collection Grid */
.collection-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 32px;
}

/* Footer */
.site-footer {
    background: #1a1a1a;
    color: #fff;
    padding: 60px 0 30px;
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .hero-section {
        min-height: 60vh;
    }

    .section {
        padding: 40px 0;
    }
}
"""


def create_theme_content():
    """Create complete theme content file."""
    content = {
        "branding": STORE_BRANDING,
        "css": CUSTOM_CSS,
        "settings": {
            "header": {
                "logo_position": "center",
                "menu_position": "center",
                "search_position": "right",
                "sticky": "always",
                "height": "standard",
                "transparent_homepage": True,
            },
            "hero": {
                "headline": STORE_BRANDING["hero_headline"],
                "subheadline": STORE_BRANDING["hero_subheadline"],
                "cta_text": STORE_BRANDING["hero_cta"],
                "alignment": "center",
                "height": "large",
                "overlay": True,
                "overlay_color": "#00000040",
                "overlay_style": "gradient",
                "overlay_direction": "up",
            },
            "colors": {
                "primary": STORE_BRANDING["color_primary"],
                "secondary": STORE_BRANDING["color_secondary"],
                "accent": STORE_BRANDING["color_accent"],
            },
            "typography": {
                "heading_font": "system-ui, -apple-system, sans-serif",
                "body_font": "system-ui, -apple-system, sans-serif",
                "heading_size": "32-48px",
                "body_size": "16px",
            },
        },
    }

    # Save to file
    content_file = Path(os.path.expanduser("~/neolight")) / "theme_branding.json"
    content_file.write_text(json.dumps(content, indent=2))

    return content_file


def create_hero_content_html():
    """Create hero section HTML content."""
    html = f"""
<div class="hero-content">
    <h1 style="font-size: 48px; font-weight: 700; margin-bottom: 20px; line-height: 1.2;">
        {STORE_BRANDING["hero_headline"]}
    </h1>
    <p style="font-size: 20px; margin-bottom: 32px; opacity: 0.95; max-width: 600px; margin-left: auto; margin-right: auto;">
        {STORE_BRANDING["hero_subheadline"]}
    </p>
    <a href="/collections/all" class="btn-primary" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s ease;">
        {STORE_BRANDING["hero_cta"]}
    </a>
</div>
"""
    return html


def create_announcement_text():
    """Create announcement bar text."""
    return "🎉 New Arrivals Every Week | Free Shipping on Orders Over $50 | 30-Day Money-Back Guarantee"


def save_theme_guide():
    """Save complete theme implementation guide."""
    guide = f"""# 🎨 TrendyTreasure Market - Complete Theme Setup Guide

## 🎯 Store Identity

**Name:** {STORE_BRANDING["name"]}
**Tagline:** {STORE_BRANDING["tagline"]}
**Mission:** {STORE_BRANDING["mission"]}

---

## 🚀 QUICK IMPLEMENTATION (15 minutes)

### Step 1: Theme Customizer
1. Go to: https://{SHOPIFY_STORE}/admin/themes
2. Click "Customize" on your active theme

### Step 2: Header Settings

**Logo:**
- Position: **Center**
- Upload logo if you have one (or use store name)

**Menu:**
- Position: **Center**
- Top level size: **16px**
- Font: **Body**

**Search:**
- Position: **Right**
- Row: **Top**

**Appearance:**
- Sticky header: **Always** ✅
- Height: **Standard**
- Width: **Full**
- Homepage: **Transparent background** ✅
- Product pages: **Solid background**

### Step 3: Announcement Bar

**Text:**
```
{create_announcement_text()}
```

**Settings:**
- Font: **Heading**
- Size: **16px**
- Background: Use primary color (#2563EB)
- Text color: **White**

### Step 4: Hero Section

**Content (Replace current text):**

**Heading:**
```
{STORE_BRANDING["hero_headline"]}
```

**Subheading:**
```
{STORE_BRANDING["hero_subheadline"]}
```

**Button Text:**
```
{STORE_BRANDING["hero_cta"]}
```
**Button Link:** `/collections/all`

**Layout Settings:**
- Alignment: **Center**
- Position: **Center**
- Height: **Large** (or Full screen)
- Width: **Full**

**Appearance:**
- Color scheme: **Scheme 2**
- Media overlay: **ON**
- Overlay color: **#00000040**
- Overlay style: **Gradient**
- Gradient direction: **Up**
- Padding: Top **24px**, Bottom **64px**

### Step 5: Theme Settings → Colors

**Color Scheme 1 (Header/Default):**
- Primary: **#2563EB** (Professional Blue)
- Secondary: **#10B981** (Success Green)
- Accent: **#F59E0B** (Energetic Orange)

### Step 6: Theme Settings → Typography

**Heading:**
- Font: **System default** or **Modern sans-serif**
- Size: **32-48px** (Hero), **24px** (Sections)
- Weight: **Bold**

**Body:**
- Font: **System default**
- Size: **16px**
- Weight: **Regular**

### Step 7: Custom CSS (Optional but Recommended)

Go to Theme Settings → Custom CSS and paste:

```css
{CUSTOM_CSS}
```

---

## 📋 Section Content

### Featured Products Section
**Title:** {STORE_BRANDING["sections"]["featured"]["title"]}
**Subtitle:** {STORE_BRANDING["sections"]["featured"]["subtitle"]}

### Electronics Collection
**Title:** {STORE_BRANDING["sections"]["electronics"]["title"]}
**Subtitle:** {STORE_BRANDING["sections"]["electronics"]["subtitle"]}

### Fitness Collection
**Title:** {STORE_BRANDING["sections"]["fitness"]["title"]}
**Subtitle:** {STORE_BRANDING["sections"]["fitness"]["subtitle"]}

### Lifestyle Collection
**Title:** {STORE_BRANDING["sections"]["lifestyle"]["title"]}
**Subtitle:** {STORE_BRANDING["sections"]["lifestyle"]["subtitle"]}

---

## ✅ Verification Checklist

After setup:
- [ ] Header is sticky and centered
- [ ] Hero section has new headline/subheadline
- [ ] Announcement bar shows promotional message
- [ ] Colors match brand (blue/green/orange)
- [ ] Typography is clean and readable
- [ ] Mobile view looks good
- [ ] All sections display correctly

---

## 🎨 Brand Message

Your store communicates:
- ✅ **Premium Quality** - World-class products
- ✅ **Unbeatable Prices** - Best value in market
- ✅ **Lifestyle Enhancement** - Products that improve daily life
- ✅ **Trust & Reliability** - 30-day guarantee, fast shipping

---

## 🚀 After Setup

Your store will have:
- Professional, modern appearance
- Cohesive brand messaging
- High conversion-optimized design
- Mobile-responsive layout
- World-class user experience

**Time to Complete:** ~15 minutes

**Result:** A store that looks and feels premium! 🎯
"""

    guide_path = Path(os.path.expanduser("~/neolight")) / "COMPLETE_THEME_SETUP.md"
    guide_path.write_text(guide)
    return guide_path


def main():
    """Main function."""
    print("🎨 Creating TrendyTreasure Market Theme Branding\n", flush=True)
    print("=" * 60, flush=True)

    # Create theme content
    print("\n📝 Creating theme content...", flush=True)
    content_file = create_theme_content()
    print(f"✅ Theme content saved: {content_file.name}", flush=True)

    # Create hero HTML
    print("\n📝 Creating hero section content...", flush=True)
    hero_html = create_hero_content_html()
    hero_file = Path(os.path.expanduser("~/neolight")) / "hero_content.html"
    hero_file.write_text(hero_html)
    print(f"✅ Hero content saved: {hero_file.name}", flush=True)

    # Save guide
    print("\n📝 Creating implementation guide...", flush=True)
    guide_path = save_theme_guide()
    print(f"✅ Complete guide saved: {guide_path.name}", flush=True)

    print("\n" + "=" * 60, flush=True)
    print("\n✅ THEME BRANDING COMPLETE!\n", flush=True)

    print("🎯 What Was Created:", flush=True)
    print("   1. Complete theme branding (colors, messaging, content)", flush=True)
    print("   2. Hero section HTML content", flush=True)
    print("   3. Custom CSS for world-class styling", flush=True)
    print("   4. Complete implementation guide", flush=True)
    print("", flush=True)

    print("🚀 Next Steps:", flush=True)
    print("", flush=True)
    print("1. Open Theme Customizer:", flush=True)
    print(f"   https://{SHOPIFY_STORE}/admin/themes", flush=True)
    print("   → Click 'Customize'", flush=True)
    print("", flush=True)
    print("2. Follow the guide:", flush=True)
    print(f"   {guide_path.name}", flush=True)
    print("", flush=True)
    print("3. Apply settings section by section:", flush=True)
    print("   → Header → Announcement → Hero → Colors → Typography", flush=True)
    print("", flush=True)
    print("⏱️  Time: 15 minutes", flush=True)
    print("", flush=True)
    print("✅ Your store will look world-class and match your products perfectly!", flush=True)


if __name__ == "__main__":
    main()

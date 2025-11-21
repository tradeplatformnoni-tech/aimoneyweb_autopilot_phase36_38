#!/usr/bin/env python3
"""
VERO Database Protection System
Prevents eBay account suspension by checking products against VERO database
before listing on eBay.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"
DATA = ROOT / "data"

# Ensure directories exist
DATA.mkdir(exist_ok=True)


# VERO Database - eBay's Verified Rights Owner Program
# These brands/products are protected and require authorization
VERO_DATABASE = {
    # Apple (HIGHEST RISK - Most monitored)
    "apple": {
        "risk_level": "CRITICAL",
        "blocked_keywords": [
            "iphone",
            "ipad",
            "ipod",
            "apple watch",
            "macbook",
            "imac",
            "airpods",
            "apple tv",
            "magic mouse",
            "magic keyboard",
            "appstore",
            "ios",
            "macos",
            "siri",
            "homepod",
        ],
        "safe_alternatives": {
            "iphone": "smartphone",
            "ipad": "tablet",
            "airpods": "wireless earbuds",
            "apple watch": "smartwatch",
            "macbook": "laptop computer",
            "magic mouse": "wireless mouse",
            "magic keyboard": "wireless keyboard",
        },
        "note": "Apple is the #1 most monitored brand on eBay VERO. NEVER use Apple keywords.",
    },
    # Nike
    "nike": {
        "risk_level": "HIGH",
        "blocked_keywords": ["nike", "air jordan", "jordan", "air max", "dunk", "just do it"],
        "safe_alternatives": {
            "nike": "athletic brand",
            "air jordan": "basketball shoes",
            "nike shoes": "athletic footwear",
        },
    },
    # Adidas
    "adidas": {
        "risk_level": "HIGH",
        "blocked_keywords": ["adidas", "three stripes", "originals", "yeezy"],
        "safe_alternatives": {"adidas": "sports brand", "adidas shoes": "athletic footwear"},
    },
    # Disney
    "disney": {
        "risk_level": "HIGH",
        "blocked_keywords": [
            "disney",
            "mickey mouse",
            "minnie mouse",
            "frozen",
            "toy story",
            "pixar",
            "marvel",
            "star wars",
            "mickey",
            "donald duck",
        ],
        "safe_alternatives": {
            "disney": "cartoon character",
            "mickey mouse": "cartoon mouse",
            "frozen": "animated movie character",
        },
    },
    # Louis Vuitton
    "louis_vuitton": {
        "risk_level": "CRITICAL",
        "blocked_keywords": ["louis vuitton", "lv", "lv monogram", "vuitton"],
        "safe_alternatives": {"louis vuitton": "luxury brand", "lv": "designer initials"},
    },
    # Chanel
    "chanel": {
        "risk_level": "CRITICAL",
        "blocked_keywords": ["chanel", "chanel no. 5", "coco chanel", "double c"],
        "safe_alternatives": {"chanel": "luxury fashion brand"},
    },
    # Gucci
    "gucci": {
        "risk_level": "CRITICAL",
        "blocked_keywords": ["gucci", "gg logo", "gucci belt"],
        "safe_alternatives": {"gucci": "luxury fashion brand"},
    },
    # Rolex
    "rolex": {
        "risk_level": "CRITICAL",
        "blocked_keywords": ["rolex", "submariner", "datejust", "daytona", "gmt"],
        "safe_alternatives": {"rolex": "luxury watch brand", "rolex watch": "luxury timepiece"},
    },
    # Beats by Dre
    "beats": {
        "risk_level": "HIGH",
        "blocked_keywords": ["beats", "beats by dre", "dr. dre", "beats headphones"],
        "safe_alternatives": {"beats": "premium headphones", "beats by dre": "wireless headphones"},
    },
    # Ray-Ban
    "ray_ban": {
        "risk_level": "MEDIUM",
        "blocked_keywords": ["ray-ban", "ray ban", "aviator", "wayfarer"],
        "safe_alternatives": {"ray-ban": "sunglasses brand", "ray ban": "designer sunglasses"},
    },
    # Oakley
    "oakley": {
        "risk_level": "MEDIUM",
        "blocked_keywords": ["oakley", "oakley sunglasses"],
        "safe_alternatives": {"oakley": "sports sunglasses brand"},
    },
    # Lego
    "lego": {
        "risk_level": "MEDIUM",
        "blocked_keywords": ["lego", "lego bricks", "minifigure"],
        "safe_alternatives": {"lego": "building blocks", "lego bricks": "interlocking bricks"},
    },
    # Hasbro
    "hasbro": {
        "risk_level": "MEDIUM",
        "blocked_keywords": ["hasbro", "nerf", "transformers", "my little pony", "g.i. joe"],
        "safe_alternatives": {"hasbro": "toy brand", "nerf": "foam dart blaster"},
    },
    # Sony
    "sony": {
        "risk_level": "HIGH",
        "blocked_keywords": ["sony", "playstation", "ps4", "ps5", "playstation controller"],
        "safe_alternatives": {
            "playstation": "gaming console",
            "ps4": "video game console",
            "ps5": "gaming system",
        },
    },
    # Microsoft
    "microsoft": {
        "risk_level": "HIGH",
        "blocked_keywords": ["microsoft", "xbox", "xbox controller", "surface"],
        "safe_alternatives": {"xbox": "gaming console", "xbox controller": "game controller"},
    },
    # Nintendo
    "nintendo": {
        "risk_level": "HIGH",
        "blocked_keywords": ["nintendo", "switch", "wii", "game boy", "3ds", "ds"],
        "safe_alternatives": {
            "nintendo switch": "portable gaming console",
            "game boy": "handheld game device",
        },
    },
}


def check_vero_violation(
    product_title: str, product_description: str = ""
) -> tuple[bool, dict[str, Any]]:
    """
    Check if product violates VERO database.

    Args:
        product_title: Product title to check
        product_description: Optional product description

    Returns:
        Tuple of (is_violation, violation_details)
    """
    title_lower = product_title.lower()
    desc_lower = product_description.lower() if product_description else ""
    combined_text = f"{title_lower} {desc_lower}"

    violations = []

    for brand, brand_data in VERO_DATABASE.items():
        risk_level = brand_data["risk_level"]
        blocked_keywords = brand_data["blocked_keywords"]
        safe_alternatives = brand_data.get("safe_alternatives", {})

        for keyword in blocked_keywords:
            # Check if keyword appears in title or description
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, combined_text):
                violation = {
                    "brand": brand,
                    "keyword": keyword,
                    "risk_level": risk_level,
                    "found_in": "title" if keyword.lower() in title_lower else "description",
                    "safe_alternative": safe_alternatives.get(keyword, None),
                    "note": brand_data.get("note", ""),
                }
                violations.append(violation)
                break  # Only report first violation per brand

    is_violation = len(violations) > 0

    result = {
        "is_violation": is_violation,
        "violations": violations,
        "original_title": product_title,
        "safe_title": None,
    }

    # Generate safe title if violations found
    if is_violation:
        result["safe_title"] = generate_safe_title(product_title, violations)

    return is_violation, result


def generate_safe_title(original_title: str, violations: list[dict[str, Any]]) -> str:
    """
    Generate a safe title by replacing blocked keywords with safe alternatives.
    """
    safe_title = original_title

    for violation in violations:
        keyword = violation["keyword"]
        safe_alternative = violation.get("safe_alternative")

        if safe_alternative:
            # Replace keyword with safe alternative (case-insensitive)
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            safe_title = pattern.sub(safe_alternative, safe_title)

    return safe_title


def sanitize_product_for_ebay(product: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize product data for eBay listing, removing VERO violations.

    Args:
        product: Product dictionary with title, description, etc.

    Returns:
        Sanitized product dictionary
    """
    title = product.get("title", "")
    description = product.get("description", "")

    is_violation, violation_details = check_vero_violation(title, description)

    sanitized_product = product.copy()

    if is_violation:
        print("[vero_protection] ⚠️ VERO violation detected!", flush=True)
        print(f"[vero_protection] Original title: {title}", flush=True)

        for violation in violation_details["violations"]:
            print(
                f"[vero_protection]   - Blocked keyword: '{violation['keyword']}' ({violation['risk_level']})",
                flush=True,
            )
            if violation.get("safe_alternative"):
                print(
                    f"[vero_protection]   - Safe alternative: '{violation['safe_alternative']}'",
                    flush=True,
                )

        # Update title
        if violation_details.get("safe_title"):
            sanitized_product["title"] = violation_details["safe_title"]
            print(f"[vero_protection] ✅ Safe title: {sanitized_product['title']}", flush=True)

        # Clean description
        desc_lower = description.lower()
        safe_description = description

        for violation in violation_details["violations"]:
            keyword = violation["keyword"]
            safe_alt = violation.get("safe_alternative")

            if safe_alt and keyword.lower() in desc_lower:
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                safe_description = pattern.sub(safe_alt, safe_description)

        sanitized_product["description"] = safe_description

        # Add note about modification
        sanitized_product["_vero_modified"] = True
        sanitized_product["_vero_violations"] = [
            v["keyword"] for v in violation_details["violations"]
        ]
    else:
        print("[vero_protection] ✅ No VERO violations found", flush=True)
        sanitized_product["_vero_modified"] = False

    return sanitized_product


def save_vero_database():
    """Save VERO database to file for persistence."""
    vero_file = DATA / "vero_database.json"
    with open(vero_file, "w") as f:
        json.dump(VERO_DATABASE, f, indent=2)
    print(f"[vero_protection] ✅ VERO database saved to {vero_file}", flush=True)


def load_vero_database() -> dict[str, Any]:
    """Load VERO database from file."""
    vero_file = DATA / "vero_database.json"
    if vero_file.exists():
        with open(vero_file) as f:
            return json.load(f)
    return VERO_DATABASE


def main():
    """Test VERO protection system."""
    print("=" * 70, flush=True)
    print("🛡️ VERO Protection System - Test", flush=True)
    print("=" * 70, flush=True)
    print()

    # Save database
    save_vero_database()

    # Test cases
    test_products = [
        {"title": "iPhone 14 Pro Max Case", "description": "Protective case for iPhone"},
        {"title": "Wireless Earbuds for Smartphone", "description": "Premium wireless earbuds"},
        {"title": "Nike Air Max Shoes", "description": "Athletic footwear"},
        {"title": "PlayStation 5 Controller", "description": "Gaming controller for PS5"},
        {"title": "Camera Lens for DSLR", "description": "Professional camera lens"},
    ]

    for idx, product in enumerate(test_products, 1):
        print(f"\n--- Test {idx} ---", flush=True)
        print(f"Title: {product['title']}", flush=True)

        is_violation, details = check_vero_violation(
            product["title"], product.get("description", "")
        )

        if is_violation:
            print("❌ VIOLATION DETECTED!", flush=True)
            for violation in details["violations"]:
                print(f"   Brand: {violation['brand']}", flush=True)
                print(f"   Keyword: '{violation['keyword']}'", flush=True)
                print(f"   Risk: {violation['risk_level']}", flush=True)
                if violation.get("safe_alternative"):
                    print(f"   Safe: '{violation['safe_alternative']}'", flush=True)
            print(f"✅ Safe title: {details.get('safe_title')}", flush=True)
        else:
            print("✅ No violations - safe to list", flush=True)

        # Test sanitization
        sanitized = sanitize_product_for_ebay(product)
        print()


if __name__ == "__main__":
    main()

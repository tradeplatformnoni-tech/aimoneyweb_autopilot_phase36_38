#!/usr/bin/env python3
"""
Multi-Platform Policy Compliance Engine
Prevents account suspensions across ALL marketplaces:
- eBay (VERO + Policy Violations)
- Amazon (Category Restrictions, Prohibited Items)
- Facebook Marketplace (Community Standards)
- Etsy (Handmade/Policies)
- Other platforms

LEARNED FROM: eBay account suspension - comprehensive protection needed
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STATE = ROOT / "state"
LOGS = ROOT / "logs"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


class PolicyComplianceEngine:
    """
    Comprehensive Policy Compliance System
    Prevents account suspensions across all marketplaces
    """

    def __init__(self):
        self.violations_checked = 0
        self.violations_found = 0
        self.products_blocked = 0

        # Load policy databases
        self.ebay_policies = self._load_ebay_policies()
        self.amazon_policies = self._load_amazon_policies()
        self.facebook_policies = self._load_facebook_policies()
        self.etsy_policies = self._load_etsy_policies()
        self.general_policies = self._load_general_policies()

    def _load_ebay_policies(self) -> dict[str, Any]:
        """eBay policy database - learned from suspension."""
        return {
            "vero_protected_brands": {
                # Already have VERO database - expanded
                "apple": {"risk": "CRITICAL", "keywords": ["iphone", "ipad", "airpods", "apple"]},
                "nike": {"risk": "HIGH", "keywords": ["nike", "air jordan"]},
                # Add more...
            },
            "prohibited_items": [
                "weapons",
                "firearms",
                "ammunition",
                "knives",
                "drugs",
                "prescription",
                "controlled substances",
                "counterfeit",
                "replica",
                "fake",
                "adult content",
                "pornography",
                "stolen goods",
                "recalled items",
            ],
            "prohibited_keywords": [
                "authentic",
                "genuine",
                "oem",
                "original equipment",
                "guaranteed authentic",
                "100% authentic",
                "brand new in box",  # if not authorized seller
            ],
            "title_violations": [
                "all caps titles",
                "excessive punctuation (!!!!)",
                "spam keywords",
                "misleading claims",
            ],
            "category_restrictions": {
                "electronics": ["requires authentication for certain brands"],
                "collectibles": ["requires authenticity proof"],
            },
            "shipping_violations": [
                "shipping time > 30 days",
                "no tracking provided",
                "incorrect shipping location",
            ],
            "price_violations": [
                "price too low (suspicious)",
                "price manipulation",
                "bait and switch",
            ],
        }

    def _load_amazon_policies(self) -> dict[str, Any]:
        """Amazon Seller Central policies."""
        return {
            "prohibited_categories": [
                "weapons",
                "drugs",
                "alcohol",
                "tobacco",
                "pesticides",
                "hazardous materials",
                "recalled items",
                "stolen goods",
            ],
            "restricted_categories": {
                "requires_approval": ["health & personal care", "beauty", "grocery"],
                "gated_categories": ["automotive", "clothing", "jewelry"],
            },
            "product_requirements": [
                "must have UPC/EAN",
                "must have brand approval",
                "must have compliance documents",
            ],
            "prohibited_keywords": [
                "best seller",
                "top rated",
                "amazon's choice",
                "comparison with competitors",
                "fake reviews",
                "review manipulation",
            ],
            "listing_violations": [
                "incorrect category",
                "missing required attributes",
                "inaccurate product information",
            ],
            "shipping_requirements": [
                "must ship within 2 days",
                "must use approved carriers",
                "must provide tracking",
            ],
        }

    def _load_facebook_policies(self) -> dict[str, Any]:
        """Facebook Marketplace policies."""
        return {
            "community_standards": [
                "no weapons",
                "no drugs",
                "no adult content",
                "no tobacco",
                "no alcohol sales",
                "no counterfeit goods",
            ],
            "prohibited_items": [
                "animals",
                "currency",
                "tickets (scalping)",
                "health products (unapproved)",
                "financial services",
            ],
            "location_requirements": [
                "must be local pickup or shipping",
                "accurate location",
                "no misleading location",
            ],
            "content_violations": [
                "misleading photos",
                "stock photos only",
                "no actual product photos",
            ],
            "price_requirements": [
                "must list actual price",
                "no 'contact for price'",
                "no auction-style listings",
            ],
        }

    def _load_etsy_policies(self) -> dict[str, Any]:
        """Etsy marketplace policies."""
        return {
            "handmade_requirements": [
                "must be handmade, vintage, or craft supply",
                "no mass-produced items",
                "no reselling unless vintage",
            ],
            "prohibited_items": [
                "weapons",
                "drugs",
                "alcohol",
                "counterfeit items",
                "mass-produced items (not handmade)",
            ],
            "listing_requirements": [
                "must be handmade by seller",
                "or vintage (20+ years old)",
                "or craft supply",
            ],
            "prohibited_keywords": ["handmade by [other person]", "mass produced", "factory made"],
        }

    def _load_general_policies(self) -> dict[str, Any]:
        """General dropshipping violations across all platforms."""
        return {
            "common_violations": [
                "dropshipping without disclosure",
                "long shipping times",
                "incorrect product descriptions",
                "stock photos only",
                "no actual inventory",
            ],
            "account_safety": [
                "too many listings at once",
                "similar listings (duplicate)",
                "price discrepancies",
                "suspicious activity patterns",
            ],
            "communication_violations": [
                "misleading messages",
                "no response to buyers",
                "cancelled orders after payment",
            ],
        }

    def check_product_compliance(
        self, product: dict[str, Any], platform: str = "ebay"
    ) -> tuple[bool, dict[str, Any]]:
        """
        Comprehensive product compliance check.
        Returns (is_compliant, violation_details)
        """
        self.violations_checked += 1

        title = product.get("title", "").lower()
        description = product.get("description", "").lower()
        category = product.get("category", "").lower()
        price = product.get("price", 0)
        shipping_days = product.get("shipping_days", 0)

        violations = []
        risk_level = "LOW"

        # Platform-specific checks
        if platform == "ebay":
            violations.extend(
                self._check_ebay_compliance(
                    product, title, description, category, price, shipping_days
                )
            )
        elif platform == "amazon":
            violations.extend(self._check_amazon_compliance(product, title, description, category))
        elif platform == "facebook":
            violations.extend(self._check_facebook_compliance(product, title, description))
        elif platform == "etsy":
            violations.extend(self._check_etsy_compliance(product, title, description))

        # General checks (all platforms)
        violations.extend(self._check_general_compliance(product, title, description))

        # Determine risk level
        if violations:
            critical_count = sum(1 for v in violations if v.get("severity") == "CRITICAL")
            high_count = sum(1 for v in violations if v.get("severity") == "HIGH")

            if critical_count > 0:
                risk_level = "CRITICAL"
            elif high_count > 0:
                risk_level = "HIGH"
            else:
                risk_level = "MEDIUM"

            self.violations_found += 1

        is_compliant = len(violations) == 0

        result = {
            "is_compliant": is_compliant,
            "risk_level": risk_level,
            "violations": violations,
            "platform": platform,
            "product_title": product.get("title", ""),
            "recommendation": "BLOCK" if not is_compliant else "APPROVE",
        }

        if not is_compliant:
            self.products_blocked += 1

        return is_compliant, result

    def _check_ebay_compliance(
        self,
        product: dict,
        title: str,
        description: str,
        category: str,
        price: float,
        shipping_days: int,
    ) -> list[dict[str, Any]]:
        """eBay-specific compliance checks."""
        violations = []
        policies = self.ebay_policies

        # Check prohibited items
        for prohibited in policies["prohibited_items"]:
            if prohibited in title or prohibited in description:
                violations.append(
                    {
                        "type": "PROHIBITED_ITEM",
                        "severity": "CRITICAL",
                        "rule": f"eBay prohibits: {prohibited}",
                        "found": prohibited,
                        "fix": "Remove product - cannot list prohibited items",
                    }
                )

        # Check prohibited keywords
        for keyword in policies["prohibited_keywords"]:
            if keyword in title or keyword in description:
                violations.append(
                    {
                        "type": "PROHIBITED_KEYWORD",
                        "severity": "HIGH",
                        "rule": f"eBay prohibits keyword: {keyword}",
                        "found": keyword,
                        "fix": f"Remove '{keyword}' from title/description",
                    }
                )

        # Check title violations
        if title.isupper():
            violations.append(
                {
                    "type": "TITLE_VIOLATION",
                    "severity": "MEDIUM",
                    "rule": "eBay: No all-caps titles",
                    "found": "All caps title",
                    "fix": "Use normal case (title case)",
                }
            )

        if title.count("!") > 2:
            violations.append(
                {
                    "type": "TITLE_VIOLATION",
                    "severity": "MEDIUM",
                    "rule": "eBay: Excessive punctuation",
                    "found": "Too many exclamation marks",
                    "fix": "Remove excessive punctuation",
                }
            )

        # Check shipping violations
        if shipping_days > 30:
            violations.append(
                {
                    "type": "SHIPPING_VIOLATION",
                    "severity": "HIGH",
                    "rule": "eBay: Shipping > 30 days not allowed",
                    "found": f"{shipping_days} days shipping",
                    "fix": "Use faster shipping or don't list",
                }
            )

        # Check price violations
        if price < 1.0:
            violations.append(
                {
                    "type": "PRICE_VIOLATION",
                    "severity": "MEDIUM",
                    "rule": "eBay: Price too low (suspicious)",
                    "found": f"Price: ${price}",
                    "fix": "Ensure price is realistic",
                }
            )

        return violations

    def _check_amazon_compliance(
        self, product: dict, title: str, description: str, category: str
    ) -> list[dict[str, Any]]:
        """Amazon-specific compliance checks."""
        violations = []
        policies = self.amazon_policies

        # Check prohibited categories
        for prohibited in policies["prohibited_categories"]:
            if prohibited in category or prohibited in title:
                violations.append(
                    {
                        "type": "PROHIBITED_CATEGORY",
                        "severity": "CRITICAL",
                        "rule": f"Amazon prohibits: {prohibited}",
                        "found": prohibited,
                        "fix": "Cannot list in this category",
                    }
                )

        # Check restricted categories
        restricted_cats = policies["restricted_categories"]
        if isinstance(restricted_cats, dict):
            for restricted in restricted_cats.get("requires_approval", []):
                if restricted in category:
                    violations.append(
                        {
                            "type": "RESTRICTED_CATEGORY",
                            "severity": "HIGH",
                            "rule": f"Amazon requires approval: {restricted}",
                            "found": restricted,
                            "fix": "Get category approval before listing",
                        }
                    )

        # Check prohibited keywords
        for keyword in policies["prohibited_keywords"]:
            if keyword in title or keyword in description:
                violations.append(
                    {
                        "type": "PROHIBITED_KEYWORD",
                        "severity": "HIGH",
                        "rule": f"Amazon prohibits: {keyword}",
                        "found": keyword,
                        "fix": f"Remove '{keyword}'",
                    }
                )

        return violations

    def _check_facebook_compliance(
        self, product: dict, title: str, description: str
    ) -> list[dict[str, Any]]:
        """Facebook Marketplace compliance checks."""
        violations = []
        policies = self.facebook_policies

        # Check community standards
        for prohibited in policies["community_standards"]:
            if prohibited in title or prohibited in description:
                violations.append(
                    {
                        "type": "COMMUNITY_STANDARDS_VIOLATION",
                        "severity": "CRITICAL",
                        "rule": f"Facebook prohibits: {prohibited}",
                        "found": prohibited,
                        "fix": "Remove product - violates community standards",
                    }
                )

        # Check prohibited items
        for item in policies["prohibited_items"]:
            if item in title or item in description:
                violations.append(
                    {
                        "type": "PROHIBITED_ITEM",
                        "severity": "CRITICAL",
                        "rule": f"Facebook prohibits: {item}",
                        "found": item,
                        "fix": "Cannot list on Facebook Marketplace",
                    }
                )

        return violations

    def _check_etsy_compliance(
        self, product: dict, title: str, description: str
    ) -> list[dict[str, Any]]:
        """Etsy-specific compliance checks."""
        violations = []
        policies = self.etsy_policies

        # Check handmade requirements
        if (
            "handmade" not in description
            and "vintage" not in description
            and "craft supply" not in description
        ):
            violations.append(
                {
                    "type": "HANDMADE_VIOLATION",
                    "severity": "CRITICAL",
                    "rule": "Etsy requires: Handmade, Vintage, or Craft Supply",
                    "found": "Not marked as handmade/vintage/craft supply",
                    "fix": "Only list handmade, vintage (20+ years), or craft supplies",
                }
            )

        # Check prohibited keywords
        for keyword in policies["prohibited_keywords"]:
            if keyword in title or keyword in description:
                violations.append(
                    {
                        "type": "PROHIBITED_KEYWORD",
                        "severity": "HIGH",
                        "rule": f"Etsy prohibits: {keyword}",
                        "found": keyword,
                        "fix": f"Remove '{keyword}'",
                    }
                )

        return violations

    def _check_general_compliance(
        self, product: dict, title: str, description: str
    ) -> list[dict[str, Any]]:
        """General compliance checks for all platforms."""
        violations = []
        policies = self.general_policies

        # Check common violations
        for violation in policies["common_violations"]:
            if violation in description:
                violations.append(
                    {
                        "type": "GENERAL_VIOLATION",
                        "severity": "MEDIUM",
                        "rule": f"Common violation: {violation}",
                        "found": violation,
                        "fix": "Fix description to comply",
                    }
                )

        # Check for misleading claims
        misleading = ["guaranteed", "promise", "best ever", "lowest price"]
        for claim in misleading:
            if claim in title or claim in description:
                violations.append(
                    {
                        "type": "MISLEADING_CLAIM",
                        "severity": "MEDIUM",
                        "rule": "Avoid misleading claims",
                        "found": claim,
                        "fix": "Use factual descriptions only",
                    }
                )

        return violations

    def sanitize_product(self, product: dict[str, Any], platform: str = "ebay") -> dict[str, Any]:
        """
        Sanitize product to make it compliant.
        Returns sanitized product data.
        """
        is_compliant, details = self.check_product_compliance(product, platform)

        if is_compliant:
            return product

        sanitized = product.copy()
        title = sanitized.get("title", "")
        description = sanitized.get("description", "")

        # Fix violations
        for violation in details["violations"]:
            fix_type = violation.get("type")
            found = violation.get("found", "")

            if fix_type == "PROHIBITED_KEYWORD":
                # Remove prohibited keywords
                title = title.replace(found, "")
                description = description.replace(found, "")

            elif fix_type == "TITLE_VIOLATION":
                if "All caps" in found:
                    title = title.title()  # Convert to title case
                elif "exclamation" in found.lower():
                    title = re.sub(r"!+", "", title)  # Remove exclamation marks

            elif fix_type == "MISLEADING_CLAIM":
                # Remove misleading claims
                title = title.replace(found, "")
                description = description.replace(found, "")

        sanitized["title"] = title.strip()
        sanitized["description"] = description.strip()
        sanitized["_compliant"] = True
        sanitized["_violations_fixed"] = [v.get("type") for v in details["violations"]]

        return sanitized

    def get_compliance_report(self) -> dict[str, Any]:
        """Get compliance statistics."""
        return {
            "violations_checked": self.violations_checked,
            "violations_found": self.violations_found,
            "products_blocked": self.products_blocked,
            "compliance_rate": (
                (self.violations_checked - self.violations_found) / self.violations_checked * 100
                if self.violations_checked > 0
                else 100
            ),
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """Test compliance engine."""
    engine = PolicyComplianceEngine()

    print("=" * 70)
    print("🛡️ Policy Compliance Engine - Test")
    print("=" * 70)
    print()

    # Test products
    test_products = [
        {
            "title": "iPhone 14 Pro Max Case - GUARANTEED AUTHENTIC!!!",
            "description": "Best ever phone case for iPhone",
            "category": "electronics",
            "price": 0.99,
            "shipping_days": 45,
        },
        {
            "title": "Camera Lens for DSLR",
            "description": "Professional camera lens",
            "category": "electronics",
            "price": 29.99,
            "shipping_days": 15,
        },
        {
            "title": "WEAPONS KNIFE SET",
            "description": "Collection of weapons",
            "category": "collectibles",
            "price": 50.00,
            "shipping_days": 10,
        },
    ]

    for idx, product in enumerate(test_products, 1):
        print(f"\n--- Test Product {idx} ---")
        print(f"Title: {product['title']}")

        is_compliant, details = engine.check_product_compliance(product, platform="ebay")

        if is_compliant:
            print("✅ COMPLIANT - Safe to list")
        else:
            print(f"❌ NOT COMPLIANT - Risk: {details['risk_level']}")
            print(f"Recommendation: {details['recommendation']}")
            print("\nViolations:")
            for violation in details["violations"]:
                print(f"  - {violation['type']}: {violation['rule']}")
                print(f"    Fix: {violation['fix']}")

        # Try to sanitize
        if not is_compliant:
            sanitized = engine.sanitize_product(product, platform="ebay")
            print(f"\n✅ Sanitized title: {sanitized['title']}")

    print("\n📊 Compliance Report:")
    report = engine.get_compliance_report()
    for key, value in report.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    main()

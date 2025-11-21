#!/usr/bin/env python3
"""
eBay Product Research Algorithm - World-Class Product Selection
Identifies high-profit, high-traffic products for eBay dropshipping.
Goal: $1M revenue in 2 years through intelligent product selection.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(os.path.expanduser("~/neolight"))
STATE = ROOT / "state"
LOGS = ROOT / "logs"

# Product categories and trends (updated monthly)
PRODUCT_CATEGORIES = {
    "electronics": {
        "tech_accessories": {
            "keywords": [
                "phone case",
                "screen protector",
                "wireless charger",
                "USB cable",
                "power bank",
            ],
            "avg_price_range": (10, 50),
            "profit_margin_target": 45,
            "monthly_trend": "high",
            "competition": "medium",
            "search_volume": 150000,
        },
        "cameras_photography": {
            "keywords": [
                "camera lens",
                "tripod",
                "camera bag",
                "memory card",
                "camera strap",
                "camera filter",
            ],
            "avg_price_range": (25, 150),
            "profit_margin_target": 40,
            "monthly_trend": "very_high",
            "competition": "low",
            "search_volume": 95000,
            "seasonal_boost": ["holiday", "summer"],
        },
        "smart_home": {
            "keywords": ["smart plug", "smart bulb", "smart switch", "smart sensor"],
            "avg_price_range": (15, 60),
            "profit_margin_target": 42,
            "monthly_trend": "high",
            "competition": "medium",
            "search_volume": 125000,
        },
        "audio": {
            "keywords": ["wireless earbuds", "bluetooth speaker", "headphone", "microphone"],
            "avg_price_range": (20, 80),
            "profit_margin_target": 40,
            "monthly_trend": "high",
            "competition": "high",
            "search_volume": 180000,
        },
    },
    "health_beauty": {
        "skincare": {
            "keywords": ["face mask", "skincare set", "cleanser", "moisturizer", "serum"],
            "avg_price_range": (15, 45),
            "profit_margin_target": 50,
            "monthly_trend": "very_high",
            "competition": "medium",
            "search_volume": 200000,
            "growth_rate": 200,  # % YoY growth
        },
        "hair_care": {
            "keywords": ["hair brush", "hair straightener", "hair dryer", "hair accessories"],
            "avg_price_range": (12, 40),
            "profit_margin_target": 48,
            "monthly_trend": "high",
            "competition": "medium",
            "search_volume": 95000,
            "growth_rate": 150,
        },
        "supplements": {
            "keywords": ["vitamin", "supplement", "protein powder", "wellness"],
            "avg_price_range": (20, 65),
            "profit_margin_target": 45,
            "monthly_trend": "high",
            "competition": "high",
            "search_volume": 145000,
        },
    },
    "home_garden": {
        "home_improvement": {
            "keywords": ["double sided tape", "organizer", "storage box", "shelf"],
            "avg_price_range": (8, 35),
            "profit_margin_target": 50,
            "monthly_trend": "medium",
            "competition": "low",
            "search_volume": 110000,
        },
        "kitchen": {
            "keywords": ["kitchen gadget", "cooking tool", "kitchen organizer"],
            "avg_price_range": (10, 40),
            "profit_margin_target": 48,
            "monthly_trend": "medium",
            "competition": "medium",
            "search_volume": 125000,
        },
    },
    "pet_supplies": {
        "pet_accessories": {
            "keywords": ["pet tag", "pet collar", "pet bed", "pet toy"],
            "avg_price_range": (5, 30),
            "profit_margin_target": 50,
            "monthly_trend": "high",
            "competition": "low",
            "search_volume": 135000,
        },
        "pet_care": {
            "keywords": ["pet brush", "pet grooming", "pet food bowl"],
            "avg_price_range": (8, 25),
            "profit_margin_target": 48,
            "monthly_trend": "medium",
            "competition": "low",
            "search_volume": 85000,
        },
    },
    "automotive": {
        "car_accessories": {
            "keywords": ["car charger", "phone mount", "car organizer", "tire inflator"],
            "avg_price_range": (15, 50),
            "profit_margin_target": 42,
            "monthly_trend": "medium",
            "competition": "medium",
            "search_volume": 105000,
        },
        "emergency": {
            "keywords": ["jump starter", "tire inflator", "emergency kit"],
            "avg_price_range": (20, 80),
            "profit_margin_target": 40,
            "monthly_trend": "high",
            "competition": "medium",
            "search_volume": 75000,
        },
    },
    "fitness": {
        "workout_equipment": {
            "keywords": ["resistance band", "yoga mat", "dumbbell", "fitness tracker"],
            "avg_price_range": (12, 45),
            "profit_margin_target": 45,
            "monthly_trend": "high",
            "competition": "medium",
            "search_volume": 140000,
            "seasonal_boost": ["new_year", "summer"],
        }
    },
    "gaming": {
        "gaming_accessories": {
            "keywords": ["gaming mouse", "gaming keyboard", "gaming headset", "controller"],
            "avg_price_range": (25, 120),
            "profit_margin_target": 38,
            "monthly_trend": "very_high",
            "competition": "high",
            "search_volume": 180000,
            "growth_rate": 30,
        }
    },
}


def get_current_month() -> str:
    """Get current month for trend analysis."""
    return datetime.now().strftime("%Y-%m")


def get_seasonal_multiplier() -> float:
    """Get seasonal boost multiplier based on current month."""
    month = datetime.now().month

    # Holiday season boost (Oct-Dec)
    if month in [10, 11, 12]:
        return 1.3

    # New Year resolution boost (Jan-Feb)
    if month in [1, 2]:
        return 1.2

    # Summer boost (May-Aug)
    if month in [5, 6, 7, 8]:
        return 1.15

    return 1.0


def calculate_product_score(
    category: str, subcategory: str, product_data: dict[str, Any], supplier_cost: float
) -> dict[str, Any]:
    """
    Calculate intelligent product score for eBay listing.
    Higher score = better product to list.
    """
    cat_data = PRODUCT_CATEGORIES.get(category, {}).get(subcategory, {})

    # Base metrics
    profit_margin_target = cat_data.get("profit_margin_target", 40)
    avg_price_min, avg_price_max = cat_data.get("avg_price_range", (10, 50))
    search_volume = cat_data.get("search_volume", 50000)
    competition = cat_data.get("competition", "medium")
    monthly_trend = cat_data.get("monthly_trend", "medium")
    growth_rate = cat_data.get("growth_rate", 0)

    # Calculate actual profit margin
    selling_price = product_data.get("selling_price", 0)
    actual_margin = (
        ((selling_price - supplier_cost) / selling_price * 100) if selling_price > 0 else 0
    )

    # Score components (0-100 scale)
    score = 0.0

    # 1. Profit margin score (30 points)
    if actual_margin >= profit_margin_target:
        score += 30
    elif actual_margin >= profit_margin_target * 0.8:
        score += 20
    elif actual_margin >= profit_margin_target * 0.6:
        score += 10

    # 2. Price range score (15 points)
    if avg_price_min <= selling_price <= avg_price_max:
        score += 15
    elif avg_price_min * 0.8 <= selling_price <= avg_price_max * 1.2:
        score += 10
    else:
        score += 5

    # 3. Demand/volume score (25 points)
    volume_score = min(25, (search_volume / 200000) * 25)
    score += volume_score

    # 4. Competition score (20 points) - lower competition = higher score
    competition_map = {"low": 20, "medium": 12, "high": 5, "very_high": 15}
    score += competition_map.get(competition, 10)

    # 5. Trend score (10 points)
    trend_map = {"low": 2, "medium": 5, "high": 8, "very_high": 10}
    score += trend_map.get(monthly_trend, 5)

    # 6. Seasonal boost (bonus points)
    seasonal = get_seasonal_multiplier()
    if cat_data.get("seasonal_boost"):
        score *= seasonal

    # 7. Growth rate bonus (if available)
    if growth_rate > 100:
        score *= 1.2

    return {
        "score": round(score, 2),
        "profit_margin": round(actual_margin, 2),
        "selling_price": selling_price,
        "supplier_cost": supplier_cost,
        "category": category,
        "subcategory": subcategory,
        "search_volume": search_volume,
        "competition_level": competition,
        "trend": monthly_trend,
        "seasonal_boost": seasonal > 1.0,
    }


def get_recommended_keywords(category: str, subcategory: str, limit: int = 10) -> list[str]:
    """Get recommended keywords for product search."""
    cat_data = PRODUCT_CATEGORIES.get(category, {}).get(subcategory, {})
    keywords = cat_data.get("keywords", [])
    return keywords[:limit]


def analyze_trending_products(trending_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Analyze trending products and rank by profitability + demand.
    Returns top products sorted by score.
    """
    analyzed = []

    for product in trending_data:
        # Try to identify category from product name/description
        product_name = product.get("signal", "").lower()

        # Match to category
        category = "electronics"  # default
        subcategory = "tech_accessories"  # default

        for cat, subcats in PRODUCT_CATEGORIES.items():
            for subcat, data in subcats.items():
                keywords = [k.lower() for k in data.get("keywords", [])]
                if any(kw in product_name for kw in keywords):
                    category = cat
                    subcategory = subcat
                    break

        # Estimate supplier cost (would come from AutoDS search)
        estimated_cost = product.get("estimated_cost", 10.0)

        # Calculate pricing
        cat_data = PRODUCT_CATEGORIES.get(category, {}).get(subcategory, {})
        profit_target = cat_data.get("profit_margin_target", 40)
        selling_price = estimated_cost * (1 + profit_target / 100)

        product_data = {
            "product_title": product.get("signal", ""),
            "selling_price": round(selling_price, 2),
            "estimated_cost": estimated_cost,
        }

        # Calculate score
        score_data = calculate_product_score(category, subcategory, product_data, estimated_cost)

        analyzed.append({**product_data, **score_data, "recommended": score_data["score"] >= 60})

    # Sort by score (highest first)
    analyzed.sort(key=lambda x: x["score"], reverse=True)

    return analyzed


def get_top_categories_for_month() -> list[dict[str, Any]]:
    """
    Get top categories for current month based on trends and seasonality.
    Updates monthly based on market research.
    """
    month = datetime.now().month
    seasonal = get_seasonal_multiplier()

    top_categories = []

    for category, subcats in PRODUCT_CATEGORIES.items():
        for subcat, data in subcats.items():
            trend = data.get("monthly_trend", "medium")
            search_vol = data.get("search_volume", 0)

            # Calculate priority score
            priority = search_vol * seasonal

            if trend in ["high", "very_high"]:
                priority *= 1.5

            top_categories.append(
                {
                    "category": category,
                    "subcategory": subcat,
                    "priority_score": priority,
                    "keywords": data.get("keywords", []),
                    "avg_price_range": data.get("avg_price_range", (10, 50)),
                    "profit_margin_target": data.get("profit_margin_target", 40),
                    "trend": trend,
                    "competition": data.get("competition", "medium"),
                    "search_volume": search_vol,
                }
            )

    # Sort by priority
    top_categories.sort(key=lambda x: x["priority_score"], reverse=True)

    return top_categories[:15]  # Top 15 categories


def save_monthly_trends():
    """Save monthly trend analysis for tracking."""
    trends_file = STATE / "ebay_monthly_trends.json"

    trends = {
        "analysis_date": datetime.now().isoformat(),
        "month": get_current_month(),
        "top_categories": get_top_categories_for_month(),
        "seasonal_multiplier": get_seasonal_multiplier(),
    }

    trends_file.write_text(json.dumps(trends, indent=2))
    print(f"[ebay_product_researcher] 💾 Saved monthly trends to {trends_file}", flush=True)

    return trends


def main():
    """Main product research function."""
    print("=" * 70, flush=True)
    print("eBay Product Research Algorithm - Top Categories for Current Month", flush=True)
    print("=" * 70, flush=True)

    # Save monthly trends
    trends = save_monthly_trends()

    print(f"\n📅 Analysis Date: {trends['analysis_date']}", flush=True)
    print(f"📊 Seasonal Multiplier: {trends['seasonal_multiplier']:.2f}x", flush=True)

    print("\n🏆 TOP 15 CATEGORIES FOR THIS MONTH:\n", flush=True)

    for idx, cat in enumerate(trends["top_categories"], 1):
        print(
            f"{idx:2d}. {cat['category'].upper()} > {cat['subcategory'].replace('_', ' ').title()}",
            flush=True,
        )
        print(f"    Keywords: {', '.join(cat['keywords'][:5])}", flush=True)
        print(
            f"    Profit Target: {cat['profit_margin_target']}% | Price Range: ${cat['avg_price_range'][0]}-${cat['avg_price_range'][1]}",
            flush=True,
        )
        print(
            f"    Trend: {cat['trend']} | Competition: {cat['competition']} | Search Vol: {cat['search_volume']:,}",
            flush=True,
        )
        print()

    print("=" * 70, flush=True)
    print("✅ Product research complete! Use these categories for product sourcing.", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()

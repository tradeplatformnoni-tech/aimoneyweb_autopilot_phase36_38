#!/usr/bin/env python3
"""
Shopify Store Editor - Make edits to your store from terminal
"""

import os
from typing import Any

import requests

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

SHOPIFY_API_VERSION = "2024-01"
BASE_URL = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}"


def shopify_request(method: str, endpoint: str, data: dict | None = None) -> dict[str, Any]:
    """Make Shopify API request."""
    url = f"{BASE_URL}/{endpoint}"
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN, "Content-Type": "application/json"}

    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "POST":
        response = requests.post(url, headers=headers, json=data)
    elif method == "PUT":
        response = requests.put(url, headers=headers, json=data)
    elif method == "DELETE":
        response = requests.delete(url, headers=headers)
    else:
        raise ValueError(f"Unknown method: {method}")

    response.raise_for_status()
    return response.json()


def get_shop_info() -> dict[str, Any]:
    """Get shop information."""
    return shopify_request("GET", "shop.json")


def update_shop_name(new_name: str) -> bool:
    """Update shop name."""
    try:
        data = {"shop": {"name": new_name}}
        shopify_request("PUT", "shop.json", data)
        print(f"✅ Shop name updated to: {new_name}")
        return True
    except Exception as e:
        print(f"❌ Error updating shop name: {e}")
        return False


def list_products(limit: int = 10) -> list:
    """List products."""
    try:
        response = shopify_request("GET", f"products.json?limit={limit}")
        return response.get("products", [])
    except Exception as e:
        print(f"❌ Error listing products: {e}")
        return []


def create_product(title: str, price: str, description: str = "") -> dict | None:
    """Create a product."""
    try:
        data = {
            "product": {"title": title, "variants": [{"price": price}], "body_html": description}
        }
        response = shopify_request("POST", "products.json", data)
        product = response.get("product", {})
        print(f"✅ Product created: {product.get('title')} (ID: {product.get('id')})")
        return product
    except Exception as e:
        print(f"❌ Error creating product: {e}")
        return None


def update_product(product_id: str, updates: dict[str, Any]) -> bool:
    """Update a product."""
    try:
        data = {"product": updates}
        shopify_request("PUT", f"products/{product_id}.json", data)
        print(f"✅ Product {product_id} updated")
        return True
    except Exception as e:
        print(f"❌ Error updating product: {e}")
        return False


def get_orders(limit: int = 10) -> list:
    """Get recent orders."""
    try:
        response = shopify_request("GET", f"orders.json?limit={limit}&status=any")
        return response.get("orders", [])
    except Exception as e:
        print(f"❌ Error getting orders: {e}")
        return []


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Shopify Store Editor")
        print("Usage:")
        print("  python3 shopify_edit.py info           # Get store info")
        print("  python3 shopify_edit.py products      # List products")
        print("  python3 shopify_edit.py orders         # List orders")
        print("  python3 shopify_edit.py create 'Title' '19.99'  # Create product")
        sys.exit(1)

    command = sys.argv[1]

    if command == "info":
        info = get_shop_info()
        shop = info.get("shop", {})
        print(f"Store: {shop.get('name')}")
        print(f"Domain: {shop.get('domain')}")
        print(f"Email: {shop.get('email')}")
        print(f"Plan: {shop.get('plan_name')}")

    elif command == "products":
        products = list_products()
        print(f"\nProducts ({len(products)}):")
        for p in products:
            print(f"  • {p.get('title')} (ID: {p.get('id')})")

    elif command == "orders":
        orders = get_orders()
        print(f"\nOrders ({len(orders)}):")
        for o in orders:
            print(f"  • Order #{o.get('order_number')} - ${o.get('total_price')}")

    elif command == "create" and len(sys.argv) >= 4:
        title = sys.argv[2]
        price = sys.argv[3]
        create_product(title, price)

    else:
        print("Unknown command")

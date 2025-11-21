#!/usr/bin/env python3
"""
Add Shipping Policy to Shopify Store via API
"""

import os
from pathlib import Path

import requests

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

SHOPIFY_API_VERSION = "2024-01"
BASE_URL = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}"
GRAPHQL_URL = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"

ROOT = Path(os.path.expanduser("~/neolight"))


def read_shipping_policy():
    """Read shipping policy content."""
    policy_file = ROOT / "policy_shipping_policy.html"
    if policy_file.exists():
        return policy_file.read_text(encoding="utf-8")
    return None


def add_policy_via_graphql(policy_content: str):
    """Attempt to add policy via GraphQL Admin API."""
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN, "Content-Type": "application/json"}

    # GraphQL mutation to create/update shipping policy
    mutation = """
    mutation shopPoliciesCreate($policies: [ShopPolicyInput!]!) {
      shopPoliciesCreate(policies: $policies) {
        shop {
          privacyPolicy {
            id
            body
          }
          refundPolicy {
            id
            body
          }
          termsOfService {
            id
            body
          }
          shippingPolicy {
            id
            body
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    variables = {"policies": [{"type": "SHIPPING_POLICY", "body": policy_content}]}

    payload = {"query": mutation, "variables": variables}

    try:
        response = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()

        if result.get("data", {}).get("shopPoliciesCreate"):
            errors = result["data"]["shopPoliciesCreate"].get("userErrors", [])
            if errors:
                print(f"⚠️  GraphQL errors: {errors}", flush=True)
                return False

            shipping_policy = (
                result["data"]["shopPoliciesCreate"].get("shop", {}).get("shippingPolicy")
            )
            if shipping_policy:
                print("✅ Shipping policy added via GraphQL!", flush=True)
                return True

        return False
    except Exception as e:
        print(f"⚠️  GraphQL attempt failed: {e}", flush=True)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_text = e.response.text[:500]
                print(f"   Response: {error_text}", flush=True)
            except Exception:
                pass
        return False


def get_current_policies():
    """Get current shop policies to check if shipping policy exists."""
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN, "Content-Type": "application/json"}

    query = """
    query {
      shop {
        shippingPolicy {
          id
          body
          title
        }
      }
    }
    """

    payload = {"query": query}

    try:
        response = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()

        shop_data = result.get("data", {}).get("shop", {})
        shipping_policy = shop_data.get("shippingPolicy")

        if shipping_policy:
            print(
                f"📋 Current shipping policy exists: {bool(shipping_policy.get('body'))}",
                flush=True,
            )
            return shipping_policy
        return None
    except Exception as e:
        print(f"⚠️  Could not check existing policy: {e}", flush=True)
        return None


def main():
    """Main function to add shipping policy."""
    print("🚀 Adding Shipping Policy to Your Store\n", flush=True)

    # Read policy content
    policy_content = read_shipping_policy()
    if not policy_content:
        print("❌ Shipping policy file not found!", flush=True)
        print("   Expected: ~/neolight/policy_shipping_policy.html", flush=True)
        return

    print(f"✅ Policy content loaded ({len(policy_content)} characters)\n", flush=True)

    # Check if policy already exists
    current_policy = get_current_policies()
    if current_policy and current_policy.get("body"):
        print("⚠️  Shipping policy already exists!", flush=True)
        print("   Attempting to update...\n", flush=True)

    # Try to add via GraphQL
    print("📝 Attempting to add policy via API...", flush=True)
    success = add_policy_via_graphql(policy_content)

    if success:
        print("\n✅ SUCCESS! Shipping policy added to your store!", flush=True)
        print(f"\n🌐 Verify at: https://{SHOPIFY_STORE}/admin/settings/legal", flush=True)
    else:
        print("\n⚠️  API method unavailable - manual setup required", flush=True)
        print("", flush=True)
        print("📝 Manual Steps:", flush=True)
        print("   1. Go to: https://{SHOPIFY_STORE}/admin/settings/legal", flush=True)
        print("   2. Click on 'Shipping policy'", flush=True)
        print("   3. Copy content from: ~/neolight/policy_shipping_policy.html", flush=True)
        print("   4. Paste into editor", flush=True)
        print("   5. Click 'Publish'", flush=True)
        print("", flush=True)
        print("   OR open the file:", flush=True)
        print("   cat ~/neolight/policy_shipping_policy.html", flush=True)


if __name__ == "__main__":
    main()

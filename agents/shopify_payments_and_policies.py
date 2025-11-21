#!/usr/bin/env python3
"""
Shopify Payment Methods & Policies Setup
- Enable payment methods (Shopify Payments, PayPal)
- Add store policies (Privacy, Refund, Terms)
"""

import os
from typing import Any

import requests

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")

SHOPIFY_API_VERSION = "2024-01"
BASE_URL = f"https://{SHOPIFY_STORE}/admin/api/{SHOPIFY_API_VERSION}"

# Store Policies Templates
POLICIES = {
    "privacy_policy": {
        "title": "Privacy Policy",
        "body": """<h2>Privacy Policy</h2>

<p><strong>Last Updated:</strong> November 2025</p>

<p>At TrendyTreasure Market, we respect your privacy and are committed to protecting your personal information. This Privacy Policy explains how we collect, use, and safeguard your data when you visit our store.</p>

<h3>1. Information We Collect</h3>
<ul>
<li><strong>Personal Information:</strong> Name, email address, shipping address, and phone number when you place an order</li>
<li><strong>Payment Information:</strong> Credit card details processed securely through Shopify Payments (we never store full card numbers)</li>
<li><strong>Browsing Data:</strong> Cookies and analytics to improve your shopping experience</li>
<li><strong>Communication:</strong> Messages you send us via email or contact forms</li>
</ul>

<h3>2. How We Use Your Information</h3>
<ul>
<li>Process and fulfill your orders</li>
<li>Send order confirmations and tracking information</li>
<li>Respond to customer service inquiries</li>
<li>Improve our website and product offerings</li>
<li>Send marketing emails (you can unsubscribe at any time)</li>
<li>Comply with legal obligations</li>
</ul>

<h3>3. Information Sharing</h3>
<p>We do NOT sell, trade, or rent your personal information to third parties. We may share your information only with:</p>
<ul>
<li><strong>Service Providers:</strong> Shipping carriers, payment processors, and fulfillment partners to complete your orders</li>
<li><strong>Legal Requirements:</strong> When required by law or to protect our rights</li>
</ul>

<h3>4. Data Security</h3>
<p>We use industry-standard security measures (SSL encryption, secure payment processing) to protect your information. However, no method of transmission over the internet is 100% secure.</p>

<h3>5. Your Rights</h3>
<p>You have the right to:</p>
<ul>
<li>Access your personal information</li>
<li>Request correction of inaccurate data</li>
<li>Request deletion of your data</li>
<li>Opt-out of marketing communications</li>
</ul>

<h3>6. Cookies</h3>
<p>We use cookies to enhance your browsing experience, analyze site traffic, and personalize content. You can disable cookies in your browser settings.</p>

<h3>7. Third-Party Links</h3>
<p>Our store may contain links to external websites. We are not responsible for the privacy practices of these sites.</p>

<h3>8. Children's Privacy</h3>
<p>Our store is not intended for children under 13. We do not knowingly collect information from children.</p>

<h3>9. Changes to This Policy</h3>
<p>We may update this Privacy Policy from time to time. Changes will be posted on this page with an updated "Last Updated" date.</p>

<h3>10. Contact Us</h3>
<p>If you have questions about this Privacy Policy, please contact us:</p>
<ul>
<li><strong>Email:</strong> tradeplatformnoni@gmail.com</li>
<li><strong>Store:</strong> TrendyTreasure Market</li>
</ul>""",
    },
    "refund_policy": {
        "title": "Refund Policy",
        "body": """<h2>Refund Policy</h2>

<p><strong>Last Updated:</strong> November 2025</p>

<h3>30-Day Money-Back Guarantee</h3>
<p>At TrendyTreasure Market, we stand behind the quality of our products. If you're not completely satisfied with your purchase, we offer a full refund within 30 days of delivery.</p>

<h3>Refund Eligibility</h3>
<p>To be eligible for a refund, your item must be:</p>
<ul>
<li>Unused and in original packaging</li>
<li>In the same condition you received it</li>
<li>Returned within 30 days of delivery</li>
<li>Accompanied by proof of purchase (order number or receipt)</li>
</ul>

<h3>Non-Refundable Items</h3>
<p>The following items cannot be refunded:</p>
<ul>
<li>Items damaged by misuse or normal wear</li>
<li>Items returned after 30 days</li>
<li>Items without original packaging</li>
<li>Custom or personalized items</li>
</ul>

<h3>How to Request a Refund</h3>
<ol>
<li><strong>Contact Us:</strong> Email us at tradeplatformnoni@gmail.com with your order number</li>
<li><strong>Reason:</strong> Provide reason for return (defective, wrong item, etc.)</li>
<li><strong>Approval:</strong> We'll review your request within 2 business days</li>
<li><strong>Return:</strong> We'll provide a return address and shipping instructions</li>
</ol>

<h3>Return Shipping</h3>
<ul>
<li><strong>Defective Items:</strong> We cover return shipping costs</li>
<li><strong>Change of Mind:</strong> Customer is responsible for return shipping</li>
<li><strong>International Returns:</strong> Customer is responsible for all shipping costs</li>
</ul>

<h3>Refund Processing</h3>
<ul>
<li>Once we receive and inspect your return, we'll notify you</li>
<li>Refunds are processed within 5-7 business days</li>
<li>Refunds are issued to the original payment method</li>
<li>Shipping costs are non-refundable (unless item was defective)</li>
</ul>

<h3>Exchanges</h3>
<p>We currently do not offer direct exchanges. Please return the item for a refund and place a new order for the item you want.</p>

<h3>Damaged or Defective Items</h3>
<p>If you receive a damaged or defective item, contact us immediately at tradeplatformnoni@gmail.com with photos. We'll send a replacement at no cost.</p>

<h3>Late or Missing Refunds</h3>
<p>If you haven't received your refund after 7 business days:</p>
<ol>
<li>Check your bank account or credit card statement</li>
<li>Contact your payment provider</li>
<li>Contact us at tradeplatformnoni@gmail.com</li>
</ol>

<h3>Contact Us</h3>
<p>For refund inquiries, please contact:</p>
<ul>
<li><strong>Email:</strong> tradeplatformnoni@gmail.com</li>
<li><strong>Response Time:</strong> Within 24-48 hours</li>
</ul>""",
    },
    "terms_of_service": {
        "title": "Terms of Service",
        "body": """<h2>Terms of Service</h2>

<p><strong>Last Updated:</strong> November 2025</p>

<p>Welcome to TrendyTreasure Market. By accessing or using our website, you agree to be bound by these Terms of Service. Please read them carefully.</p>

<h3>1. Agreement to Terms</h3>
<p>By accessing our store, you agree to comply with and be bound by these Terms of Service. If you do not agree, please do not use our services.</p>

<h3>2. Use of Our Store</h3>
<p>You agree to use our store only for lawful purposes. You may not:</p>
<ul>
<li>Use the store in any way that violates applicable laws</li>
<li>Transmit any harmful code, viruses, or malware</li>
<li>Attempt to gain unauthorized access to our systems</li>
<li>Interfere with or disrupt the store's operation</li>
<li>Use automated systems to access the store without permission</li>
</ul>

<h3>3. Products and Pricing</h3>
<ul>
<li>All products are subject to availability</li>
<li>We reserve the right to modify prices at any time</li>
<li>Product descriptions and images are for illustration purposes</li>
<li>We strive for accuracy but do not guarantee exact color matches</li>
<li>Prices are in USD unless otherwise stated</li>
</ul>

<h3>4. Orders and Payment</h3>
<ul>
<li>By placing an order, you make an offer to purchase products</li>
<li>We reserve the right to accept or reject any order</li>
<li>Payment must be completed before order processing</li>
<li>We accept major credit cards and PayPal</li>
<li>Orders are subject to verification and approval</li>
</ul>

<h3>5. Shipping and Delivery</h3>
<ul>
<li>Shipping times are estimates, not guarantees</li>
<li>We are not responsible for delays caused by carriers</li>
<li>International shipping may be subject to customs fees</li>
<li>Risk of loss transfers to you upon delivery</li>
</ul>

<h3>6. Intellectual Property</h3>
<p>All content on this store (text, images, logos, designs) is owned by TrendyTreasure Market or its licensors. You may not reproduce, distribute, or create derivative works without permission.</p>

<h3>7. Limitation of Liability</h3>
<p>To the maximum extent permitted by law:</p>
<ul>
<li>We are not liable for indirect, incidental, or consequential damages</li>
<li>Our total liability shall not exceed the amount you paid for the product</li>
<li>We provide products "as is" without warranties</li>
</ul>

<h3>8. Indemnification</h3>
<p>You agree to indemnify and hold TrendyTreasure Market harmless from any claims, damages, or expenses arising from your use of our store or violation of these Terms.</p>

<h3>9. Dispute Resolution</h3>
<p>Any disputes will be resolved through good faith negotiation. If unresolved, disputes will be governed by the laws of Illinois, United States.</p>

<h3>10. Changes to Terms</h3>
<p>We reserve the right to modify these Terms at any time. Changes will be effective immediately upon posting. Continued use constitutes acceptance of changes.</p>

<h3>11. Termination</h3>
<p>We may terminate or suspend your access to our store at any time, without notice, for any reason, including violation of these Terms.</p>

<h3>12. Contact Information</h3>
<p>For questions about these Terms, contact us:</p>
<ul>
<li><strong>Email:</strong> tradeplatformnoni@gmail.com</li>
<li><strong>Store:</strong> TrendyTreasure Market</li>
<li><strong>Address:</strong> 424 W Diversey Pkwy apt 524, Chicago, IL 60614</li>
</ul>""",
    },
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
        return response.json()
    except Exception as e:
        print(f"❌ API error: {e}", flush=True)
        if hasattr(e, "response") and e.response is not None:
            try:
                error_text = e.response.text[:300]
                print(f"   Response: {error_text}", flush=True)
            except:
                pass
        return {}


def get_payment_providers() -> list[dict]:
    """Get available payment providers."""
    try:
        response = shopify_request("GET", "payment_providers.json")
        return response.get("payment_providers", [])
    except:
        return []


def enable_shopify_payments() -> bool:
    """Enable Shopify Payments."""
    try:
        # Check if Shopify Payments is available
        providers = get_payment_providers()
        shopify_payments = [p for p in providers if p.get("name") == "shopify_payments"]

        if not shopify_payments:
            print("📝 Shopify Payments setup requires:", flush=True)
            print("   1. Go to: Settings → Payments", flush=True)
            print("   2. Click 'Complete account setup' for Shopify Payments", flush=True)
            print("   3. Provide business information and bank details", flush=True)
            print("   4. This must be done manually in admin panel", flush=True)
            return False

        print("✅ Shopify Payments is available", flush=True)
        print("   Complete setup in admin: Settings → Payments", flush=True)
        return True
    except Exception as e:
        print(f"⚠️  Shopify Payments check: {e}", flush=True)
        return False


def enable_paypal() -> bool:
    """Enable PayPal payment method."""
    try:
        # PayPal setup via API is limited - usually requires manual setup
        print("📝 PayPal setup instructions:", flush=True)
        print("   1. Go to: Settings → Payments", flush=True)
        print("   2. Click 'Add payment provider'", flush=True)
        print("   3. Select 'PayPal'", flush=True)
        print("   4. Connect your PayPal business account", flush=True)
        print("   5. Enable PayPal Express Checkout", flush=True)
        print("   Note: PayPal requires manual setup in admin panel", flush=True)
        return True
    except Exception as e:
        print(f"⚠️  PayPal setup: {e}", flush=True)
        return False


def add_policy(policy_key: str) -> bool:
    """Add a store policy."""
    policy_data = POLICIES.get(policy_key)
    if not policy_data:
        return False

    try:
        # Note: Shopify Admin API doesn't directly support policy creation
        # Policies are managed through the admin UI or via GraphQL
        # We'll provide instructions for manual setup

        print(f"📝 Policy: {policy_data['title']}", flush=True)
        print("   Template ready - add manually in admin:", flush=True)
        print("   1. Go to: Settings → Legal", flush=True)
        print("   2. Click 'Create from template' or 'Add policy'", flush=True)
        print(f"   3. Select '{policy_data['title']}'", flush=True)
        print("   4. Copy and paste the policy content below:", flush=True)
        print(f"\n{'=' * 60}", flush=True)
        print("POLICY CONTENT:", flush=True)
        print(f"{'=' * 60}", flush=True)
        print(policy_data["body"], flush=True)
        print(f"{'=' * 60}\n", flush=True)

        # Save to file for easy copy-paste
        policy_file = f"policy_{policy_key}.html"
        with open(policy_file, "w", encoding="utf-8") as f:
            f.write(policy_data["body"])
        print(f"✅ Policy saved to: {policy_file} (for easy copy-paste)", flush=True)

        return True
    except Exception as e:
        print(f"❌ Failed to create policy: {e}", flush=True)
        return False


def create_policy_files():
    """Create HTML files for all policies."""
    for policy_key, policy_data in POLICIES.items():
        filename = f"policy_{policy_key}.html"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(policy_data["body"])
            print(f"✅ Created: {filename}", flush=True)
        except Exception as e:
            print(f"❌ Failed to create {filename}: {e}", flush=True)


def main():
    """Main setup function."""
    print("🚀 Setting Up Payment Methods & Store Policies\n", flush=True)

    # Step 1: Payment Methods
    print("💳 Step 1: Payment Methods Setup\n", flush=True)

    print("📋 Shopify Payments:", flush=True)
    enable_shopify_payments()
    print("", flush=True)

    print("📋 PayPal:", flush=True)
    enable_paypal()
    print("", flush=True)

    # Step 2: Store Policies
    print("📄 Step 2: Store Policies Setup\n", flush=True)

    print("Creating policy templates...\n", flush=True)
    create_policy_files()
    print("", flush=True)

    for policy_key in POLICIES:
        add_policy(policy_key)
        print("", flush=True)

    print("\n✅ Setup Instructions Complete!", flush=True)
    print("\n📝 Next Steps:", flush=True)
    print("   1. Go to: https://{SHOPIFY_STORE}/admin/settings/payments", flush=True)
    print("      Enable Shopify Payments or PayPal", flush=True)
    print("", flush=True)
    print("   2. Go to: https://{SHOPIFY_STORE}/admin/settings/legal", flush=True)
    print("      Add the three policies using the HTML files created above", flush=True)
    print("", flush=True)
    print("📁 Policy files created in current directory:", flush=True)
    print("   • policy_privacy_policy.html", flush=True)
    print("   • policy_refund_policy.html", flush=True)
    print("   • policy_terms_of_service.html", flush=True)


if __name__ == "__main__":
    main()

#!/bin/bash
echo "🧠 NeoLight Phase 3901–4000 — Commodity Intelligence Autopilot"
echo "--------------------------------------------------------------"

# ✅ Ensure folder structure
mkdir -p ai/providers logs config

# ==============================================================
# 1️⃣ Install the Unified CommodityProvider (Gold + Silver)
# ==============================================================

cat > ai/providers/commodity_provider.py <<'EOF'
import requests, time, json
from datetime import datetime

class CommodityProvider:
    def __init__(self):
        self.api_keys = {
            "metalpriceapi": "demo",  # Replace with key if available
            "metalsapi": "demo"
        }
        self.last_success = None

    def _get_goldapi(self):
        try:
            url = "https://api.gold-api.com/price"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                gold = data.get("XAU")
                silver = data.get("XAG")
                if gold and silver:
                    print(f"🏅 Gold-API: XAU={gold}, XAG={silver}")
                    return {"XAU": gold, "XAG": silver, "source": "GoldAPI"}
        except Exception as e:
            print(f"⚠️ Gold-API failed: {e}")
        return {}

    def _get_metalpriceapi(self):
        try:
            url = f"https://api.metalpriceapi.com/v1/latest?api_key={self.api_keys['metalpriceapi']}&base=USD&currencies=XAU,XAG"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json().get("rates", {})
                print(f"💰 MetalpriceAPI: {data}")
                return {"XAU": data.get("XAU"), "XAG": data.get("XAG"), "source": "MetalpriceAPI"}
        except Exception as e:
            print(f"⚠️ MetalpriceAPI failed: {e}")
        return {}

    def _get_coingecko(self):
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=pax-gold,silver&vs_currencies=usd"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                gold = data.get("pax-gold", {}).get("usd")
                silver = data.get("silver", {}).get("usd")
                print(f"🪙 CoinGecko: XAU={gold}, XAG={silver}")
                return {"XAU": gold, "XAG": silver, "source": "CoinGecko"}
        except Exception as e:
            print(f"⚠️ CoinGecko failed: {e}")
        return {}

    def get_latest_prices(self):
        for fn in [self._get_goldapi, self._get_metalpriceapi, self._get_coingecko]:
            data = fn()
            if data:
                self.last_success = data["source"]
                return data
        print("❌ All commodity feeds failed.")
        return {}
EOF

echo "✅ CommodityProvider installed."


# ==============================================================
# 2️⃣ Add Diagnostics + Auto-Alert into neolight-fix
# ==============================================================

if ! grep -q "🧩 Verifying commodity feed health" neolight-fix 2>/dev/null; then
cat >> neolight-fix <<'EOF'

echo "🧩 Verifying commodity feed health..."
python3 - <<'PYCODE'
from ai.providers.commodity_provider import CommodityProvider
from tools.alert_notify import send_alert
provider = CommodityProvider()
data = provider.get_latest_prices()
if not data:
    print("⚠️ No commodity data. Sending alert...")
    send_alert("⚠️ Commodity feed failure — All sources offline.")
else:
    print(f"✅ Commodity feed OK from {data['source']}: XAU={data.get('XAU')} XAG={data.get('XAG')}")
PYCODE
EOF
fi

echo "✅ neolight-fix upgraded with commodity diagnostics."


# ==============================================================
# 3️⃣ Patch signal engine to include Gold & Silver
# ==============================================================

if [ -f ai/signal_engine.py ]; then
  sed -i '' 's/"NVDA"/"NVDA", "GOLD", "SILVER"/g' ai/signal_engine.py
  echo "✅ GOLD & SILVER added to trading universe."
else
  echo "⚠️ signal_engine.py not found — skipping."
fi


# ==============================================================
# 4️⃣ Test and Verify
# ==============================================================

echo "🧪 Running quick commodity feed test..."
python3 - <<'PYCODE'
from ai.providers.commodity_provider import CommodityProvider
provider = CommodityProvider()
print(provider.get_latest_prices())
PYCODE

echo "✅ Phase 3901–4000 Autopilot complete!"


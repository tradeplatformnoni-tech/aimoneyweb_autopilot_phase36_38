import json, os, sys
POL = "config/risk_policy.json"
OUT = "config/weights.json"

def main():
    if not os.path.exists(POL):
        print("❗ risk_policy.json not found. Run: python3 ai/risk/risk_governor.py")
        sys.exit(1)
    data = json.load(open(POL))
    weights = data.get("weights", {})
    json.dump(weights, open(OUT, "w"), indent=2)
    print(f"✅ Wrote weights → {OUT}")
if __name__=="__main__":
    main()

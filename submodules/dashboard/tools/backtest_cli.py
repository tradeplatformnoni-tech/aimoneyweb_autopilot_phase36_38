import requests, sys, json

if len(sys.argv) != 4:
    print("Usage: python backtest_cli.py <strategy> <config_json> <ohlcv_data_json>")
    sys.exit(1)

strategy = sys.argv[1]
config = json.loads(sys.argv[2])
data_file = sys.argv[3]

resp = requests.post("http://localhost:8000/api/backtest", json={
    "strategy": strategy,
    "config": config,
    "data_file": data_file
})

print("🧪 Backtest Results:")
print(json.dumps(resp.json(), indent=2))

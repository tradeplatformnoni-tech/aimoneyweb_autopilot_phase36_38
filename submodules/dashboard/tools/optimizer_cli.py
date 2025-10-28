#!/usr/bin/env python3
import requests, json, sys
payload={
  "strategy":"momentum",
  "grid":{"window":[2,3,4,5]},
  "data_file":"historical_data/sample_data.json"
}
resp=requests.post("http://127.0.0.1:8000/api/optimize",json=payload)
print(json.dumps(resp.json(),indent=2))

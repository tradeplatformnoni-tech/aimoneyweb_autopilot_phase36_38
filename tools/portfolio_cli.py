#!/usr/bin/env python3
import requests, json
payload={
 "strategies":["momentum","crossover","mean_reversion"],
 "weights":{"momentum":0.4,"crossover":0.4,"mean_reversion":0.2},
 "data_files":{
   "momentum":"historical_data/momentum_data.json",
   "crossover":"historical_data/crossover_data.json",
   "mean_reversion":"historical_data/mean_reversion_data.json"
 }
}
r=requests.post("http://127.0.0.1:8000/api/portfolio_optimize",json=payload)
print(json.dumps(r.json(),indent=2))

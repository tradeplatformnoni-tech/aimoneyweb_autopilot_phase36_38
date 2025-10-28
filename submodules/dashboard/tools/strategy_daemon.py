import json
from ai.strategy_engine import run_once

with open("config/symbols.json") as f:
    symbols = json.load(f)

with open("config/agents.json") as f:
    agents = json.load(f)

for symbol in symbols:
    for agent in agents:
        run_once(symbol=symbol, agent=agent)

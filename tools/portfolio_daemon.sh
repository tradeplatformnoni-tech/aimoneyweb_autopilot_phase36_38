#!/bin/bash
while true
do
  echo "🧠 Updating portfolio snapshot..."
  python3 tools/portfolio_updater.py
  sleep 300
done

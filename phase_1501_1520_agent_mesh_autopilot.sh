#!/bin/bash

echo "🤖 Starting Phase 1501–1520: Mesh-Connecting All Agents..."

mkdir -p agents/atlas
mkdir -p agents/dropship
mkdir -p agents/ticketbot

# Shared mesh sync function
cat <<EOT > mesh/agent_adapter.py
# mesh/agent_adapter.py

import requests

def mesh_sync(agent_id, signal_data):
    payload = {"agent_id": agent_id, "signal_data": signal_data}
    try:
        res = requests.post("http://127.0.0.1:8000/api/mesh/sync", json=payload, timeout=2)
        return res.json()
    except Exception as e:
        return {"error": str(e)}
EOT

# Atlas integration
cat <<EOT > agents/atlas/runner.py
# agents/atlas/runner.py

from mesh.agent_adapter import mesh_sync

def run_atlas():
    print("⚡ Atlas running...")
    signal = "Buy TSLA"
    mesh_response = mesh_sync("Atlas", signal)
    print("📡 Atlas Mesh Sync:", mesh_response)
EOT

# Dropship integration
cat <<EOT > agents/dropship/runner.py
# agents/dropship/runner.py

from mesh.agent_adapter import mesh_sync

def run_dropship():
    print("🛒 Dropship scanning...")
    signal = "Found undervalued item: Gucci Belt"
    mesh_response = mesh_sync("Dropship", signal)
    print("📡 Dropship Mesh Sync:", mesh_response)
EOT

# TicketBot integration
cat <<EOT > agents/ticketbot/runner.py
# agents/ticketbot/runner.py

from mesh.agent_adapter import mesh_sync

def run_ticketbot():
    print("🎟️ TicketBot alerting...")
    signal = "Alert: Resell event for Travis Scott tickets"
    mesh_response = mesh_sync("TicketBot", signal)
    print("📡 TicketBot Mesh Sync:", mesh_response)
EOT

echo "✅ Agent Mesh Integration Code Created!"
echo "📍 Run tests:"
echo "   ➤ python agents/atlas/runner.py"
echo "   ➤ python agents/dropship/runner.py"
echo "   ➤ python agents/ticketbot/runner.py"


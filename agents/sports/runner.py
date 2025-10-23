# agents/sports/runner.py

from mesh.agent_adapter import mesh_sync

def run_sports():
    print("🏈 Sports Insight Agent running...")
    signal = "Over/Under Alert: NYG vs PHI | Model: Over 41.5"
    mesh_response = mesh_sync("SportsInsight", signal)
    print("📡 SportsInsight Mesh Sync:", mesh_response)

# agents/atlas/runner.py

from mesh.agent_adapter import mesh_sync

def run_atlas():
    print("⚡ Atlas running...")
    signal = "Buy TSLA"
    mesh_response = mesh_sync("Atlas", signal)
    print("📡 Atlas Mesh Sync:", mesh_response)

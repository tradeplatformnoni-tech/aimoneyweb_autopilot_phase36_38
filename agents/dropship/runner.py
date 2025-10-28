# agents/dropship/runner.py

from mesh.agent_adapter import mesh_sync

def run_dropship():
    print("🛒 Dropship scanning...")
    signal = "Found undervalued item: Gucci Belt"
    mesh_response = mesh_sync("Dropship", signal)
    print("📡 Dropship Mesh Sync:", mesh_response)

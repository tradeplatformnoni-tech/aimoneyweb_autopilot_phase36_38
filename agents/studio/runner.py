# agents/studio/runner.py

from mesh.agent_adapter import mesh_sync

def run_studiobot():
    print("🎙️ Studio Booking AI scheduling...")
    signal = "Available Slot: Downtown Studio 12PM-2PM | Client: NeoLight Media"
    mesh_response = mesh_sync("StudioBot", signal)
    print("📡 StudioBot Mesh Sync:", mesh_response)

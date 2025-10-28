# mesh/agentsync.py

from mesh.core import mesh_bus

def agent_sync(agent_id, signal_data):
    mesh_bus.broadcast(agent_id, f"Signal: {signal_data}")
    mesh_bus.update_memory(f"{agent_id}_last_signal", signal_data)
    return {"status": "synced", "agent": agent_id}

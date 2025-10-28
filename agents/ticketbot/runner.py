# agents/ticketbot/runner.py

from mesh.agent_adapter import mesh_sync

def run_ticketbot():
    print("🎟️ TicketBot alerting...")
    signal = "Alert: Resell event for Travis Scott tickets"
    mesh_response = mesh_sync("TicketBot", signal)
    print("📡 TicketBot Mesh Sync:", mesh_response)

#!/bin/bash

echo "🧠 Starting Phase 1301–1400: Neural Mesh Layer..."

# Create mesh core structure
mkdir -p mesh
mkdir -p api/mesh

# Core mesh memory bus
cat <<EOT > mesh/core.py
# mesh/core.py

class NeuralMeshBus:
    def __init__(self):
        self.message_log = []
        self.shared_memory = {}

    def broadcast(self, sender, message):
        entry = {"from": sender, "msg": message}
        self.message_log.append(entry)
        return entry

    def update_memory(self, key, value):
        self.shared_memory[key] = value
        return self.shared_memory

    def get_state(self):
        return {"memory": self.shared_memory, "log": self.message_log[-10:]}
        
# Singleton instance
mesh_bus = NeuralMeshBus()
EOT

# Agent sync interface
cat <<EOT > mesh/agentsync.py
# mesh/agentsync.py

from mesh.core import mesh_bus

def agent_sync(agent_id, signal_data):
    mesh_bus.broadcast(agent_id, f"Signal: {signal_data}")
    mesh_bus.update_memory(f"{agent_id}_last_signal", signal_data)
    return {"status": "synced", "agent": agent_id}
EOT

# FastAPI route: sync
cat <<EOT > api/mesh/sync.py
# api/mesh/sync.py

from fastapi import APIRouter
from mesh.agentsync import agent_sync

router = APIRouter()

@router.post("/api/mesh/sync")
def sync_agent(agent_id: str, signal_data: str):
    return agent_sync(agent_id, signal_data)
EOT

# FastAPI route: message
cat <<EOT > api/mesh/message.py
# api/mesh/message.py

from fastapi import APIRouter
from mesh.core import mesh_bus

router = APIRouter()

@router.post("/api/mesh/message")
def message(sender: str, msg: str):
    return mesh_bus.broadcast(sender, msg)
EOT

# FastAPI route: state
cat <<EOT > api/mesh/state.py
# api/mesh/state.py

from fastapi import APIRouter
from mesh.core import mesh_bus

router = APIRouter()

@router.get("/api/mesh/state")
def state():
    return mesh_bus.get_state()
EOT

# Inject routes into backend/main.py
main_file="backend/main.py"
if grep -q "mesh" "$main_file"; then
    echo "✅ Mesh routes already integrated."
else
    echo "⚙️ Injecting Neural Mesh routes..."
    sed -i '' '/from fastapi import FastAPI/a\
from api.mesh import sync as mesh_sync, message as mesh_message, state as mesh_state' $main_file

    sed -i '' '/app = FastAPI()/a\
app.include_router(mesh_sync.router)\napp.include_router(mesh_message.router)\napp.include_router(mesh_state.router)' $main_file
fi

# Restart FastAPI via PM2
pm2 restart neolight || echo "⚠️ PM2 not found. Restart manually."

echo "✅ Neural Mesh Layer Activated!"
echo "🧬 Endpoints ready:"
echo "  ➤ POST /api/mesh/sync"
echo "  ➤ POST /api/mesh/message"
echo "  ➤ GET  /api/mesh/state"


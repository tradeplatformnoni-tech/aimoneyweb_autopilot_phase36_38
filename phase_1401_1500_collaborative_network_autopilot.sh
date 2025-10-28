#!/bin/bash

echo "🌍 Starting Phase 1401–1500: Collaborative Network Layer..."

mkdir -p network
mkdir -p api/network

# Node file with identity and peer registry
cat <<EOT > network/node.py
# network/node.py

import uuid
from datetime import datetime

class NodeIdentity:
    def __init__(self):
        self.node_id = str(uuid.uuid4())
        self.start_time = datetime.utcnow().isoformat()
        self.peers = {}

    def register_peer(self, peer_id, address):
        self.peers[peer_id] = {"address": address, "last_seen": datetime.utcnow().isoformat()}
        return self.peers[peer_id]

    def get_peers(self):
        return self.peers

    def get_identity(self):
        return {"node_id": self.node_id, "start_time": self.start_time}
        
# Singleton
node = NodeIdentity()
EOT

# API: Register peer
cat <<EOT > api/network/peer.py
# api/network/peer.py

from fastapi import APIRouter
from network.node import node

router = APIRouter()

@router.post("/api/network/peer")
def register(peer_id: str, address: str):
    peer_info = node.register_peer(peer_id, address)
    return {"registered": peer_info}
EOT

# API: Get node identity
cat <<EOT > api/network/handshake.py
# api/network/handshake.py

from fastapi import APIRouter
from network.node import node

router = APIRouter()

@router.get("/api/network/handshake")
def handshake():
    return node.get_identity()
EOT

# API: Ping
cat <<EOT > api/network/ping.py
# api/network/ping.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/api/network/ping")
def ping():
    return {"pong": True}
EOT

# Patch backend/main.py
main_file="backend/main.py"
if grep -q "network" "$main_file"; then
    echo "✅ Collaborative Network routes already integrated."
else
    echo "⚙️ Injecting Collaborative Network routes..."
    sed -i '' '/from fastapi import FastAPI/a\
from api.network import peer as peer_api, handshake as handshake_api, ping as ping_api' $main_file

    sed -i '' '/app = FastAPI()/a\
app.include_router(peer_api.router)\napp.include_router(handshake_api.router)\napp.include_router(ping_api.router)' $main_file
fi

# Restart app
pm2 restart neolight || echo "⚠️ PM2 not found. Restart manually."

echo "✅ Collaborative Network Layer Deployed!"
echo "🌐 Endpoints:"
echo "  ➤ POST /api/network/peer"
echo "  ➤ GET  /api/network/handshake"
echo "  ➤ GET  /api/network/ping"


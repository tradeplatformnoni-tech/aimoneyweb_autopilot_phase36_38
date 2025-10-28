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

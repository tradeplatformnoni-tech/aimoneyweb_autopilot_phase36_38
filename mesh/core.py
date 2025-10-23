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

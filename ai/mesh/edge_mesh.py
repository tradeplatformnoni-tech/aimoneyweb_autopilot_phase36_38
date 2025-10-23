import random,time
def edge_heartbeat():
    # pretend 3-8 edge nodes are alive, some lagging
    return {
        "nodes": random.randint(3,8),
        "avg_latency_ms": round(random.uniform(20,120),1),
        "lagging": random.randint(0,2)
    }

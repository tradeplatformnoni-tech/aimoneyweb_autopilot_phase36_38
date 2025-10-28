import random, joblib, os, time

GA_PATH = "models/ga_model.pkl"

def _fitness(weights):
    # Toy fitness: prefer small positive weight
    w = float(weights.get("w", 0.0))
    return 1.0 - abs(w - 0.2)

def evolve(pop_size=16, gens=8, mutate=0.1):
    pop = [{"w": random.uniform(-1, 1)} for _ in range(pop_size)]
    for _ in range(gens):
        scored = [(w, _fitness(w)) for w in pop]
        scored.sort(key=lambda x: x[1], reverse=True)
        keep = [w for w, _ in scored[: max(2, pop_size // 2)]]
        children = []
        while len(keep) + len(children) < pop_size:
            a, b = random.sample(keep, 2)
            child = {"w": (a["w"] + b["w"]) / 2.0}
            if random.random() < mutate:
                child["w"] += random.uniform(-0.1, 0.1)
            children.append(child)
        pop = keep + children
    best = max(pop, key=_fitness)
    os.makedirs("models", exist_ok=True)
    joblib.dump({"weights": best, "score": _fitness(best), "ts": time.time()}, GA_PATH)
    return {"best": best, "score": _fitness(best), "path": GA_PATH}
